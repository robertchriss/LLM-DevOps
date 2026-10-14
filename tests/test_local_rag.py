from local_rag import LocalRAG

def test_index_and_search(tmp_path):
    (tmp_path / "README.md").write_text("The harness runs pytest and checks application health.", encoding="utf-8")
    rag = LocalRAG(tmp_path, "test.sqlite3")
    assert rag.index_workspace() == 1
    results = rag.search("pytest application health", 3)
    assert results and results[0]["path"] == "README.md"

def test_ignores_node_modules(tmp_path):
    dep = tmp_path / "node_modules" / "dep"
    dep.mkdir(parents=True)
    (dep / "README.md").write_text("do not index", encoding="utf-8")
    assert LocalRAG(tmp_path, "test.sqlite3").index_workspace() == 0
