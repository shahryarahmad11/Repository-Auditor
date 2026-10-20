import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

class RepositoryTools:
    """Encapsulates safe inspection tools for a target repository directory."""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir).resolve()

    def _resolve_path(self, relative_path: str) -> Path:
        """Ensure path remains within target repo to prevent directory traversal."""
        target_path = (self.repo_dir / relative_path).resolve()
        if not str(target_path).startswith(str(self.repo_dir)):
            raise ValueError(f"Path traversal attempt blocked: {relative_path}")
        return target_path

    def list_files(self) -> List[str]:
        """Discover all files in the target repository relative to its root."""
        file_list = []
        for root, dirs, files in os.walk(self.repo_dir):
            # Skip hidden git directory
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.repo_dir)
                file_list.append(str(rel_path))
        return sorted(file_list)

    def read_file(self, relative_path: str, max_bytes: int = 100000) -> str:
        """Read text content of a target file with size limits."""
        try:
            file_path = self._resolve_path(relative_path)
            if not file_path.exists():
                return f"Error: File '{relative_path}' does not exist."
            if file_path.is_dir():
                return f"Error: '{relative_path}' is a directory."
            
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
                if file_path.stat().st_size > max_bytes:
                    content += f"\n... [Truncated: File exceeds {max_bytes} bytes]"
                return content
        except Exception as e:
            return f"Error reading file '{relative_path}': {str(e)}"

    def search_code(self, pattern: str) -> List[Dict[str, Any]]:
        """Search for regular expression patterns across repository files."""
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return [{"error": f"Invalid regex pattern: {str(e)}"}]

        for rel_file in self.list_files():
            file_path = self._resolve_path(rel_file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({
                                "file": rel_file,
                                "line": line_num,
                                "content": line.strip()
                            })
            except Exception:
                continue
        return matches[:50]  # Cap results to avoid overwhelming context window

    def git_log(self, max_commits: int = 10) -> str:
        """Inspect recent git commit history."""
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_dir), "log", f"-n{max_commits}", "--pretty=format:%h - %an, %ar : %s"],
                capture_output=True, text=True, timeout=10
            )
            return res.stdout if res.returncode == 0 else f"Git log error: {res.stderr}"
        except Exception as e:
            return f"Error running git log: {str(e)}"

    def run_ruff((self) -> str:
        """Run linter check on target repo safely."""
        try:
            res = subprocess.run(
                ["ruff", "check", str(self.repo_dir)],
                capture_output=True, text=True, timeout=15
            )
            return res.stdout if res.stdout else res.stderr
        except Exception as e:
            return f"Ruff execution skipped or failed: {str(e)}"
