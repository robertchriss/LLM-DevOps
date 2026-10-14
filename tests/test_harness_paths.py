import pytest
from harness import CodingHarness

def test_rejects_parent_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False)
    with pytest.raises(ValueError):
        h._safe_relative("../outside.py")

def test_rejects_absolute_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False)
    with pytest.raises(ValueError):
        h._safe_relative(str((tmp_path.parent / "outside.py").resolve()))

def test_accepts_repo_relative_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False)
    assert h._safe_relative("src/main.py") == "src/main.py"
