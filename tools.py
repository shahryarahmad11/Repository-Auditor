"""Safe, read-only inspection tools for the DevOps auditing agent."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_FILES = 1000
MAX_READ_LINES = 400
MAX_LINE_CHARS = 300
MAX_FILE_BYTES = 1_000_000
MAX_SEARCH_RESULTS = 50
MAX_RUFF_CHARS = 3000

# Known credential formats that are always redacted.
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

# key = "value" style assignments for secret-looking names.
ASSIGNMENT_PATTERN = re.compile(
    r"((?:api[_-]?key|secret|token|passw(?:or)?d|pwd|private[_-]?key|access[_-]?key)"
    r"""[\w\-]*\s*[:=]\s*)(['"]?)([^\s'"#,;]{4,})(\2)""",
    re.IGNORECASE,
)

# Values that are references to a secret store, not the secret itself.
REFERENCE_PREFIX = re.compile(
    r"(os\.|env|\$\{|\$\(|process\.|secrets\.|getenv|config|settings|<|your_|\{\{)",
    re.IGNORECASE,
)

# Unquoted plain identifiers (no digits) are variable references, not secrets.
PLAIN_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_.\[\]()]*")


def _redact_assignment(match: re.Match[str]) -> str:
    quote, value = match.group(2), match.group(3)
    if REFERENCE_PREFIX.match(value):
        return match.group(0)
    if not quote and PLAIN_IDENTIFIER.fullmatch(value):
        return match.group(0)
    return f"{match.group(1)}{quote}[REDACTED]{match.group(4)}"


def redact(text: str) -> str:
    """Remove secret values from text so they never reach the LLM or the report."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return ASSIGNMENT_PATTERN.sub(_redact_assignment, text)


class RepositoryTools:
    """Read-only inspection tools for a cloned target repository."""

    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir).resolve()

    # ---------- internal helpers ----------

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a path and block anything outside the repository."""
        target = (self.repo_dir / relative_path).resolve()
        if not target.is_relative_to(self.repo_dir):
            raise ValueError(f"Path traversal attempt blocked: {relative_path}")
        return target

    def _git(self, *args: str, timeout: int = 20) -> subprocess.CompletedProcess:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        return subprocess.run(
            ["git", "-C", str(self.repo_dir), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )

    def _walk_files(self) -> list[str]:
        files = []
        for root, dirs, names in os.walk(self.repo_dir):
            if ".git" in dirs:
                dirs.remove(".git")
            for name in names:
                files.append(str((Path(root) / name).relative_to(self.repo_dir)))
        return sorted(files)

    def _tracked_files(self) -> list[str]:
        try:
            res = self._git("ls-files", "-z")
            if res.returncode == 0 and res.stdout:
                return sorted(p for p in res.stdout.split("\0") if p)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return self._walk_files()

    @staticmethod
    def _is_binary(path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                return b"\x00" in f.read(2048)
        except OSError:
            return True

    # ---------- tools exposed to the agent ----------

    def list_files(self) -> list[str]:
        """List files tracked in the repository (relative paths)."""
        files = self._tracked_files()
        if len(files) > MAX_FILES:
            extra = len(files) - MAX_FILES
            return [*files[:MAX_FILES], f"... [truncated: {extra} more files]"]
        return files

    def read_file(
        self, relative_path: str, start_line: int = 1, max_lines: int = MAX_READ_LINES
    ) -> str:
        """Read a text file with line numbers. Secrets are redacted."""
        try:
            start_line = max(1, int(start_line))
            max_lines = max(1, min(int(max_lines), MAX_READ_LINES))
            path = self._resolve_path(relative_path)
            if not path.exists():
                return f"Error: file '{relative_path}' does not exist."
            if path.is_dir():
                return f"Error: '{relative_path}' is a directory."
            if self._is_binary(path):
                return f"'{relative_path}' is a binary file; content not shown."

            out, truncated = [], False
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    if n < start_line:
                        continue
                    if len(out) >= max_lines:
                        truncated = True
                        break
                    text = redact(line.rstrip("\n")[:MAX_LINE_CHARS])
                    out.append(f"{n}: {text}")
            if truncated:
                out.append(f"... [truncated: continue with start_line={start_line + max_lines}]")
            return "\n".join(out) if out else "(empty file or start_line beyond end of file)"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file '{relative_path}': {e}"

    def search_code(self, pattern: str, path_filter: str = "") -> list[dict[str, Any]]:
        """Regex search (case-insensitive) across tracked files. Results are redacted."""
        if not isinstance(pattern, str) or not pattern or len(pattern) > 200:
            return [{"error": "Pattern must be a non-empty regex of at most 200 characters."}]
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return [{"error": f"Invalid regex pattern: {e}"}]

        matches: list[dict[str, Any]] = []
        for rel in self._tracked_files():
            if path_filter and path_filter.lower() not in rel.lower():
                continue
            try:
                path = self._resolve_path(rel)
                if (
                    not path.is_file()
                    or path.stat().st_size > MAX_FILE_BYTES
                    or self._is_binary(path)
                ):
                    continue
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for n, line in enumerate(f, 1):
                        if regex.search(line[:1000]):
                            matches.append(
                                {
                                    "file": rel,
                                    "line": n,
                                    "content": redact(line.strip()[:MAX_LINE_CHARS]),
                                }
                            )
                            if len(matches) >= MAX_SEARCH_RESULTS:
                                return matches
            except (OSError, ValueError):
                continue
        return matches

    def git_log(self, max_commits: int = 20) -> str:
        """Recent commit history: hash | author | date | subject."""
        try:
            max_commits = max(1, min(int(max_commits), 50))
            res = self._git(
                "log",
                f"-n{max_commits}",
                "--date=short",
                "--pretty=format:%h | %an | %ad | %s",
            )
            if res.returncode != 0:
                return f"Git log error: {res.stderr.strip()}"
            return redact(res.stdout) or "(no commits found)"
        except Exception as e:
            return f"Error running git log: {e}"

    def run_ruff(self) -> str:
        """Static lint check. Does not execute repository code or write a cache."""
        try:
            res = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--no-cache",
                    "--isolated",
                    "--output-format",
                    "concise",
                    str(self.repo_dir),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "Ruff check timed out; result unavailable."
        except OSError as e:
            return f"Ruff could not be run: {e}"
        if "No module named ruff" in res.stderr:
            return "Ruff is not installed in this environment; lint check unavailable."
        if res.returncode == 0:
            return "Ruff: no issues found."
        out = (res.stdout or res.stderr).replace(str(self.repo_dir) + os.sep, "")
        return redact(out[:MAX_RUFF_CHARS])