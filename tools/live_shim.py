"""Run an unmodified reference CLI against the course's Vocareum API proxy.

Why this exists: the course API key (``voc-...``) is served by a proxy at
https://claude.vocareum.com that enables the dated snapshot
``claude-haiku-4-5-20251001`` but rejects the bare alias ``claude-haiku-4-5``
that the reference code pins. This shim rewrites only that alias to its own
snapshot (the same model) at request time and then calls the CLI's real
``main()``. No reference source file is edited.

Usage (from a system's solution folder, with that system's venv python):

    python <pack>/tools/live_shim.py policy_extractor.__main__ pipeline data/policies/ ...

Author: Narendran Chakkrapani <n.chakkrapani@accenture.com>
"""
from __future__ import annotations

import importlib
import os
import sys
from typing import Any

from anthropic.resources.messages import Messages

ALIASES = {"claude-haiku-4-5": "claude-haiku-4-5-20251001"}

os.environ.setdefault("ANTHROPIC_BASE_URL", "https://claude.vocareum.com")

_original_create = Messages.create


def _create(self: Messages, *args: Any, **kwargs: Any) -> Any:
    model = kwargs.get("model")
    if model in ALIASES:
        kwargs["model"] = ALIASES[model]
    return _original_create(self, *args, **kwargs)


Messages.create = _create  # type: ignore[method-assign]

if __name__ == "__main__":
    module_name, *cli_args = sys.argv[1:]
    module = importlib.import_module(module_name)
    sys.argv = [module_name, *cli_args]
    raise SystemExit(module.main())
