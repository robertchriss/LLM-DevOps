
from pathlib import Path


class UnsafePathError(ValueError):
    pass


def resolve_project_path(root: Path, supplied_path: str) -> Path:
    """Resolve a path and reject paths outside the project root."""
    root = root.resolve(strict=True)

    if not supplied_path or "\x00" in supplied_path:
        raise UnsafePathError("Invalid path")

    candidate = Path(supplied_path)

    if candidate.is_absolute():
        raise UnsafePathError("Absolute paths are not allowed")

    resolved = (root / candidate).resolve(strict=False)

    try:
        resolved.relative_to(root)
    except ValueError:
        raise UnsafePathError("Path escapes project root") from None

    return resolved


def read_project_file(root: Path, supplied_path: str) -> str:
    path = resolve_project_path(root, supplied_path)

    if not path.is_file():
        raise FileNotFoundError(supplied_path)

    return path.read_text(encoding="utf-8")


def write_project_file(
    root: Path, supplied_path: str, content: str
) -> None:
    path = resolve_project_path(root, supplied_path)

    if path.exists() and path.is_symlink():
        raise UnsafePathError("Symlink writes are not allowed")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
