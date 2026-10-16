"""Security utilities for workspace path validation and file access control."""
from pathlib import Path


class UnsafePathError(Exception):
    """Raised when a file path escapes the configured workspace boundary."""
    pass


class Workspace:
    """Small workspace facade shared by the autonomous coding harness."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise ValueError(f"Workspace root is not a directory: {self.root}")

    def resolve(self, relative_path: str) -> Path:
        return resolve_safe_path(self.root, relative_path)

    def read_text(self, relative_path: str, max_bytes: int = 1_000_000) -> str:
        return read_workspace_file(self.root, relative_path, max_bytes=max_bytes)

    def write_text(self, relative_path: str, content: str, max_bytes: int = 1_000_000) -> None:
        write_workspace_file(self.root, relative_path, content, max_bytes=max_bytes)


def resolve_safe_path(workspace_root: Path | str, target_path: str) -> Path:
    """Resolve target_path relative to workspace_root and ensure it stays within bounds."""
    root = Path(workspace_root).resolve()
    target = (root / target_path).resolve()
    
    try:
        target.relative_to(root)
    except ValueError:
        raise UnsafePathError(
            f"Path traversal blocked: '{target_path}' is outside workspace '{root}'"
        ) from None
    
    return target


def read_workspace_file(workspace_root: Path | str, target_path: str, max_bytes: int = 1_000_000) -> str:
    """Safely read a text file within the workspace bounds."""
    safe_path = resolve_safe_path(workspace_root, target_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {target_path}")
    if not safe_path.is_file():
        raise ValueError(f"Path is not a regular file: {target_path}")
    if safe_path.stat().st_size > max_bytes:
        raise ValueError(f"File size exceeds limit of {max_bytes} bytes")
    
    return safe_path.read_text(encoding="utf-8")


def write_workspace_file(workspace_root: Path | str, target_path: str, content: str, max_bytes: int = 1_000_000) -> None:
    """Safely write content to a file within the workspace bounds."""
    safe_path = resolve_safe_path(workspace_root, target_path)
    if len(content.encode("utf-8")) > max_bytes:
        raise ValueError(f"Content exceeds limit of {max_bytes} bytes")
    
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")