from __future__ import annotations

import time

import pytest

from task_manager import TaskManager


def make_manager(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("LLM_DEVOPS_TASK_DB", str(tmp_path / "state" / "tasks.sqlite3"))
    monkeypatch.setenv("LLM_DEVOPS_WORKTREE_ROOT", str(tmp_path / "worktrees"))
    manager = TaskManager(repo)
    return manager


def insert_task(manager, status="queued"):
    now = time.time()
    task_id = "test-task"
    with manager._connect() as con:
        con.execute(
            "INSERT INTO tasks(id,goal,include_web,status,created_at,updated_at) VALUES(?,?,?, ?,?,?)",
            (task_id, "test goal", 0, status, now, now),
        )
    return task_id


def test_task_state_persists_and_events_are_ordered(tmp_path, monkeypatch):
    manager = make_manager(tmp_path, monkeypatch)
    task_id = insert_task(manager)
    manager._event(task_id, "queued", {"goal": "test goal"})
    manager._event(task_id, "started", {"worker": 1})

    task = manager.get(task_id)
    assert task["goal"] == "test goal"
    assert task["status"] == "queued"
    events = manager.events(task_id)
    assert [event["event"] for event in events] == ["queued", "started"]
    assert manager.events(task_id, after=events[0]["seq"]) == events[1:]


def test_settle_refuses_to_remove_an_active_worktree(tmp_path, monkeypatch):
    manager = make_manager(tmp_path, monkeypatch)
    task_id = insert_task(manager, status="running")
    with pytest.raises(ValueError, match="active task"):
        manager.settle(task_id)


def test_snooze_and_resume_are_persisted(tmp_path, monkeypatch):
    manager = make_manager(tmp_path, monkeypatch)
    task_id = insert_task(manager, status="pr_open")
    snoozed = manager.snooze(task_id, 300)
    assert snoozed["snoozed_until"] > time.time()
    resumed = manager.resume(task_id)
    assert resumed["snoozed_until"] is None


def test_settle_hides_task_but_preserves_worktree(tmp_path, monkeypatch):
    manager = make_manager(tmp_path, monkeypatch)
    task_id = insert_task(manager, status="ready_for_review")
    worktree = tmp_path / "worktree-to-preserve"
    worktree.mkdir()
    manager._update(task_id, worktree=str(worktree), branch="agent/task-test")
    settled = manager.settle(task_id)
    assert settled["settled"] is True
    assert settled["status"] == "settled"
    assert worktree.exists()
    assert manager.list() == []
    assert manager.list(include_settled=True)[0]["id"] == task_id
