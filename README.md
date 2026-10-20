# DevOps Repository Auditing Agent

An autonomous, AI-powered DevOps auditing agent built in pure Python. It inspects public GitHub repositories for DevOps best-practice violations across security, CI/CD, repository hygiene, code quality, testing, dependencies, configuration, collaboration, and build/release engineering.

## Setup & Architecture Status
- **Phase 1 Complete**: Repository initialized, virtual environment configured, and dependencies installed.
- **Phase 2 Complete**: Core inspection tools implemented in `tools.py` (`list_files`, `read_file`, `search_code`, `git_log`, `run_ruff`).
- **Architecture**: Custom agentic tool-use loop (no LangChain / LangGraph).
