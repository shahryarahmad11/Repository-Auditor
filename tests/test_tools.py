import subprocess
from pathlib import Path

import pytest

from tools import RepositoryTools, redact


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "app.py").write_text(
        'API_KEY = "supersecretvalue123"\n'
        'password = "anothersecretvalue"\n'
        'print("hello")\n',
        encoding="utf-8",
    )
    (repo / "notes.txt").write_text("first line\nsecond line\nthird line\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "app.py", "notes.txt"], check=True)
    return repo


def test_redact_known_token_and_secret_assignment():
    text = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd"\nAPI_KEY="supersecretvalue123"'
    safe = redact(text)
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in safe
    assert "supersecretvalue123" not in safe
    assert "[REDACTED]" in safe


def test_redact_multiline_private_key():
    private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "private-key-material-that-must-not-leak\n"
        "-----END PRIVATE KEY-----"
    )
    safe = redact(private_key)
    assert "private-key-material-that-must-not-leak" not in safe
    assert safe == "[REDACTED]"


def test_read_file_redacts_secrets_and_keeps_line_numbers(tmp_path):
    repo = make_repo(tmp_path)
    tools = RepositoryTools(str(repo))
    result = tools.read_file("app.py")
    assert "1: API_KEY = \"[REDACTED]\"" in result
    assert "supersecretvalue123" not in result
    assert "3: print(\"hello\")" in result


def test_read_file_supports_line_ranges(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    assert tools.read_file("notes.txt", start_line=2, max_lines=1) == (
        "2: second line\n... [truncated: continue with start_line=3]"
    )


def test_path_traversal_is_blocked(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    outside = tmp_path / "outside.txt"
    outside.write_text("do not read", encoding="utf-8")
    result = tools.read_file("../outside.txt")
    assert "Path traversal attempt blocked" in result
    with pytest.raises(ValueError):
        tools._resolve_path("../outside.txt")


def test_search_code_returns_redacted_line_content(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    matches = tools.search_code("API_KEY")
    assert matches
    assert matches[0]["file"] == "app.py"
    assert matches[0]["line"] == 1
    assert "supersecretvalue123" not in matches[0]["content"]
    assert "[REDACTED]" in matches[0]["content"]


def test_invalid_regex_is_reported_without_crashing(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    result = tools.search_code("[")
    assert result and "Invalid regex" in result[0]["error"]
