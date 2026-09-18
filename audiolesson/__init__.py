"""audiolesson — generate audio-first, recall-driven language lessons.

Pipeline (each stage is a separate module so any one can be swapped):

    curriculum (TOML)  ──┐
                         ├─► planner ─► script (JSON) ─► render (TTS + silence) ─► lesson audio
    learner state (JSON) ┘         │
                                   └─► learner state update + review metadata
"""

__version__ = "0.1.0"
