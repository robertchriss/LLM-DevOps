"""Workspace-scoped file access helpers for LLM-DevOps.

Path checks are defense-in-depth, not a sandbox. Run generated code and the API
under an unprivileged OS account/container with limited filesystem permissions.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


class UnsafePathError(ValueError):
    """Raised when a requested path is outside the configured workspace."""


def resolve_workspace_path(root: str | Path, supplied_path: str) -> Path:
    workspace = Path(root).resolve(strict=True)
    if not isinstance(supplied_path, str) or not supplied_path.strip():
        raise UnsafePathError("A relative file path is required.")
    if "\x00" in supplied_path:
        raise UnsafePathError("NUL bytes are not allowed in paths.")

    candidate = Path(supplied_path)
    if candidate.is_absolute():
        raise UnsafePathError("Absolute paths are not allowed.")

    resolved = (workspace / candidate).resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError:
        raise UnsafePathError("Path escapes the configured workspace.") from None
    return resolved


def read_workspace_file(
    root: str | Path, supplied_path: str, *, max_bytes: int = 1_000_000
) -> str:
    path = resolve_workspace_path(root, supplied_path)
    if not path.is_file():
        raise FileNotFoundError(supplied_path)
    if path.stat().st_size > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes}-byte read limit.")
    # The workspace should be owned by the service account and not writable by
    # untrusted users. Use OS/container isolation for stronger race protection.
    return path.read_text(encoding="utf-8")


def write_workspace_file(
    root: str | Path,
    supplied_path: str,
    content: str,
    *,
    max_bytes: int = 1_000_000,
) -> Path:
    if not isinstance(content, str):
        raise TypeError("File content must be a string.")
    if len(content.encode("utf-8")) > max_bytes:
        raise ValueError(f"Content exceeds the {max_bytes}-byte write limit.")

    path = resolve_workspace_path(root, supplied_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = resolve_workspace_path(root, supplied_path)

    # Atomic replacement prevents partially written files. This still assumes
    # no untrusted local user can race modifications inside the workspace.
    fd, temp_name = tempfile.mkstemp(prefix=".llm-devops-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        resolve_workspace_path(root, supplied_path)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return path
