<div align="center">

# 🛡️ AI-Powered DevOps Repository Auditing Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An autonomous, AI-driven DevOps auditing agent that inspects public GitHub repositories, detects best-practice violations, and generates structured, evidence-based reports with actionable recommendations.

[Features](#features--audit-scope) · [Architecture](#architecture--design) · [Setup](#installation--setup) · [Usage](#usage--cli-interface) · [Testing](#testing) · [Sample Report](#sample-report-output)

</div>

---

## Table of Contents

- [Features & Audit Scope](#features--audit-scope)
- [Architecture & Design](#architecture--design)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage & CLI Interface](#usage--cli-interface)
- [Testing](#testing)
- [Sample Report Output](#sample-report-output)

---

## Features & Audit Scope

The agent autonomously audits 9 core DevOps areas. Click any area to expand its details.

<details>
<summary><b>1. Repository Hygiene</b></summary>

Missing README, improper `.gitignore`, committed temporary/generated files.
</details>

<details>
<summary><b>2. Dependency Management</b></summary>

Weak constraints, missing lockfiles, spec inconsistencies.
</details>

<details>
<summary><b>3. Code Quality</b></summary>

Missing linting/formatting configs, obvious code maintainability flaws.
</details>

<details>
<summary><b>4. Testing</b></summary>

Missing unit/integration tests, failing test runs, lack of CI test setup.
</details>

<details>
<summary><b>5. GitHub Actions / CI</b></summary>

Incorrect workflow triggers, missing quality gates, skipped checks.
</details>

<details>
<summary><b>6. Security</b></summary>

Hardcoded secrets/credentials, exposed keys, overly permissive action tokens.
</details>

<details>
<summary><b>7. Configuration</b></summary>

Machine-specific file paths, hardcoded local settings, environment leakage.
</details>

<details>
<summary><b>8. Collaboration</b></summary>

Missing PR templates, unsafe PR automation, absent review guidelines.
</details>

<details>
<summary><b>9. Build & Release</b></summary>

Absent build validation, risky release steps, insecure artifact handling.
</details>

---

## Architecture & Design

- **Pure Python Control Loop**: Implements a custom agent loop using Google's native Gemini SDK, without third-party agent orchestration frameworks (such as LangChain or LangGraph).
- **Tool Isolation**: Clones target repositories into isolated temporary workspaces and restricts file traversal safely.
- **Strict Evidence Verification**: Guarantees zero secret reproduction in outputs and enforces schema validation for JSON reports.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **OS** | Linux, macOS, or Windows via WSL (Ubuntu recommended) |
| **Python** | `3.10` or higher |
| **Git** | Installed and configured locally |
| **API Key** | Google Gemini API key from [Google AI Studio](https://aistudio.google.com/) |

---

## Installation & Setup

Run the following commands in your terminal to set up the project environment.

**1. Clone the repository**

```bash
git clone https://github.com/shahryarahmad11/Repository-Auditor.git
cd Repository-Auditor
```

**2. Create and activate a virtual environment**

<details open>
<summary><b>Linux / macOS / WSL</b></summary>

```bash
python3 -m venv venv
source venv/bin/activate
```
</details>

<details>
<summary><b>Windows PowerShell</b></summary>

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
</details>

**3. Upgrade pip and install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

1. Obtain a Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).

2. Create a `.env` file in the root directory by copying `.env.example`:

   ```bash
   cp .env.example .env
   ```

3. Open `.env` and add your API key:

   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

> **Note:** `.env` is listed in `.gitignore` and will never be committed to Git.

---

## Usage & CLI Interface

Run the auditing agent against any public GitHub repository:

```bash
python agent.py --repo <GITHUB_REPOSITORY_URL> --output report.json
```

| Flag | Description |
|------|-------------|
| `--repo` | URL of the public GitHub repository to audit |
| `--output` | Path of the JSON report file to generate |

<details>
<summary><b>Example command</b></summary>

```bash
python agent.py --repo https://github.com/shahryarahmad11/Repository-Auditor --output sample_report.json
```
</details>

---

## Testing

Run the automated tests to verify agent functionality and tool logic:

```bash
pytest
```

---

## Sample Report Output

<details open>
<summary><b>Click to expand / collapse the sample JSON report</b></summary>

```json
{
  "repository": "https://github.com/example/demo-project",
  "violations": [
    {
      "rule_id": "SEC-001",
      "category": "security",
      "severity": "critical",
      "file": "config.py",
      "line": 17,
      "description": "Hardcoded API credential",
      "evidence": "Credential assigned directly in source code",
      "recommendation": "Use a secrets manager or environment variable"
    }
  ]
}
```
</details>

<div align="right">

[⬆ Back to top](#-ai-powered-devops-repository-auditing-agent)

</div>