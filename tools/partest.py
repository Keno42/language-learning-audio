#!/usr/bin/env python3
"""Run the tests in parallel: what ``python -m unittest`` runs, spread over worker processes.

    python tools/partest.py                  # the whole suite, one worker per CPU
    python tools/partest.py -j 4             # four workers
    python tools/partest.py tests.test_docs  # modules, classes or tests, named as unittest names them
    python tools/partest.py --shard 2/4      # the second of four parts of the suite (CI runs the parts as separate jobs)
    python tools/partest.py --slowest 20     # and the 20 slowest tests, to see where the time goes

The suite is hundreds of independent simulated courses, each a second to a minute of one CPU: run one after another they
take tens of minutes, and nearly all of that is waiting for a single core. Here every test is scheduled on its own, except
that a class with a class-level fixture (``setUpClass``) or a module with a module-level one runs whole in one worker, so
its fixture is built once, as under ``python -m unittest``. Each worker is a fresh ``python`` process that imports the
tests itself: a test must not rely on another one having run before it in the same process.

The slow tests start first: a minute-long test started last keeps one worker busy after the others have finished. Each
test's time in the last run here is kept in ``.partest-times.json`` (not committed) for that; a test never timed starts
before all of them. The order changes nothing else: which tests run, and the parts of ``--shard``, do not depend on it.

``python -m unittest`` stays the reference: same loader, same ``TestCase`` machinery, same outcome. What a test prints is
shown only when it fails. Exit 0 when every test passes, 1 when one fails or errors, 2 when the tests cannot be loaded.
Standard library only, as the suite is.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMES = ROOT / ".partest-times.json"  # {test id: seconds} of the last run here


def _flatten(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _flatten(t)
        else:
            yield t


def _own(cls, name: str) -> bool:
    """Whether ``cls`` (or a base of it other than ``TestCase``) defines the class-level hook ``name``."""
    return getattr(getattr(cls, name), "__func__", None) is not getattr(unittest.TestCase, name).__func__


def units(tests) -> list[list[str]]:
    """The work to hand out, as lists of test ids: one list per test, except a class with ``setUpClass``/``tearDownClass`` (one list for
    the class) and a module with ``setUpModule``/``tearDownModule`` (one list for the module). Sorted, so the split is the same every run."""
    grouped: dict[str, list[str]] = {}
    for t in tests:
        cls = type(t)
        mod = sys.modules[cls.__module__]
        if hasattr(mod, "setUpModule") or hasattr(mod, "tearDownModule"):
            key = cls.__module__
        elif _own(cls, "setUpClass") or _own(cls, "tearDownClass"):
            key = f"{cls.__module__}.{cls.__qualname__}"
        else:
            key = t.id()
        grouped.setdefault(key, []).append(t.id())
    return [grouped[k] for k in sorted(grouped)]


class _Record(unittest.TestResult):
    """Collects what the parent prints: each test's time, and the text of every failure, error and skip."""

    def __init__(self):
        super().__init__()
        self.buffer = True  # what a test prints is kept with its failure, and dropped when it passes
        self.times: list[tuple[str, float]] = []
        self.unexpected: list[str] = []
        self._started = 0.0

    def startTest(self, test):
        self._started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        self.times.append((test.id(), time.perf_counter() - self._started))

    def _restoreStdout(self):
        self._mirrorOutput = False  # a failing test's output goes to the parent inside its text; written here as well it would be shown twice
        super()._restoreStdout()

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.unexpected.append(test.id())


EMPTY = {"ran": 0, "times": [], "skipped": [], "expected": 0, "unexpected": [], "failures": [], "errors": []}  # a unit's outcome


def run_unit(ids: list[str]) -> dict:
    """Run one unit in this worker process and return its outcome as plain data."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)  # where ``python -m unittest`` is run from
    result = _Record()
    try:
        unittest.defaultTestLoader.loadTestsFromNames(ids).run(result)
    except BaseException as exc:  # a worker must always answer: the parent would wait for it
        return {**EMPTY, "errors": [(ids[0], f"{type(exc).__name__}: {exc}")]}
    name = lambda t: t.id() if hasattr(t, "id") else str(t)  # noqa: E731  (a failed setUpClass is reported under a holder, not a test)
    return {
        "ran": result.testsRun,
        "times": result.times,
        "skipped": [(name(t), why) for t, why in result.skipped],
        "expected": len(result.expectedFailures),
        "unexpected": result.unexpected,
        "failures": [(name(t), text) for t, text in result.failures],
        "errors": [(name(t), text) for t, text in result.errors],
    }


def load(names: list[str]) -> list:
    """The tests ``python -m unittest [names]`` would run, loaded here only to list them (the workers load their own)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(names) if names else loader.discover(str(ROOT), top_level_dir=str(ROOT))
    tests = list(_flatten(suite))
    broken = [t for t in tests if type(t).__module__ == "unittest.loader"]  # a module that failed to import, a name that matched nothing
    if loader.errors or broken:
        for text in loader.errors:
            print(text, file=sys.stderr)
        raise SystemExit(2)
    return tests


def read_times() -> dict[str, float]:
    try:
        return {str(k): float(v) for k, v in json.loads(TIMES.read_text(encoding="utf-8")).items()}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}  # no run here yet, or a file cut short: every test counts as never timed


def write_times(times: dict[str, float]) -> None:
    try:
        tmp = TIMES.with_name(TIMES.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({k: round(v, 3) for k, v in sorted(times.items())}, indent=0), encoding="utf-8")
        os.replace(tmp, TIMES)  # whole or not at all: two runs at once leave one of the two files
    except OSError:
        pass  # a read-only checkout: the next run starts in the order of the names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="modules, classes or tests (default: everything under tests/)")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: one per CPU)")
    ap.add_argument("--shard", metavar="K/N", help="run only the K-th of N parts of the suite")
    ap.add_argument("--slowest", type=int, default=0, metavar="N", help="list the N slowest tests")
    ap.add_argument("-v", "--verbose", action="store_true", help="a line per test as it finishes")
    args = ap.parse_args(argv)

    work = units(load(args.names))
    if args.shard:
        try:
            k, n = (int(x) for x in args.shard.split("/"))
        except ValueError:
            ap.error("--shard takes K/N, e.g. 2/4")
        if not 1 <= k <= n:
            ap.error("--shard K/N needs 1 <= K <= N")
        work = work[k - 1 :: n]  # every N-th unit: neighbours (the tests of one class, alike in cost) go to different parts
    last = read_times()
    work.sort(key=lambda ids: -sum(last.get(i, float("inf")) for i in ids))  # stable: by name among the tests never timed
    jobs = max(1, min(args.jobs, len(work)))

    started = time.perf_counter()
    ran = expected = 0
    times: list[tuple[str, float]] = []
    skipped: list[tuple[str, str]] = []
    failures: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []
    unexpected: list[str] = []
    # "spawn" everywhere: the same on Linux and macOS, and no worker inherits the parent's imported tests or its threads
    pool = ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context("spawn"))
    pending = {pool.submit(run_unit, ids): ids for ids in work}
    try:
        for done in as_completed(pending):
            try:
                out = done.result()
            except Exception as exc:  # the worker process died (killed, out of memory) or could not start: its tests count as errors
                out = {**EMPTY, "errors": [(pending[done][0], f"no answer from the worker: {type(exc).__name__}: {exc}")]}
            ran += out["ran"]
            expected += out["expected"]
            times += out["times"]
            skipped += out["skipped"]
            failures += out["failures"]
            errors += out["errors"]
            unexpected += out["unexpected"]
            if args.verbose:
                bad = {t.split(" ")[0] for t, _ in out["failures"] + out["errors"]}  # a failing subTest is named «test (its values)»
                skip = {t for t, _ in out["skipped"]}
                for test, seconds in out["times"]:
                    print(f"{'FAIL' if test in bad else 'skip' if test in skip else 'ok':4} {seconds:7.2f}s  {test}", flush=True)
            for kind, rows in (("FAIL", out["failures"]), ("ERROR", out["errors"])):
                for test, text in rows:
                    print(f"\n{'=' * 70}\n{kind}: {test}\n{'-' * 70}\n{text}", flush=True)
    except KeyboardInterrupt:  # Ctrl-C stops the run now: without this the workers go on through everything still queued
        workers = list((getattr(pool, "_processes", None) or {}).values())  # read before the shutdown, which forgets them
        pool.shutdown(wait=False, cancel_futures=True)
        for worker in workers:
            worker.terminate()  # the tests running now are dropped too: the exit would wait for them
        print(f"\ninterrupted after {ran} tests", file=sys.stderr)
        return 130
    pool.shutdown()
    wall = time.perf_counter() - started
    write_times({**last, **dict(times)})

    if args.slowest:
        print(f"\nslowest {args.slowest}:")
        for test, seconds in sorted(times, key=lambda r: -r[1])[: args.slowest]:
            print(f"  {seconds:7.2f}s  {test}")
    notes = [f"{label}={len(rows)}" for label, rows in (("failures", failures), ("errors", errors), ("skipped", skipped), ("unexpected successes", unexpected)) if rows]
    if expected:
        notes.append(f"expected failures={expected}")
    cpu = sum(s for _, s in times)
    part = f", part {args.shard}" if args.shard else ""
    print(f"\nRan {ran} tests in {wall:.1f}s ({cpu:.0f}s of test time over {jobs} workers{part})")
    ok = not (failures or errors or unexpected)
    print(("OK" if ok else "FAILED") + (f" ({', '.join(notes)})" if notes else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
