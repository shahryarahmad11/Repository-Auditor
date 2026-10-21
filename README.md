# Repository Auditor — AI-Powered DevOps Repository Auditing Agent

An AI-powered DevOps repository auditing agent that examines GitHub repositories, investigates potential engineering and configuration issues, and produces structured, evidence-based audit reports with actionable recommendations.

Unlike a fixed checklist that runs the same inspections against every repository, Repository Auditor uses an LLM-driven tool-calling loop to select inspection tools based on the information observed, investigate relevant files, and gather additional evidence before submitting its findings.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture and Agent Workflow](#architecture-and-agent-workflow)
- [Available Tools](#available-tools)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Audit Report Format](#audit-report-format)
- [Running Tests](#running-tests)
- [Continuous Integration](#continuous-integration)
- [Security and Safety](#security-and-safety)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

Repository Auditor is designed to help developers identify potential DevOps and repository-maintenance issues in software projects hosted on GitHub.

The agent uses a language model to investigate repository contents through a collection of Python inspection tools. It can inspect files, search source code, examine Git history, and run supported static-analysis checks. Based on its observations, it can select further tools to investigate potential findings before producing a JSON report.

The project is implemented in Python with an explicit agent/tool-calling loop rather than relying on an agent orchestration framework.

### Project Goals

- Automate repository inspection and DevOps auditing.
- Use observations to guide inspection-tool selection.
- Support follow-up investigations when additional evidence is needed.
- Produce structured findings with evidence and remediation guidance.
- Validate and normalize model-generated findings before reporting them.
- Handle repository inspection errors without unnecessarily terminating the audit.
- Avoid executing untrusted repository code as part of the inspection workflow.

## Key Features

### Dynamic Tool Selection

The language model chooses from the available inspection tools according to the repository information it receives. The agent processes tool calls, returns their results to the model, and supports additional investigation steps before report submission.

### Evidence-Based Findings

Reported violations contain supporting evidence and a recommended remediation. The agent normalizes findings, validates relevant file and line references, and removes duplicate findings.

### Repository Inspection

The agent can enumerate files, inspect file contents, search for patterns, examine Git history, and run Ruff where supported by the implementation.

### Secret Redaction

The inspection tools apply pattern-based redaction to recognized credential formats and secret-like assignments before returning matching content. This reduces the risk of exposing credentials in tool output and reports.

Redaction is not guaranteed to detect every possible secret format.

### Structured JSON Reports

Each completed audit produces a JSON report containing the repository URL and a list of normalized violations. Reports can be consumed by scripts, CI workflows, dashboards, or other automation.

### Trace Support

An optional trace file records tool-call activity to help developers inspect the agent's investigation process and troubleshoot its behavior.

### Automated Testing and CI

The project includes automated tests for agent behavior, repository inspection tools, input validation, secret redaction, and other important functionality. GitHub Actions runs linting and tests across supported Python versions configured in the workflow.

## Architecture and Agent Workflow

Repository Auditor follows an explicit Python agent/tool-calling architecture.

```text
GitHub Repository URL
        |
        v
Validate Repository URL
        |
        v
Clone Repository into a Temporary Workspace
        |
        v
Initialize the AI Agent
        |
        v
Observe Repository Information
        |
        v
Model Selects an Inspection Tool
        |
        v
Execute Tool and Return Its Results
        |
        v
Model Evaluates the New Evidence
        |
        +----> Select Another Tool if Needed
        |
        v
Submit Proposed Findings
        |
        v
Validate and Normalize Findings
        |
        v
Write JSON Audit Report
```

The agent can perform multiple investigation steps. Its next tool call depends on the information returned from earlier inspections, rather than following only a predetermined sequence.

### Main Components

**`agent.py`**

Responsible for the agent workflow, model interaction, tool-call handling, violation normalization, report generation, and command-line interface.

**`tools.py`**

Implements repository inspection tools, including file enumeration, bounded file reading, code searching, Git history inspection, static-analysis integration, and report-submission support.

**`tests/`**

Contains automated tests covering the agent and inspection tools.

**`.github/workflows/ci.yml`**

Defines the GitHub Actions workflow for linting and automated testing.

**`sample_report.json`**

Provides an illustrative example of the JSON report format. It is not evidence of an actual audit of the example repository.

## Available Tools

The agent exposes inspection capabilities through Python functions that it can select during its investigation.

| Tool | Purpose |
|---|---|
| `list_files()` | Enumerates repository files for initial discovery. |
| `read_file(path)` | Reads repository file content with bounded reading and redaction. |
| `search_code(pattern)` | Searches repository files using a regular expression and returns matching locations. |
| `git_log()` | Retrieves Git history information for repository investigation. |
| `run_ruff()` | Runs Ruff static-analysis checks where supported. |
| `submit_report(violations)` | Submits proposed findings for report validation and normalization. |

Tool arguments and return values are handled by the Python agent. The available inspection results inform subsequent model decisions.

The agent may choose different tools or make follow-up calls depending on the repository and the evidence discovered.

## Project Structure

```text
Repository-Auditor/
├── .github/
│   └── workflows/
│       └── ci.yml
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   └── test_tools.py
├── .env.example
├── .gitignore
├── agent.py
├── tools.py
├── pyproject.toml
├── requirements.txt
├── sample_report.json
├── LICENSE
└── README.md
```

Generated audit reports and traces are created when requested and are not part of the source-code structure.

## Prerequisites

Before running the project, ensure you have:

- Python 3.10 or later, subject to dependency compatibility.
- Git installed and available on your system's PATH.
- A Gemini API key for model access.
- Internet access to clone the target GitHub repository and communicate with the model API.

The automated CI workflow currently tests Python 3.10, 3.11, and 3.12.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/shahryarahmad11/Repository-Auditor.git
cd Repository-Auditor
```

### 2. Create a Virtual Environment

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Upgrade pip and install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

Repository Auditor requires a Gemini API key to communicate with the language model.

### 1. Create Your Environment File

Copy the example configuration:

Linux or macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 2. Configure Your API Key

Open `.env` and set your key using the variable expected by the application:

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
```

Replace the placeholder with your actual key. Do not commit `.env` or share your API key publicly.

The default model and any supported model override are determined by the application's configuration and command-line arguments.

## Usage

### Basic Audit

Run the agent against a public GitHub repository:

```bash
python agent.py \
  --repo https://github.com/owner/repository \
  --output report.json
```

Replace `owner/repository` with the GitHub repository you want to inspect.

For example, to audit this project:

```bash
python agent.py \
  --repo https://github.com/shahryarahmad11/Repository-Auditor \
  --output report.json
```

### Specify a Model

If you want to override the configured model, use the supported `--model` argument:

```bash
python agent.py \
  --repo https://github.com/owner/repository \
  --output report.json \
  --model gemini-3.5-flash
```

Use a model identifier that is available to your API key. Model availability and rate limits may vary.

### Save an Investigation Trace

To save the agent's tool-call trace:

```bash
python agent.py \
  --repo https://github.com/owner/repository \
  --output report.json \
  --trace trace.json
```

The trace is useful for understanding which tools were called and diagnosing unexpected results.

### Command-Line Arguments

| Argument | Required | Description |
|---|---|---|
| `--repo` | Yes | Public GitHub repository URL to audit. |
| `--output` | Yes | Destination path for the JSON audit report. |
| `--model` | No | Overrides the configured language model. |
| `--trace` | No | Destination path for the optional investigation trace. |

Run `python agent.py --help` to inspect the options exposed by your current version.

## Audit Report Format

A completed audit produces a JSON document with the repository URL and a `violations` array.

A violation contains the following fields:

| Field | Description |
|---|---|
| `rule_id` | Identifier assigned to the finding. |
| `category` | Category of the reported issue. |
| `severity` | Severity classification: `critical`, `high`, `medium`, or `low`. |
| `file` | Relevant repository file, or `null` when no specific file applies. |
| `line` | Relevant line number, or `null` when no specific line applies. |
| `description` | Explanation of the potential violation. |
| `evidence` | Supporting evidence observed during the audit. |
| `recommendation` | Suggested remediation or next step. |

### Example Report

The following is an illustrative report showing the output structure for an audit with no findings:

```json
{
  "repository": "https://github.com/example/demo-project",
  "violations": []
}
```

A report containing findings uses the same top-level structure:

```json
{
  "repository": "https://github.com/example/demo-project",
  "violations": [
    {
      "rule_id": "TST-001",
      "category": "testing",
      "severity": "medium",
      "file": "pyproject.toml",
      "line": null,
      "description": "Automated test configuration could not be identified.",
      "evidence": "The inspected repository files did not establish a configured automated test suite.",
      "recommendation": "Review the project structure and configure an appropriate automated test suite if one is missing."
    }
  ]
}
```

**Note:** This second example illustrates the schema only. Its finding is not a verified result from an actual repository audit. The category and severity values in real reports depend on the application's validation rules and the evidence returned during the audit.

A finding should be reviewed in context before remediation. The absence of a file or configuration does not necessarily establish that a project has a defect; a repository may use an alternative mechanism or configuration location.

## Running Tests

The project includes automated tests that can be run locally without requiring a live audit of a GitHub repository.

Run the test suite:

```bash
python -m pytest -q
```

Compile the main Python modules:

```bash
python -m py_compile agent.py tools.py
```

Run Ruff:

```bash
python -m ruff check agent.py tools.py tests
```

Check for whitespace errors in Git changes:

```bash
git diff --check
```

The test suite covers important functionality such as repository URL validation, violation normalization, report serialization, secret redaction, file reading, path traversal protection, code searching, and agent tool-call behavior.

## Continuous Integration

The project includes a GitHub Actions workflow at:

```text
.github/workflows/ci.yml
```

The workflow runs on pushes and pull requests and performs:

1. Python environment setup.
2. Dependency installation.
3. Ruff linting.
4. Automated pytest execution.

The configured Python version matrix includes Python 3.10, 3.11, and 3.12.

After pushing changes, inspect the repository's **Actions** tab on GitHub to review the workflow results.

## Security and Safety

Repository auditing involves inspecting untrusted repository contents and handling potentially sensitive information. The implementation includes safeguards intended to reduce these risks.

### Repository Validation

The agent validates repository URLs before cloning and uses Git subprocess arguments rather than constructing shell commands from the supplied URL.

### Temporary Workspace

The target repository is cloned into a temporary workspace for inspection. The agent's inspection workflow is designed not to modify the target repository.

### File Access Restrictions

File inspection applies path containment checks to help prevent path traversal outside the repository. File reading is bounded, and symbolic links are treated cautiously.

### Secret Redaction

Recognized secrets are redacted from supported tool outputs before they are returned to the agent. However, pattern-based redaction cannot guarantee that every credential or sensitive value will be detected.

### No Intentional Execution of Target Code

The auditing workflow inspects repository content and uses supported static-analysis tools. It is not intended to run the target project's application, build scripts, or tests as part of the audit.

### API Key Protection

Keep API credentials in `.env` or another appropriate secret-management mechanism. Do not place API keys in source code, audit reports, trace files, screenshots, or public commits.

### Responsible Reporting

Findings should be supported by observed evidence. Review reported issues before making changes, especially when a recommendation depends on project-specific conventions or configuration that the agent may not have discovered.

## Limitations

- The quality of findings depends on the model, repository contents, available tools, and evidence discovered during inspection.
- The agent may produce false positives or miss genuine issues.
- Pattern-based secret detection is not exhaustive.
- Missing optional files or configurations do not automatically establish a violation.
- API rate limits, temporary service outages, network failures, and model availability can interrupt an audit.
- Static inspection cannot establish every aspect of runtime behavior, deployment security, or infrastructure configuration.
- A successful audit report does not certify that a repository is secure, compliant, or free of defects.

Repository Auditor is intended to support engineering review, not replace human verification or dedicated security testing.

## Troubleshooting

### Gemini API Errors

If the model API returns a rate-limit or service-availability error:

- Confirm that the API key is valid.
- Verify that the selected model is available to your account.
- Check API usage and rate limits.
- Retry later if the provider is experiencing a temporary outage.

### Invalid Repository URL

Provide a supported public GitHub repository URL rather than a URL to a file, branch page, or unrelated Git hosting service.

### Missing Dependencies

Activate the project's virtual environment and reinstall dependencies:

```bash
python -m pip install -r requirements.txt
```

### Test Failures

Run the test suite with more detailed output:

```bash
python -m pytest -v
```

For linting issues, run:

```bash
python -m ruff check agent.py tools.py tests
```

### Missing Report

Check the terminal output for cloning errors, API errors, or other fatal failures. Verify that the output directory exists or that the application has permission to create it.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for the full license text.

---

**Repository:** [shahryarahmad11/Repository-Auditor](https://github.com/shahryarahmad11/Repository-Auditor)
