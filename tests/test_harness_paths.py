import pytest
from harness import CodingHarness

def test_rejects_parent_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False, rag_db_path=tmp_path / "rag.sqlite3", research_db_path=tmp_path / "webcache.sqlite3")
    with pytest.raises(ValueError):
        h._safe_relative("../outside.py")

def test_rejects_absolute_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False, rag_db_path=tmp_path / "rag.sqlite3", research_db_path=tmp_path / "webcache.sqlite3")
    with pytest.raises(ValueError):
        h._safe_relative(str((tmp_path.parent / "outside.py").resolve()))

def test_accepts_repo_relative_path(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False, rag_db_path=tmp_path / "rag.sqlite3", research_db_path=tmp_path / "webcache.sqlite3")
    assert h._safe_relative("src/main.py") == "src/main.py"


def test_normalizes_windows_relative_paths(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False, rag_db_path=tmp_path / "rag.sqlite3", research_db_path=tmp_path / "webcache.sqlite3")
    assert h._safe_relative(r"src\main.py") == "src/main.py"


def test_extracts_json_from_fenced_model_response(tmp_path):
    h = CodingHarness(tmp_path, "http://localhost:11434", "fake", use_judge=False, rag_db_path=tmp_path / "rag.sqlite3", research_db_path=tmp_path / "webcache.sqlite3")
    parsed = h._extract_json('Plan follows:\n```json\n{"tasks": [{"id": "T1", "files": ["src/main.py"]}], "summary": "ok"}\n```')
    assert parsed == {"tasks": [{"id": "T1", "files": ["src/main.py"]}], "summary": "ok"}
