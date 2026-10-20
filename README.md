# DevOps Repository Auditing Agent

An autonomous, AI-powered DevOps auditing agent built in pure Python. It inspects public GitHub repositories for DevOps best-practice violations across security, CI/CD, repository hygiene, code quality, testing, dependencies, configuration, collaboration, and build/release engineering.

## Setup & Architecture Status
- **Phase 1 Complete**: Repository initialized, virtual environment configured, and dependencies installed.
- **Phase 2 Complete**: Core inspection tools implemented in `tools.py` (`list_files`, `read_file`, `search_code`, `git_log`, `run_ruff`).
- **Phase 3 Complete**: Agent loop and CLI interface implemented in `agent.py`.
- **Architecture**: Custom agentic tool-use loop using native Gemini SDK (no LangChain / LangGraph).

## Execution
```bash
python agent.py --repo <github_repository_url> --output report.json
