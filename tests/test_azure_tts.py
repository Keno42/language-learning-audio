"""#299: Azure Speech's official REST API as a provider with the same voices as edge-tts, and as the fallback when edge-tts is refused."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from audiolesson.render.renderer import _cache_path
from audiolesson.render.tts import AzureProvider, EdgeProvider, cache_family, get_provider

NEEDS_FFMPEG = unittest.skipUnless(shutil.which("ffmpeg"), "no ffmpeg")


def mp3_bytes() -> bytes:
    return subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=d=0.3", "-f", "mp3", "pipe:1"], capture_output=True, check=True
    ).stdout


class Server:
    """A fake Azure Speech endpoint: records the requests, answers from a script of (status, headers) then 200 with an mp3."""

    def __init__(self, script=()):
        self.requests = []
        self.script = list(script)
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body.decode()})
                if outer.script:
                    status, headers = outer.script.pop(0)
                    self.send_response(status)
                    for k, v in headers.items():
                        self.send_header(k, v)
                    self.end_headers()
                    return
                data = outer.mp3
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.mp3 = mp3_bytes() if shutil.which("ffmpeg") else b""
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}/cognitiveservices/v1"


def env(server):
    return mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": "SECRET-KEY-123", "AZURE_SPEECH_REGION": "northeurope", "AZURE_SPEECH_ENDPOINT": server.url})


class CheckTests(unittest.TestCase):
    def test_check_names_what_is_missing_without_a_value(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(AzureProvider().check(), "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are not set")
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": "k"}, clear=True):
            self.assertEqual(AzureProvider().check(), "AZURE_SPEECH_REGION is not set")
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": "k", "AZURE_SPEECH_REGION": "r"}, clear=True):
            self.assertIsNone(AzureProvider().check())

    def test_the_default_url_is_the_regions_and_the_voices_are_edges(self):
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_REGION": "northeurope"}, clear=True):
            self.assertEqual(AzureProvider().endpoint(), "https://northeurope.tts.speech.microsoft.com/cognitiveservices/v1")
        self.assertEqual(AzureProvider().default_voices("is"), ["is-IS-GudrunNeural", "is-IS-GunnarNeural"])
        self.assertIs(get_provider("azure").__class__, AzureProvider)

    def test_ssml_escapes_the_text_and_maps_the_rate(self):
        ssml = AzureProvider.ssml("Tom & <Jerry>", "is-IS-GudrunNeural", 0.6)
        self.assertIn("xml:lang='is-IS'", ssml)
        self.assertIn("<voice name='is-IS-GudrunNeural'>", ssml)
        self.assertIn("rate='-40%'", ssml)
        self.assertIn("Tom &amp; &lt;Jerry&gt;", ssml)
        self.assertIn("rate='+0%'", AzureProvider.ssml("a", "en-US-AriaNeural", 1.0))


@NEEDS_FFMPEG
class RequestTests(unittest.TestCase):
    def test_the_request_has_the_ssml_and_headers_and_the_key_only_in_a_header(self):
        with Server() as server, env(server):
            clip = AzureProvider().synthesize("Halló", "is", "is-IS-GudrunNeural", 1.0)
        self.assertGreater(clip.seconds, 0.1)
        (req,) = server.requests
        self.assertEqual(req["headers"]["ocp-apim-subscription-key"], "SECRET-KEY-123")
        self.assertEqual(req["headers"]["content-type"], "application/ssml+xml")
        self.assertEqual(req["headers"]["x-microsoft-outputformat"], "audio-24khz-48kbitrate-mono-mp3")
        self.assertIn("<prosody rate='+0%'>Halló</prosody>", req["body"])
        self.assertNotIn("SECRET-KEY-123", req["path"] + req["body"])

    def test_a_429_waits_for_retry_after_and_goes_on(self):
        waits = []
        err = io.StringIO()
        with Server(script=[(429, {"Retry-After": "7"}), (429, {"Retry-After": "2"})]) as server, env(server):
            with mock.patch("audiolesson.render.tts.time.sleep", side_effect=waits.append), contextlib.redirect_stderr(err):
                AzureProvider().synthesize("a", "is", "is-IS-GudrunNeural")
        self.assertEqual(waits, [7.0, 2.0])
        self.assertEqual(len(server.requests), 3)
        self.assertNotIn("SECRET-KEY-123", err.getvalue())

    def test_a_server_error_is_retried_and_a_bad_key_fails_without_the_key_in_the_message(self):
        waits = []
        with Server(script=[(503, {})]) as server, env(server):
            with mock.patch("audiolesson.render.tts.time.sleep", side_effect=waits.append), contextlib.redirect_stderr(io.StringIO()):
                AzureProvider().synthesize("a", "is", "is-IS-GudrunNeural")
        self.assertEqual(waits, [5.0])
        with Server(script=[(401, {})]) as server, env(server):
            with self.assertRaises(RuntimeError) as cm:
                AzureProvider().synthesize("a", "is", "is-IS-GudrunNeural")
        self.assertIn("HTTP 401", str(cm.exception))
        self.assertNotIn("SECRET-KEY-123", str(cm.exception))


class CacheTests(unittest.TestCase):
    def test_edge_and_azure_share_one_cache(self):
        cache = Path("/c")
        a = _cache_path(EdgeProvider(), cache, "Halló", "is", "is-IS-GudrunNeural", 1.0, True)
        b = _cache_path(AzureProvider(), cache, "Halló", "is", "is-IS-GudrunNeural", 1.0, True)
        self.assertEqual(a, b)
        self.assertEqual((cache_family(EdgeProvider()), cache_family(AzureProvider())), ("edge", "edge"))
        self.assertNotEqual(a, _cache_path(get_provider("stub"), cache, "Halló", "is", "is-IS-GudrunNeural", 1.0, True))

    def test_the_edge_cache_key_is_what_it_was(self):
        import hashlib

        key = hashlib.sha1("edge|v|1.000|is|True|x".encode()).hexdigest()
        self.assertEqual(_cache_path(EdgeProvider(), Path("/c"), "x", "is", "v", 1.0, True), Path("/c") / f"{key}.wav")


@NEEDS_FFMPEG
class FallbackTests(unittest.TestCase):
    def fake_edge_tts(self):
        class Refused(Exception):
            status = 403

        mod = types.ModuleType("edge_tts")

        class Communicate:
            def __init__(self, *a, **k):
                pass

            async def stream(self):
                raise Refused("403")
                yield  # pragma: no cover

        mod.Communicate = Communicate
        return mod

    def test_a_403_moves_the_clips_to_the_fallback_at_once_without_the_wait(self):
        err = io.StringIO()
        with Server() as server, env(server), mock.patch.dict(sys.modules, {"edge_tts": self.fake_edge_tts()}):
            edge = EdgeProvider()
            edge.fallback = AzureProvider()
            with mock.patch("audiolesson.render.tts.time.sleep") as sleep, contextlib.redirect_stderr(err):
                first = edge.synthesize("Halló", "is", "is-IS-GudrunNeural")
                second = edge.synthesize("Takk", "is", "is-IS-GudrunNeural")
            sleep.assert_not_called()
        self.assertGreater(first.seconds, 0.1)
        self.assertGreater(second.seconds, 0.1)
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(err.getvalue().count("edge-tts: service refusing (403); using azure"), 1, "said once")

    def test_without_a_fallback_the_wait_stays(self):
        with mock.patch.dict(sys.modules, {"edge_tts": self.fake_edge_tts()}):
            edge = EdgeProvider()
            edge.MINUTE = 0.0
            edge.refusal_budget_min = 1.0
            with mock.patch("audiolesson.render.tts.time.sleep"), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(Exception) as cm:
                    edge.synthesize("Halló", "is", "is-IS-GudrunNeural")
        self.assertIn("speech service refused (403)", str(cm.exception))

    def test_the_profile_key_wires_the_fallback_only_when_it_can_run(self):
        from audiolesson.render.renderer import load_profile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "v.toml"
            p.write_text('provider = "edge"\nfallback = "azure"\n', "utf-8")
            self.assertEqual(load_profile(p).fallback, "azure")
            self.assertEqual(load_profile(None).fallback, "")


if __name__ == "__main__":
    unittest.main()
