import os
from pathlib import Path

import pytest

from codeagent.workspace import Workspace, MAX_FILE_BYTES, new_project


@pytest.fixture
def ws(tmp_path):
    return Workspace(new_project(tmp_path, "test-project"))


@pytest.mark.parametrize("path", ["../outside.txt", "dir/../../x", "/abs", "C:/file", "C:file", "\\\\server\\share\\a", ".agent/report.json", ".AGENT/x", ".git/config", "a/../b", "a//b", "CON", "aux.txt", "dir/NUL.py", "x:stream", "a.", "a ", "x\x00y", "a?b"])
def test_rejects_unsafe_windows_paths(ws, path):
    with pytest.raises(ValueError):
        ws.write(path, "bad")


def test_write_read_replace_and_search(ws):
    ws.write("src/main.py", "answer = 42\n")
    assert ws.read("src/main.py") == "answer = 42\n"
    ws.replace("src/main.py", "42", "43")
    assert ws.search("43")[0]["line"] == 1
    with pytest.raises(ValueError):
        ws.replace("src/main.py", "42", "44")
    assert ws.files() == ["src/main.py"]


def test_hard_links_rejected(ws, tmp_path):
    target = tmp_path / "original.txt"
    target.write_text("untouched")
    os.link(target, ws.root / "linked.txt")
    with pytest.raises(ValueError):
        ws.write("linked.txt", "overwrite")
    assert target.read_text() == "untouched"


def test_symlink_rejected(ws, tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    try:
        (ws.root / "link").symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink permission unavailable")
    with pytest.raises(ValueError):
        ws.write("link/stolen.txt", "no")


def test_size_limit(ws):
    with pytest.raises(ValueError):
        ws.write("large.txt", "x" * (MAX_FILE_BYTES + 1))


def test_static_validation_distinguishes_structure_from_behavior(ws):
    assert not ws.check()["passed"]
    ws.write("README.md", "# Project\n")
    ws.write("requirements.txt", "# stdlib\n")
    ws.write("app.py", "def broken(:\n")
    ws.write("tests/test_app.py", "import unittest\n")
    assert len(ws.check()["syntax_errors"]) == 1
    ws.write("app.py", "answer = 42\n")
    assert ws.check()["passed"]
    ws.write("config.json", "{broken}")
    assert not ws.check()["passed"]


def test_new_runs_do_not_overwrite_existing_files(tmp_path):
    one, two = new_project(tmp_path, "demo"), new_project(tmp_path, "demo")
    assert one != two
    assert one.is_dir() and two.is_dir()
