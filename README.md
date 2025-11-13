# AutoTriage

AI-powered security and code quality triage system that automatically investigates which issues actually matter in your codebase.

**Copy this into your repository** to get automated AI-powered triage of security vulnerabilities and code quality issues.

> 🔧 **Fully Customizable**: Extend with your own investigation tools, security tool parsers, or LLM providers. The AI automatically discovers and uses any tools you add.

## Table of Contents

- [What It Does](#what-it-does)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Known Issues Management](#known-issues-management)
- [Output](#output)
- [Extending AutoTriage](#extending-autotriage)
- [Troubleshooting](#troubleshooting)

---

## What It Does

AutoTriage analyzes security vulnerabilities and code quality issues **in context** using an AI agent that investigates your codebase:

**Instead of:**

- "PyYAML has CVE-2020-14343 (CRITICAL)" → ❌ Manual investigation required

**You get:**

- "PyYAML vulnerability not applicable - not imported in production code. Only in test dependencies. Evidence: `grep -r 'import yaml' src/` returned 0 matches." → ✅ Auto-triaged

**Supports:**

- SonarQube (code quality, security hotspots)
- OWASP Dependency-Check (CVE vulnerabilities)
- CycloneDX SBOMs (software bill of materials)

**Key Features:**

- **Agentic AI**: LLM autonomously uses tools to investigate issues (reads files, searches code, checks imports)
- **Contextual Analysis**: Determines if vulnerabilities are actually exploitable in your code
- **Human Learning**: Document your decisions once, AI references them in future analyses
- **Fully Extensible**: Add custom investigation tools, security tool parsers, or LLM providers - AI automatically discovers them

---

## How It Works

### The Agentic Loop

For each issue, the AI agent iteratively investigates using available tools:

```
1. Issue: "CVE-2020-14343 in PyYAML 5.3.1 (CRITICAL)"

2. AI searches known issues database
   → Tool: search_known_issues(["PyYAML", "CVE-2020-14343"])
   → Result: Found human review from 2025-11-13

3. AI reads full human review
   → Tool: check_known_issue("CVE-2020-14343")
   → Result: "Not applicable - only test dependency"

4. AI verifies human's claim
   → Tool: check_import_usage("PyYAML")
   → Result: 0 imports found in src/

5. AI concludes
   → Tool: provide_analysis(
       is_applicable=false,
       severity="trivial",
       explanation="Per security team review: PyYAML only in tests..."
     )
```

### Investigation Tools Available to AI

The AI has access to 10 investigation tools (you can add more):

| Tool                  | Purpose                                             |
| --------------------- | --------------------------------------------------- |
| `search_known_issues` | Search human-reviewed issues by keywords            |
| `check_known_issue`   | Get full details of a specific human review         |
| `check_import_usage`  | Check if Python packages are imported (Python only) |
| `search_code`         | Grep-based regex search across codebase             |
| `read_file`           | Read complete file contents                         |
| `read_file_lines`     | Read specific line ranges (for large files)         |
| `list_directory`      | List directory contents                             |
| `find_files`          | Find files matching patterns                        |
| `search_sbom`         | Search SBOM for packages (if SBOM exists)           |
| `provide_analysis`    | Submit final conclusion                             |

**Dynamic filtering**: Tools automatically hidden if requirements not met (e.g., no SBOM → `search_sbom` hidden)

**Want to add your own tools?** See [Extending AutoTriage](#extending-autotriage) - the AI automatically discovers new tools.

---

## Installation

### Step 1: Copy AutoTriage into Your Repository

```bash
# In your repository root
git clone https://github.com/your-org/AutoTriage.git temp-autotriage
cp -r temp-autotriage/_AutoTriageScripts .
cp temp-autotriage/.github/workflows/code-analysis.yml .github/workflows/
rm -rf temp-autotriage
```

Your repository structure:

```
your-repo/
├── _AutoTriageScripts/      # AutoTriage system (you just copied this)
├── .github/workflows/
│   └── code-analysis.yml    # Workflow file (you just copied this)
├── src/                     # Your actual code
├── package.json             # Your project files
└── ...
```

### Step 2: Configure GitHub Secrets

Add these secrets in **Settings → Secrets and variables → Actions**:

| Secret               | Required | Purpose          | Get it from                                                  |
| -------------------- | -------- | ---------------- | ------------------------------------------------------------ |
| `OPENROUTER_API_KEY` | ✅ Yes   | AI model access  | [openrouter.ai](https://openrouter.ai) (free tier available) |
| `SONAR_HOST_URL`     | Optional | SonarQube server | Your SonarQube instance                                      |
| `SONAR_TOKEN`        | Optional | SonarQube auth   | SonarQube user settings                                      |

**Want to add your own secrets?** Edit `.github/workflows/code-analysis.yml` and add them to the `env:` section of the analysis step.

### Step 3: Customize Workflow (Optional)

Edit `.github/workflows/code-analysis.yml` to:

- **Add your security tools**: Integrate Snyk, Trivy, Bandit, etc. by adding steps that generate reports
- **Add more secrets**: Include any API keys or tokens your custom tools need
- **Adjust timing**: Change when analysis runs (on push, PR, schedule)
- **Modify tool flags**: Enable/disable `--sonarqube`, `--dependency-check`, `--sbom`

Example customization:

```yaml
# Add before "Run Analysis Aggregation" step
- name: Run Snyk Scan
  run: snyk test --json > analysis-inputs/snyk/snyk-report.json
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

### Step 4: Run Analysis

**Automatic**: Workflow runs on every push/PR (configure triggers in `code-analysis.yml`)

**Manual**:

1. Go to **Actions** → **Code Analysis**
2. Click **Run workflow**
3. Wait for completion
4. Download artifacts:
   - `analysis_report.json` - Detailed JSON
   - `analysis_summary.md` - Human-readable summary
   - `conversation_logs/` - AI investigation logs

---

## Configuration

### AI Model (`_AutoTriageScripts/config/ai_config.json`)

```json
{
  "ai_providers": {
    "openrouter": {
      "models": {
        "default": "qwen/qwen3-30b-a3b:free",
        "backup": "deepseek/deepseek-chat-v3.1:free"
      }
    }
  },
  "analysis": {
    "max_retries": 3,
    "retry_delay_seconds": 5,
    "timeout_seconds": 300
  }
}
```

**Recommended models:**

- `qwen/qwen3-30b-a3b:free` - Good quality, free
- `deepseek/deepseek-chat-v3.1:free` - Backup, free
- `anthropic/claude-3.5-sonnet` - Best quality, paid

**Backup model**: Automatically used if primary model rate-limited or unavailable.

### Analysis Prompts (`_AutoTriageScripts/config/prompts.json`)

System prompts for different analysis types:

- `vulnerability_analysis` - Security vulnerabilities
- `code_quality_analysis` - Code smells, bugs
- `dependency_analysis` - Dependency usage

Edit these to customize AI behavior and investigation strategies.

### Workflow Configuration (`.github/workflows/code-analysis.yml`)

Key settings you can adjust:

- **Max iterations**: Default 15 tool calls per issue (balance between thoroughness and speed)
- **Tool selection**: `--sonarqube`, `--dependency-check`, `--sbom` flags
- **Triggers**: When workflow runs (push, PR, schedule, manual)
- **Custom steps**: Add your own security scanning tools

---

## Known Issues Management

**Problem**: AI re-analyzes the same false positives every time.

**Solution**: Document your decisions once, AI references them forever.

### Quick Start

```bash
# Install PyYAML (only needed for managing known issues)
pip install pyyaml

# Navigate to AutoTriage scripts
cd _AutoTriageScripts

# Add your first known issue
python manage_known_issues.py add
```

### CLI Tool

```bash
cd _AutoTriageScripts

# Add a new known issue (interactive)
python manage_known_issues.py add

# List all documented issues
python manage_known_issues.py list

# Show full details
python manage_known_issues.py show CVE-2020-14343

# Search by keyword
python manage_known_issues.py search "PyYAML"

# Get statistics
python manage_known_issues.py summary
```

### How AI Uses It

**Automatic workflow**:

1. AI sees issue: `CVE-2020-14343 in PyYAML`
2. AI searches: `search_known_issues(["PyYAML", "CVE-2020-14343"])`
3. AI finds: Match score 10.0 - human reviewed on 2025-11-13
4. AI reads full details: `check_known_issue("CVE-2020-14343")`
5. AI uses human context in analysis: "Per security team review..."

**Benefits**:

- Never analyze the same false positive twice
- Capture institutional knowledge (things only humans know)
- New team members see past decisions
- Audit trail for compliance

### File Format

Known issues stored as YAML in `_AutoTriageScripts/known_issues/`:

```yaml
# CVE-2020-14343.yaml
problem_id: "CVE-2020-14343"
title: "PyYAML arbitrary code execution vulnerability"
status: not_applicable # or: accepted_risk, mitigated, wont_fix

human_reasoning: |
  PyYAML only used in testing framework, not production.
  Verified with grep and Docker container inspection.

context:
  - "Confirmed with DevOps team"
  - "Not in production requirements.txt"

evidence:
  - "grep -r 'import yaml' src/ returned 0 matches"
  - "Production SBOM scan shows PyYAML absent"

reviewed_by: "Security Team"
review_date: "2025-11-13"
expires: "2026-11-13"

re_evaluate_on:
  - "If PyYAML added to production dependencies"
```

See `_AutoTriageScripts/known_issues/README.md` for full documentation.

---

## Output

### Analysis Summary (`analysis_summary.md`)

Human-readable markdown report categorizing issues:

```markdown
# Security and Quality Analysis Summary

**Total Issues Analyzed:** 3
**Security Issues Requiring Attention:** 0 (CRITICAL/HIGH/MEDIUM)
**Code Quality Issues:** 0
**False Positives/Not Applicable:** 3

## 📊 Analysis Details

- Problems by Severity:
  - CRITICAL: 0
  - HIGH: 0
  - MEDIUM: 0

## ✅ False Positives / Not Applicable

### Problem: PyYAML arbitrary code execution vulnerability

**Description:** CVE-2020-14343 in PyYAML 5.3.1

- **ID:** CVE-2020-14343
- **Investigation:** Found human review. Verified PyYAML not imported in src/
- **Analysis:** Per security team (2025-11-13): Only test dependency
- **Verify Yourself:**
  - Run: `grep -r 'import yaml' src/`
  - Check production containers
- **Limitations:** Did not verify dynamic imports
```

**Categories:**

- **Security Issues Requiring Attention** - CRITICAL/HIGH/MEDIUM vulnerabilities that need action
- **Low Priority Security Issues** - LOW/TRIVIAL vulnerabilities for maintenance
- **Code Quality Issues** - Code smells, bugs (separate from security)
- **False Positives / Not Applicable** - Issues that don't apply to your codebase
- **Analysis Failures - Manual Review Required** - Issues AI couldn't analyze (rare)

### Detailed Report (`analysis_report.json`)

Full JSON with all findings, evidence, and AI reasoning:

```json
{
  "summary": {
    "total_problems": 3,
    "applicable": 0,
    "dismissed": 3,
    "by_severity": { "TRIVIAL": 3 }
  },
  "results": [
    {
      "problem_id": "CVE-2020-14343",
      "problem_title": "PyYAML arbitrary code execution",
      "problem_description": "CVE-2020-14343...",
      "problem_type": "vulnerability",
      "is_applicable": false,
      "severity": "TRIVIAL",
      "explanation": "Per security team review...",
      "investigation_summary": "Found human review. Verified claims.",
      "verification_steps": ["grep -r 'import yaml' src/"],
      "limitations": ["Did not verify dynamic imports"],
      "recommended_actions": ["No action needed"],
      "evidence": {
        "human_review_found": true,
        "imports_found": false
      },
      "analysis_steps": [
        { "tool": "search_known_issues", "iteration": 1 },
        { "tool": "check_known_issue", "iteration": 2 },
        { "tool": "check_import_usage", "iteration": 3 }
      ]
    }
  ]
}
```

### Conversation Logs (`conversation_logs/`)

Full AI investigation logs for debugging:

- `{problem_id}_conversation.json` - Complete tool call history per issue
- Includes AI reasoning, tool parameters, tool results
- Useful for understanding AI decisions or debugging unexpected results

---

## Extending AutoTriage

AutoTriage is designed to be extended. Add your own tools, parsers, or LLM providers - the system automatically discovers them.

### Add Investigation Tool

Create a new tool file in `_AutoTriageScripts/tools/`:

```python
# _AutoTriageScripts/tools/git_history.py
from .base_tool import BaseTool

class GitHistoryTool(BaseTool):
    name = "check_git_history"
    description = "Check git commit history for a file to see recent changes"

    parameters = {
        "file_path": {
            "type": "string",
            "description": "File to check history for",
            "required": True
        },
        "max_commits": {
            "type": "number",
            "description": "Number of commits to retrieve",
            "required": False
        }
    }

    requirements = []  # Or specify ["git"] if git must be installed

    example = {
        "call": {
            "tool": "check_git_history",
            "parameters": {"file_path": "app.py", "max_commits": 5}
        },
        "result": {
            "success": True,
            "commits": 5,
            "last_author": "john@example.com",
            "last_modified": "2025-11-10"
        }
    }

    def execute(self, params):
        file_path = params["file_path"]
        max_commits = params.get("max_commits", 10)

        # Run git log
        import subprocess
        result = subprocess.run(
            ["git", "log", f"-{max_commits}", "--format=%H|%an|%ad", file_path],
            capture_output=True,
            text=True,
            cwd=self.workspace_root
        )

        # Parse and return results
        commits = result.stdout.strip().split('\n')
        return {
            "success": True,
            "commits": len(commits),
            "history": commits
        }
```

**That's it!** The AI can now use `check_git_history` in its investigations. No other changes needed.

### Add Security Tool Parser

Create a new parser in `_AutoTriageScripts/parsers/`:

```python
# _AutoTriageScripts/parsers/snyk_parser.py
from .base_parser import BaseParser, Problem
from pathlib import Path
from typing import List
import json

class SnykParser(BaseParser):
    """Parse Snyk vulnerability reports."""

    def parse(self, file_path: Path) -> List[Problem]:
        with open(file_path) as f:
            data = json.load(f)

        problems = []
        for vuln in data.get("vulnerabilities", []):
            problems.append(Problem(
                id=vuln["id"],
                source="snyk",
                title=vuln["title"],
                description=vuln["description"],
                severity=vuln["severity"].upper(),
                component=vuln["packageName"],
                type="vulnerability",
                line=None,
                raw_data=vuln
            ))

        return problems
```

Then use it in `analyze_dependencies.py`:

```python
from parsers import SnykParser

# Add to collect_problems()
if args.snyk:
    snyk_file = input_dir / "snyk" / "snyk-report.json"
    if snyk_file.exists():
        parser = SnykParser()
        snyk_problems = parser.parse(snyk_file)
        all_problems.extend(snyk_problems)
```

### Add LLM Provider

Create a new provider in `_AutoTriageScripts/llm_providers/`:

```python
# _AutoTriageScripts/llm_providers/anthropic_provider.py
from .base_provider import BaseLLMProvider
from anthropic import Anthropic

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = config.get("model", "claude-3-5-sonnet-20241022")

    def query(self, messages, model=None, **kwargs):
        response = self.client.messages.create(
            model=model or self.model,
            messages=messages,
            max_tokens=4096
        )
        return response.content[0].text

    def validate_config(self):
        return os.getenv("ANTHROPIC_API_KEY") is not None
```

Register in `llm_providers/__init__.py`:

```python
from .anthropic_provider import AnthropicProvider

PROVIDER_REGISTRY = {
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider
}
```

Update `ai_config.json`:

```json
{
  "ai_providers": {
    "anthropic": {
      "model": "claude-3-5-sonnet-20241022"
    }
  }
}
```

---

## Troubleshooting

### "API key must be set"

**Cause**: `OPENROUTER_API_KEY` not set.

**Fix**: Add secret in GitHub Settings → Secrets → Actions

### "File not found" errors

**Cause**: Security tool outputs not in expected locations.

**Fix**: Verify your workflow places tool outputs in `analysis-inputs/`:

- SonarQube: `analysis-inputs/sonarqube/sonar-issues.json`
- Dependency-Check: `analysis-inputs/dependency-check/dependency-check-report.json`
- SBOM: `analysis-inputs/sbom/sbom.json`

### Empty analysis results

**Cause**: No issues detected or all filtered out.

**Fix**:

1. Verify scanning tools ran successfully
2. Check workflow logs for tool execution
3. Look at `problems.json` in output to see what was collected

### Rate limiting errors

**Behavior**: System automatically switches to backup model.

**Fix**:

1. Use paid OpenRouter model for higher limits
2. Add your own API keys to OpenRouter
3. Increase `retry_delay_seconds` in `ai_config.json`

### Analysis taking too long

**Cause**: AI making many tool calls per issue.

**Current default**: 15 iterations per issue (about 1-2 minutes per issue)

**Options**:

1. Document common false positives in `known_issues/` - AI will check these first and conclude faster
2. Reduce iteration limit in workflow (trade-off: less thorough)

---

## Project Structure

```
your-repo/                              # Your repository
├── _AutoTriageScripts/                 # AutoTriage system (copied in)
│   ├── analyze_dependencies.py         # Entry point
│   ├── analysis_agent.py               # Agentic loop
│   ├── llm_client.py                   # LLM provider factory
│   ├── tool_executor.py                # Tool dispatcher
│   │
│   ├── llm_providers/                  # LLM integrations
│   │   ├── base_provider.py
│   │   └── openrouter_provider.py
│   │
│   ├── parsers/                        # Security tool parsers
│   │   ├── base_parser.py
│   │   ├── sonarqube_parser.py
│   │   ├── dependency_check_parser.py
│   │   └── cyclonedx_parser.py
│   │
│   ├── tools/                          # AI investigation tools
│   │   ├── search_known_issues.py      # 🔍 Searches human reviews
│   │   ├── check_known_issues.py       # Gets specific review
│   │   ├── check_import_usage.py       # Python package imports
│   │   ├── search_code.py
│   │   ├── read_file.py
│   │   ├── read_file_lines.py
│   │   ├── list_directory.py
│   │   ├── find_files.py
│   │   ├── search_sbom.py
│   │   └── provide_analysis.py
│   │
│   ├── known_issues/                   # Human-reviewed issues
│   │   ├── README.md
│   │   ├── .template.yaml
│   │   └── CVE-2020-14343.yaml         # Example
│   │
│   ├── config/
│   │   ├── ai_config.json              # Model settings
│   │   └── prompts.json                # System prompts
│   │
│   ├── manage_known_issues.py          # CLI for known issues
│   └── requirements.txt
│
├── .github/workflows/
│   └── code-analysis.yml               # Workflow (copied in)
│
├── src/                                # Your actual code
├── package.json                        # Your project
└── ...
```

---

## How It Works Technically

**Agentic AI System**: Unlike traditional static analysis, AutoTriage uses an LLM that can autonomously decide what to investigate and how. It iteratively calls tools based on what it learns, making up to 15 tool calls per issue.

**Tool Calling**: LLM receives tool documentation, decides which tool to call with what parameters, receives results, and repeats until reaching a conclusion.

**Known Issues Database**: Human decisions stored as YAML files. AI searches these first using keyword matching with relevance scoring, then reads full details if relevant match found.

**Dynamic Tool Filtering**: Tools can specify requirements (files, executables). System checks requirements before each analysis and only shows usable tools to AI.

**Modular Architecture**: New tools, parsers, and providers automatically discovered via Python's import system. No manual registration required.
