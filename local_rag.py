from __future__ import annotations
import re, sqlite3
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", "dist", "build"}
ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".sql", ".sh"}
SECRET_WORDS = ("password", "secret", "api_key", "token", "private_key")

def _connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    return con

class LocalRAG:
    def __init__(self, root, db_path=".llm_devops_rag.sqlite3", chunk_chars=1400):
        self.root = Path(root).resolve()
        db = Path(db_path)
        if not db.is_absolute(): db = self.root / db
        db.parent.mkdir(parents=True, exist_ok=True)
        self.db_path, self.chunk_chars = str(db), chunk_chars
        with _connect(self.db_path) as con:
            con.execute("CREATE TABLE IF NOT EXISTS chunks(path TEXT NOT NULL, chunk INTEGER NOT NULL, text TEXT NOT NULL, PRIMARY KEY(path,chunk))")
            try:
                con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(path UNINDEXED, chunk UNINDEXED, text)")
                self.fts = True
            except sqlite3.OperationalError: self.fts = False

    def _safe_path(self, relative):
        path = (self.root / relative).resolve()
        if path != self.root and self.root not in path.parents: raise ValueError("Path escapes workspace")
        return path

    def _ignored(self, path):
        return any(part in SKIP_DIRS for part in path.relative_to(self.root).parts) or path.name.startswith(".llm_devops_")

    def index_file(self, relative):
        path = self._safe_path(relative)
        if not path.is_file() or self._ignored(path) or path.suffix.lower() not in ALLOWED_SUFFIXES: return 0
        if any(word in path.name.lower() for word in SECRET_WORDS): return 0
        try: text = path.read_text(encoding="utf-8", errors="replace")
        except OSError: return 0
        if len(text) > 1_000_000: return 0
        rel = path.relative_to(self.root).as_posix()
        chunks = [text[i:i+self.chunk_chars] for i in range(0, len(text), self.chunk_chars)] or [""]
        with _connect(self.db_path) as con:
            con.execute("DELETE FROM chunks WHERE path=?", (rel,))
            if self.fts: con.execute("DELETE FROM chunks_fts WHERE path=?", (rel,))
            for i, chunk in enumerate(chunks):
                con.execute("INSERT INTO chunks VALUES(?,?,?)", (rel, i, chunk))
                if self.fts: con.execute("INSERT INTO chunks_fts VALUES(?,?,?)", (rel, i, chunk))
        return len(chunks)

    def index_workspace(self):
        count = 0
        for path in self.root.rglob("*"):
            if path.is_file() and not self._ignored(path) and path.suffix.lower() in ALLOWED_SUFFIXES:
                count += bool(self.index_file(path.relative_to(self.root).as_posix()))
        return int(count)

    def search(self, query, limit=5):
        terms = re.findall(r"[A-Za-z0-9_]{2,}", query.lower())
        if not terms: return []
        with _connect(self.db_path) as con:
            if self.fts:
                match = " OR ".join('"' + t.replace('"', '""') + '"' for t in terms[:12])
                try:
                    rows = con.execute("SELECT path,chunk,text,bm25(chunks_fts) score FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?", (match, limit)).fetchall()
                    return [dict(r) for r in rows]
                except sqlite3.OperationalError: pass
            rows = con.execute("SELECT path,chunk,text FROM chunks").fetchall()
        scored = []
        for row in rows:
            hay = (row["path"] + " " + row["text"]).lower()
            score = sum(hay.count(t) for t in terms)
            if score: scored.append((score, dict(row)))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
