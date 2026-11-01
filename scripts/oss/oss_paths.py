"""Path guard shared by the scripts/oss tools.

The tools are run by people and by AI agents (Cursor skills), so a path that arrives as a CLI
argument is untrusted: it must stay inside the current working directory (the project being
checked). Run a tool from the project's own folder to work on that project.

Defaults that the scripts compute themselves (the kit's policy, cache, inventory) and project
paths listed in a committed inventory file are trusted configuration and are not passed here.
"""
from __future__ import annotations

import os
from pathlib import Path


class OutsideWorkspace(ValueError):
    """A CLI path resolved outside the working directory."""


def workspace() -> str:
    return os.path.realpath(os.getcwd())


def safe_path(value: str | os.PathLike, what: str = "path") -> Path:
    """Resolve a CLI path (symlinks included) and require it to be inside the working directory."""
    base = workspace()
    full = os.path.realpath(os.path.join(base, os.fspath(value)))
    if full != base and not full.startswith(base + os.sep):
        raise OutsideWorkspace(
            f"{what} '{value}' is outside the working directory {base}. "
            "Run the command from that project's folder.")
    return Path(full)
