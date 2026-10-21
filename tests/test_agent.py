import json
import subprocess
from pathlib import Path

import pytest

import agent
from tools import RepositoryTools


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "app.py").write_text("print('ok')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "app.py"], check=True)
    return repo


def test_validate_repo_url_normalizes_git_suffix():
    assert agent.validate_repo_url("https://github.com/example/project.git/") == (
        "https://github.com/example/project"
    )


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:example/project.git",
        "https://gitlab.com/example/project",
        "https://github.com/example",
        "https://github.com/example/project/tree/main",
        "https://github.com/example/project?tab=readme",
    ],
)
def test_validate_repo_url_rejects_unsupported_urls(url):
    with pytest.raises(ValueError):
        agent.validate_repo_url(url)


def test_normalize_violations_enforces_schema_and_deduplicates(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    raw = [
        {
            "category": "code_quality",
            "severity": "medium",
            "file": "app.py",
            "line": 1,
            "description": "Maintainability issue",
            "evidence": "Confirmed evidence",
            "recommendation": "Refactor the statement",
        },
        {
            "category": "code_quality",
            "severity": "medium",
            "file": "app.py",
            "line": 1,
            "description": "Maintainability issue",
            "evidence": "Same issue, repeated",
            "recommendation": "Refactor the statement",
        },
        {
            "category": "not_a_category",
            "severity": "high",
            "description": "Invalid category",
            "evidence": "Evidence",
            "recommendation": "Fix it",
        },
        {
            "category": "security",
            "severity": "critical",
            "file": "missing.py",
            "line": 5,
            "description": "File not tracked",
            "evidence": "Evidence",
            "recommendation": "Fix it",
        },
    ]
    result = agent.normalize_violations(raw, tools)
    assert len(result) == 2
    assert result[0] == {
        "rule_id": "QUA-001",
        "category": "code_quality",
        "severity": "medium",
        "file": "app.py",
        "line": 1,
        "description": "Maintainability issue",
        "evidence": "Confirmed evidence",
        "recommendation": "Refactor the statement",
    }
    assert result[1]["file"] is None
    assert result[1]["line"] is None


def test_normalize_violations_does_not_drop_distinct_findings_on_same_line(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    base = {
        "category": "security",
        "severity": "medium",
        "file": "app.py",
        "line": 1,
        "evidence": "Different evidence",
        "recommendation": "Address it",
    }
    result = agent.normalize_violations(
        [
            {**base, "description": "First distinct issue"},
            {**base, "description": "Second distinct issue"},
        ],
        tools,
    )
    assert len(result) == 2
    assert [item["rule_id"] for item in result] == ["SEC-001", "SEC-002"]


def test_normalize_violations_never_returns_secret_value(tmp_path):
    tools = RepositoryTools(str(make_repo(tmp_path)))
    result = agent.normalize_violations(
        [
            {
                "category": "security",
                "severity": "high",
                "file": "app.py",
                "line": 1,
                "description": "Credential leak",
                "evidence": 'API_KEY = "supersecretvalue123"',
                "recommendation": "Use an environment variable",
            }
        ],
        tools,
    )
    assert result
    assert "supersecretvalue123" not in json.dumps(result)


def test_write_json_creates_parent_and_valid_json(tmp_path):
    target = tmp_path / "nested" / "report.json"
    agent.write_json(target, {"repository": "https://github.com/example/project", "violations": []})
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "repository": "https://github.com/example/project",
        "violations": [],
    }


def test_investigate_executes_llm_selected_tool_then_submits(monkeypatch):
    from types import SimpleNamespace

    calls = [
        SimpleNamespace(name="list_files", args={}),
        SimpleNamespace(name="search_code", args={"pattern": "password"}),
        SimpleNamespace(name="read_file", args={"path": "pyproject.toml"}),
        SimpleNamespace(name="submit_report", args={"violations": []}),
    ]

    responses = [
        SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[SimpleNamespace(function_call=call)]
                    )
                )
            ]
        )
        for call in calls
    ]
    requested_tools = []

    class FakePart:
        @staticmethod
        def from_function_response(name, response):
            return SimpleNamespace(name=name, response=response)

        @staticmethod
        def from_text(text):
            return SimpleNamespace(text=text)

    class FakeTools:
        def list_files(self):
            requested_tools.append("list_files")
            return ["app.py", "README.md"]

        def search_code(self, pattern, path_filter=""):
            requested_tools.append("search_code")
            return f"Search completed for pattern: {pattern}. No matches."

        def read_file(self, path, start_line=1, max_lines=400):
            requested_tools.append("read_file")
            return "[1] [tool.pytest.ini_options]"

    monkeypatch.setattr(agent, "_make_config", lambda force_submit=False: object())
    monkeypatch.setattr(agent, "_user_text", lambda text: SimpleNamespace(text=text))
    monkeypatch.setattr(agent.types, "Part", FakePart, raising=False)
    monkeypatch.setattr(
        agent.types,
        "Content",
        lambda **kwargs: SimpleNamespace(**kwargs),
        raising=False,
    )
    monkeypatch.setattr(agent, "call_model", lambda *args, **kwargs: responses.pop(0))

    trace = []
    result = agent.investigate(
        object(), "test-model", FakeTools(), "https://github.com/a/b", trace
    )

    assert result == []
    assert requested_tools == ["list_files", "search_code", "read_file"]
    assert [item["tool"] for item in trace] == [
        "list_files",
        "search_code",
        "read_file",
    ]
