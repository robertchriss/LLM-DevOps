import json, sqlite3, time

class WebResearch:
    """DuckDuckGo text search with SQLite TTL cache; results are untrusted."""
    def __init__(self, db_path=".llm_devops_webcache.sqlite3", ttl_seconds=3600):
        self.db_path, self.ttl_seconds = db_path, ttl_seconds
        with sqlite3.connect(self.db_path) as con:
            con.execute("CREATE TABLE IF NOT EXISTS cache(query TEXT PRIMARY KEY, created REAL, payload TEXT)")

    def search(self, query, limit=5):
        query = query.strip()[:500]
        if not query: return []
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT created,payload FROM cache WHERE query=?", (query,)).fetchone()
            if row and time.time() - row[0] < self.ttl_seconds: return json.loads(row[1])[:limit]
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise RuntimeError("Install the ddgs dependency from requirements-rag.txt") from exc
        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=limit):
                results.append({"title": str(item.get("title", "")), "url": str(item.get("href", item.get("url", ""))),
                                "snippet": str(item.get("body", item.get("snippet", "")) )})
        with sqlite3.connect(self.db_path) as con:
            con.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (query, time.time(), json.dumps(results)))
        return results
