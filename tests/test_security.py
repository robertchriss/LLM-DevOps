import pytest
from security import UnsafePathError, read_workspace_file, write_workspace_file


def test_write_and_read_workspace_file(tmp_path):
    write_workspace_file(tmp_path, "src/example.txt", "hello")
    assert read_workspace_file(tmp_path, "src/example.txt") == "hello"


@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", ""])
def test_rejects_unsafe_paths(tmp_path, path):
    with pytest.raises((UnsafePathError, ValueError)):
        write_workspace_file(tmp_path, path, "no")


def test_rejects_symlink_escape(tmp_path):
    import os

    from security import resolve_workspace_path

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside_file = tmp_path / "outside-secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    link = workspace / "escape"

    try:
        os.symlink(outside_file, link)
    except (OSError, NotImplementedError) as exc:
        import pytest

        pytest.skip(f"Symlink creation is unavailable on this system: {exc}")

    with pytest.raises((ValueError, PermissionError)):
        resolve_workspace_path(workspace, "escape")