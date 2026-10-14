import json, sqlite3, time
from research import WebResearch

def test_cached_results_return_without_network(tmp_path):
    db = str(tmp_path / "cache.sqlite3")
    research = WebResearch(db, ttl_seconds=60)
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO cache VALUES(?,?,?)", ("example query", time.time(), json.dumps([{"title":"T","url":"https://example.com","snippet":"S"}])))
    assert research.search("example query") == [{"title":"T","url":"https://example.com","snippet":"S"}]
