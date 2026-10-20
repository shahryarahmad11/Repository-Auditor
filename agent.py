import os
import sys
import json
import argparse
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import RepositoryTools

load_dotenv()

SYSTEM_PROMPT = """
You are an expert DevOps Repository Security & Architecture Auditor.
Your job is to thoroughly inspect a target repository using the tools provided and discover any DevOps violations.

Cover the following 9 categories during your investigation:
1. Repository hygiene (missing README, missing/unsuitable .gitignore, tracked generated files)
2. Dependency management (inconsistent specs, missing lockfiles, loose version bounds)
3. Code quality (missing linting/formatting, clear maintainability issues)
4. Testing (missing tests, failing tests, lack of test execution setup)
5. GitHub Actions / CI (incorrect triggers, ineffective gates, skipped validation)
6. Security (exposed credentials, hardcoded secrets, unsafe permissions)
7. Configuration (machine-specific paths, committed local settings, poor env separation)
8. Collaboration (unsafe PR automation, missing review/contribution guidance)
9. Build and release (missing build validation, risky deployment automation)

CRITICAL RULES:
- Do NOT assume a defect without concrete evidence.
- Do NOT treat absent optional tools as defects if valid alternatives exist.
- Never output real secret strings in findings.
- Ensure all findings match the exact schema required.
"""

def clone_repo(repo_url: str, target_dir: str):
    import subprocess
    res = subprocess.run(["git", "clone", "--depth", "1", repo_url, target_dir], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {res.stderr}")

def run_agent_audit(repo_url: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    client = genai.Client(api_key=api_key)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        clone_repo(repo_url, tmp_dir)
        tools = RepositoryTools(tmp_dir)

        # Map tool names to execution functions
        available_tools = {
            "list_files": tools.list_files,
            "read_file": tools.read_file,
            "search_code": tools.search_code,
            "git_log": tools.git_log,
            "run_ruff": tools.run_ruff,
        }

        # Step 1: Initial tool execution
        files = tools.list_files()
        ruff_out = tools.run_ruff()
        glog = tools.git_log()

        # Step 2: Query model for analysis
        prompt = f"""
Target Repo: {repo_url}
Discovered Files: {json.dumps(files[:100])}
Recent Commits:\n{glog}
Ruff Output:\n{ruff_out[:2000]}

Please review these initial outputs and identify all genuine DevOps violations across the 9 auditing categories.
Respond with a JSON array of violation objects matching this format:
[
  {{
    "rule_id": "SEC-001",
    "category": "security",
    "severity": "critical",
    "file": "path/to/file.py",
    "line": 10,
    "description": "Short explanation",
    "evidence": "Concrete proof from code/config",
    "recommendation": "Remediation step"
  }}
]
Allowed severity values: critical, high, medium, low. Use null for non-file/line issues.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )

        try:
            violations = json.loads(response.text)
            return violations if isinstance(violations, list) else []
        except Exception:
            return []

def main():
    parser = argparse.ArgumentParser(description="DevOps Repository Auditing Agent")
    parser.add_argument("--repo", required=True, help="Public GitHub Repository URL")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    try:
        violations = run_agent_audit(args.repo)
        report = {
            "repository": args.repo,
            "violations": violations
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Audit completed successfully. Report written to {args.output}")
    except Exception as e:
        print(f"Fatal error during audit execution: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
