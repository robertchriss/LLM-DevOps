import pytest
from security import Workspace

def test_write_and_read(tmp_path):
    ws = Workspace(tmp_path)
    ws.write_text("src/main.py", "print('ok')")
    assert ws.read_text("src/main.py") == "print('ok')"

def test_reject_parent_traversal(tmp_path):
    with pytest.raises(ValueError): Workspace(tmp_path).resolve("../outside.txt")

def test_reject_absolute_path(tmp_path):
    with pytest.raises(ValueError): Workspace(tmp_path).resolve(str((tmp_path.parent / "outside.txt").resolve()))
