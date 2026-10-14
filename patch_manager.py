from __future__ import annotations
from pathlib import Path
from security import Workspace

class PatchManager:
    """Small reusable path-guarded file writer. CodingHarness performs staged atomic writes itself."""
    def __init__(self, root):
        self.workspace = Workspace(root)
    def write(self, relative_path: str, content: str) -> Path:
        target = self.workspace.resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target
