import json
from pathlib import Path

from orchestrator import validate_code, extract_code


def test_valid_json(tmp_path):
    assert validate_code(tmp_path / "x.json", json.dumps({"ok": True}))[0]


def test_invalid_json(tmp_path):
    assert not validate_code(tmp_path / "x.json", '{"ok":')[0]


def test_valid_python(tmp_path):
    assert validate_code(tmp_path / "x.py", "def f():\n    return 1\n")[0]


def test_invalid_python(tmp_path):
    assert not validate_code(tmp_path / "x.py", "def f(:\n")[0]


def test_extract_one_code_block():
    assert extract_code("```python\nprint('ok')\n```") == "print('ok')\n"


def test_reject_multiple_code_blocks():
    import pytest
    with pytest.raises(ValueError):
        extract_code("```js\none()\n```\n```js\ntwo()\n```")
