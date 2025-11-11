# AutoTriage

An AI-powered automated security and code quality triage system that intelligently analyzes issues from various scanning tools (SonarQube, OWASP Dependency-Check, CycloneDX SBOMs) to determine which issues are truly applicable to your project.

## Overview

AutoTriage uses an agentic AI system to analyze security vulnerabilities and code quality issues in context. Instead of simply flagging every potential issue, it uses an LLM with tool-calling capabilities to intelligently investigate your codebase and determine:

- **Is this vulnerability actually exploitable?** Does the code use the vulnerable functions?
- **Is this dependency actually used?** Is it imported anywhere in the codebase?
- **Is this code smell a real problem?** Does it warrant attention in this specific context?

## How It Works

### Architecture

1. **Problem Collection**: Parses outputs from security tools (SonarQube, Dependency-Check, SBOM)
2. **Agentic Analysis**: For each issue, an AI agent with tool access investigates:
   - Reads source code files
   - Searches for patterns (imports, function usage)
   - Checks SBOM for package information
   - Analyzes file structures
3. **Contextualized Results**: Provides actionable reports with confidence scores and evidence

### The Agentic Loop

The AI agent uses an iterative tool-calling approach:

```
1. Receive problem (e.g., "PyYAML 5.3.1 has CVE-2020-1234")
2. LLM decides what to investigate first
   → Calls: search_sbom("PyYAML")
3. Receives result: { found: true, version: "5.3.1" }
4. LLM decides next step
   → Calls: check_import_usage("yaml")
5. Receives result: { is_imported: false }
6. LLM concludes
   → Calls: provide_analysis(is_applicable=false, confidence=0.9, ...)
```

This continues for up to 5 iterations per issue.

### Supported Analysis Tools

AutoTriage can parse and analyze results from:

- **SonarQube**: Code quality issues, bugs, security hotspots
- **OWASP Dependency-Check**: CVE vulnerabilities in dependencies
- **CycloneDX SBOM**: Software Bill of Materials with optional vulnerability data

### AI Investigation Tools

The AI agent has access to these tools during analysis:

- **read_file**: Read complete file contents
- **read_file_lines**: Read specific line ranges (for large files)
- **search_code**: Grep-based pattern search with regex support
- **find_files**: Find files matching patterns
- **list_directory**: List directory contents
- **search_sbom**: Search Software Bill of Materials for packages (⚠️ only available if SBOM exists)
- **check_import_usage**: Check if Python packages are imported
- **provide_analysis**: Submit final analysis conclusion

**Dynamic Tool Filtering**: Tools are automatically filtered based on availability. For example, if no SBOM file is present, the `search_sbom` tool is hidden from the AI to prevent confusion. This ensures the AI only sees tools it can actually use.

## Setup

### Prerequisites

- Python 3.8+
- GitHub Actions environment (or Linux for local testing)
- OpenRouter API key (for AI model access)
- (Optional) Syft or Trivy for SBOM generation - see [SBOM Guide](_AutoTriageScripts/SBOM_GUIDE.md)

### GitHub Secrets

Configure these secrets in your repository:

- `OPENROUTER_API_KEY`: API key from [OpenRouter](https://openrouter.ai)
- `SONAR_HOST_URL`: SonarQube server URL (if using SonarQube)
- `SONAR_TOKEN`: SonarQube authentication token

### Local Setup

```bash
# Install dependencies
pip install -r _AutoTriageScripts/requirements.txt

# Set environment variable
export OPENROUTER_API_KEY="your-api-key-here"
```

## Usage

### Via GitHub Workflow

The workflow runs automatically or can be triggered manually:

1. Go to **Actions** → **Code Analysis**
2. Click **Run workflow**
3. Configure the workflow:
   - **Subfolder**: Select the test subfolder (e.g., `container_security`, `old_deps`)
   - **Max Iterations** (optional): Maximum tool calls AI can make per issue (default: 5)

Results are uploaded as workflow artifacts:

- `analysis_report.json`: Detailed JSON report with all findings
- `analysis_summary.md`: Human-readable summary with actionable recommendations
- `problems.json`: Debug file with all detected issues (before analysis)
- `conversation_logs/`: Detailed AI conversation logs for each issue (useful for debugging)

### Manual Execution

```bash
# Analyze a project
python _AutoTriageScripts/analyze_dependencies.py <subfolder> --sonarqube --dependency-check

# Example with container_security test project
python _AutoTriageScripts/analyze_dependencies.py container_security --dependency-check

# Include SBOM vulnerability analysis
python _AutoTriageScripts/analyze_dependencies.py container_security --dependency-check --sbom

# Customize max iterations (allow more thorough investigation)
python _AutoTriageScripts/analyze_dependencies.py container_security --dependency-check --max-iterations 8

# Quick analysis (fewer iterations)
python _AutoTriageScripts/analyze_dependencies.py old_deps --sonarqube --max-iterations 3
```

**Available Options:**

- `--sonarqube`: Process SonarQube results
- `--dependency-check`: Process OWASP Dependency-Check results
- `--sbom`: Process CycloneDX SBOM for vulnerabilities
- `--input-dir`: Custom input directory (default: `analysis-inputs`)
- `--output-dir`: Custom output directory (default: `analysis-outputs`)
- `--max-iterations`: Max tool calls per issue (default: `5`)

## Project Structure

```
AutoTriage/
├── _AutoTriageScripts/           # Main analysis system
│   ├── analyze_dependencies.py   # Entry point script
│   ├── analysis_agent.py         # Core agent logic and agentic loop
│   ├── tool_executor.py          # Lightweight tool execution dispatcher
│   ├── llm_client.py             # LLM provider factory
│   ├── prompt_formatter.py       # Formats tool docs for LLM
│   ├── tool_availability.py      # Dynamic tool filtering
│   │
│   ├── llm_providers/            # 🔌 Pluggable LLM providers
│   │   ├── __init__.py
│   │   ├── base_provider.py     # Abstract base class
│   │   └── openrouter_provider.py  # OpenRouter implementation
│   │
│   ├── parsers/                  # 🔌 Pluggable tool parsers
│   │   ├── __init__.py
│   │   ├── base_parser.py       # Abstract base class + Problem dataclass
│   │   ├── sonarqube_parser.py  # SonarQube parser
│   │   ├── dependency_check_parser.py  # OWASP Dependency-Check parser
│   │   └── cyclonedx_parser.py  # CycloneDX SBOM parser
│   │
│   ├── tools/                    # 🔌 Modular investigation tools
│   │   ├── __init__.py           # Auto-discovery and tool registry
│   │   ├── base_tool.py          # Abstract base class
│   │   ├── read_file.py          # Read complete file contents
│   │   ├── read_file_lines.py    # Read specific line ranges
│   │   ├── search_code.py        # Grep-based pattern search
│   │   ├── list_directory.py     # List directory contents
│   │   ├── find_files.py         # Find files by pattern
│   │   ├── search_sbom.py        # Search SBOM for packages
│   │   ├── check_import_usage.py # Check Python import usage
│   │   └── provide_analysis.py   # Final analysis submission
│   │
│   ├── config/
│   │   ├── ai_config.json        # AI model configuration
│   │   └── prompts.json          # LLM prompt templates
│   │
│   └── tests/                    # Test suite
│       ├── test_parser_compatibility.py  # Verifies parsers match old behavior
│       ├── test_cyclonedx_parser.py     # CycloneDX-specific tests
│       ├── test_modular_tools.py        # Tests for modular tool system
│       └── test_tool_filtering.py       # Tests for dynamic tool availability
│
├── _example_output/              # Example outputs from tools
│   ├── CycloneDX/               # SBOM examples
│   ├── Dependency-Check/        # Vulnerability scan examples
│   └── SonarQube/               # Code quality scan examples
│
├── container_security/           # Test project #1: Vulnerable containers
│   ├── app/
│   │   └── app.py
│   ├── requirements.txt
│   └── vulnerable/
│       └── Dockerfile
│
├── old_deps/                     # Test project #2: Outdated dependencies
│   ├── app.py
│   └── requirements.txt
│
└── .github/
    └── workflows/
        └── code-analysis.yml     # GitHub Actions workflow
```

### Parser Path Verification ✅

The parsers expect files at these locations (verified to match GitHub workflow):

| Tool             | Workflow Output                                                 | Parser Expects                                            | Status   |
| ---------------- | --------------------------------------------------------------- | --------------------------------------------------------- | -------- |
| SonarQube        | `analysis-inputs/sonarqube/sonar-issues.json`                   | `input_dir/sonarqube/sonar-issues.json`                   | ✅ Match |
| Dependency-Check | `analysis-inputs/dependency-check/dependency-check-report.json` | `input_dir/dependency-check/dependency-check-report.json` | ✅ Match |
| CycloneDX SBOM   | `analysis-inputs/sbom/sbom.json`                                | `input_dir/sbom/sbom.json`                                | ✅ Match |

The workflow downloads artifacts to `analysis-inputs/` directory, and parsers read from the same structure by default.

**SBOM Format**: Currently enforced to be **CycloneDX** format. The system gracefully handles missing SBOMs by:

- Filtering out the `search_sbom` tool from available tools
- Continuing analysis with other investigation tools
- This prevents the AI from attempting to use unavailable tools

## Modular Architecture 🔌

AutoTriage is built with extensibility in mind. The system uses a pluggable architecture that allows you to:

### Custom LLM Providers

Easily swap or add LLM providers without touching core code.

**Included**: OpenRouter (supports Claude, GPT-4, Gemini, etc.)

**Add Your Own**: Extend `BaseLLMProvider` to add support for:

- Direct OpenAI API
- Anthropic Claude API
- Azure OpenAI
- Google Vertex AI
- Local models (Ollama, LM Studio, etc.)
- Any OpenAI-compatible endpoint

Check `_AutoTriageScripts/llm_providers/` for base class and examples.

### Custom Security Tool Parsers

Add support for new security scanning tools by creating parsers.

**Included**:

- SonarQube (code quality & security)
- OWASP Dependency-Check (CVE vulnerabilities)
- CycloneDX (SBOM with optional vulnerabilities)

**Add Your Own**: Extend `BaseParser` to add support for:

- Snyk
- Trivy
- Bandit
- ESLint with security plugins
- Custom internal tools
- SARIF format tools

Creating a new parser is easy - just extend `BaseParser` and implement 3 methods!

### Custom Investigation Tools

The AI agent uses investigation tools to analyze your codebase. All tools are now **modular** - one file per tool, with automatic discovery.

**Included Tools** (8 total):

- `read_file` - Read complete file contents
- `read_file_lines` - Read specific line ranges (for large files)
- `search_code` - Grep-based pattern search with regex
- `list_directory` - List directory contents
- `find_files` - Find files matching glob patterns
- `search_sbom` - Search SBOM for package info (dynamic availability)
- `check_import_usage` - Check if Python packages are imported
- `provide_analysis` - Submit final analysis conclusion

**Add Your Own**: Extend `BaseTool` to add custom investigation capabilities:

- Git history analysis
- Database schema checks
- API endpoint discovery
- Dependency tree traversal
- Custom static analysis
- Integration with internal tools

Creating a new tool is simple - define metadata and implement one `execute` method!

### Example: Adding a New Parser

```python
# _AutoTriageScripts/parsers/snyk_parser.py
from .base_parser import BaseParser, Problem

class SnykParser(BaseParser):
    def parse(self, file_path: Path) -> List[Problem]:
        # Parse Snyk JSON output
        # Return list of Problem objects
        pass
```

### Example: Adding a New Investigation Tool

```python
# _AutoTriageScripts/tools/git_blame.py
from .base_tool import BaseTool

class GitBlameTool(BaseTool):
    name = "git_blame"
    description = "Get git blame for a file to see who last modified it"
    parameters = {
        "file_path": {"type": "string", "required": True}
    }
    requirements = []  # Or specify git executable requirement

    def execute(self, params, workspace_root, input_dir):
        # Run git blame and return results
        pass
```

No changes needed to core analysis logic! The tool is automatically discovered and made available to the AI.

## Configuration

### AI Model Settings (`_AutoTriageScripts/config/ai_config.json`)

```json
{
  "api_base_url": "https://openrouter.ai/api/v1",
  "model": "anthropic/claude-3.5-sonnet",
  "analysis": {
    "max_retries": 3,
    "timeout_seconds": 300
  }
}
```

### Max Iterations

Controls how many tools the AI can call before forcing a conclusion:

- **Default: 5** - Good balance for most cases
- **Lower (2-3)**: Faster, cheaper, but less thorough
  - Use for quick scans or low-priority issues
  - May miss complex dependencies
- **Higher (7-10)**: More thorough investigation
  - Use for critical vulnerabilities
  - Better at tracing complex import chains
  - Higher API costs

Set via `--max-iterations` flag or workflow input.

### Prompt Templates (`_AutoTriageScripts/config/prompts.json`)

Contains system prompts and templates for different analysis types:

- `vulnerability_analysis`: Security vulnerability evaluation
- `code_quality_analysis`: Code smell and bug analysis
- `dependency_analysis`: Dependency usage and impact

## Analysis Process

### Input

The system accepts problems from three sources:

1. **SonarQube**: Code quality issues, bugs, security hotspots

   - Parsed from JSON export
   - Includes file paths, line numbers, rule types

2. **OWASP Dependency-Check**: CVE vulnerabilities in dependencies

   - Parsed from JSON report
   - Includes CVE IDs, severity, affected packages

3. **CycloneDX SBOM**: Software Bill of Materials
   - Used as supplementary data for dependency analysis
   - Provides version and licensing information

### Output

**`analysis_report.json`** - Detailed JSON report:

```json
{
  "summary": {
    "total_problems": 10,
    "applicable_problems": 3,
    "by_severity": {
      "CRITICAL": 1,
      "HIGH": 2
    }
  },
  "results": [
    {
      "problem_id": "CVE-2020-1234",
      "is_applicable": false,
      "confidence": 0.9,
      "explanation": "PyYAML is in requirements.txt but never imported...",
      "evidence": {
        "in_requirements": true,
        "import_found": false,
        "files_searched": ["*.py"]
      },
      "recommended_actions": ["Remove unused PyYAML dependency", "Run pip freeze to clean requirements.txt"],
      "analysis_steps": [
        { "step": 1, "action": "search_sbom", "tool": "search_sbom" },
        { "step": 2, "action": "check_import_usage", "tool": "check_import_usage" }
      ]
    }
  ]
}
```

**`analysis_summary.md`** - Human-readable markdown:

```markdown
# Security and Quality Analysis Summary

Total problems analyzed: 10
Applicable problems: 3

## Problems by Severity

- CRITICAL: 1
- HIGH: 2
```

## Future Enhancements

### Planned Features

1. **User Feedback System**

   - Allow developers to provide feedback on false positives
   - Store feedback in a knowledge base
   - Agent learns from historical context to reduce false positives

2. **Advanced Timeout Handling**

   - Soft timeout (5 messages): Nudge LLM to change strategy
   - Hard timeout (8 messages): Force best-effort conclusion
   - Currently: Simple 5-iteration limit

3. **Multi-Language Support**

   - Currently Python-focused
   - Expand to JavaScript, Java, Go, etc.

4. **Custom Rule Definitions**
   - Allow teams to define project-specific rules
   - Override default analysis behavior

## Testing

### Test Projects

- **`container_security/`**: Tests container security issues
  - Vulnerable Dockerfile configurations
  - Python security vulnerabilities
- **`old_deps/`**: Tests dependency analysis
  - Outdated packages
  - Unused dependencies

### Running Tests

```bash
cd _AutoTriageScripts/tests

# Run all tests
python test_basic.py

# Test parser compatibility (ensures new parsers produce same results as old code)
python test_parser_compatibility.py

# Test CycloneDX parser
python test_cyclonedx_parser.py

# Test specific components
python test_tools.py           # Test individual tools
python test_path_resolution.py  # Test file path handling
```

### Parser Compatibility Guarantee

The modular parser system is **guaranteed to produce identical results** to the original inline parsing functions. This is verified by the test suite:

- ✅ **SonarQube Parser**: All fields match exactly (id, severity, component, type, line)
- ✅ **Dependency-Check Parser**: All vulnerabilities parsed identically (CVE IDs, descriptions, CWE formatting)
- ✅ **CycloneDX Parser**: New parser for SBOM vulnerability extraction

Run `python _AutoTriageScripts/tests/test_parser_compatibility.py` to verify anytime.

### Tool Availability Filtering

The system dynamically filters tools based on their requirements:

**How it works:**

1. Tools can specify requirements (e.g., "SBOM file must exist")
2. Before each analysis, the system checks which tools are available
3. Only available tools are shown to the AI
4. This prevents the AI from trying to use tools that can't function

**Example:** If no SBOM is present, the `search_sbom` tool is automatically hidden from the AI's available tools.

**Test it:**

```bash
python _AutoTriageScripts/tests/test_tool_filtering.py
```

**Add requirements to new tools:**

```json
{
  "name": "my_tool",
  "description": "...",
  "requirements": [
    {
      "type": "file_exists",
      "path": "{input_dir}/myfile.json",
      "description": "My data file must be present"
    }
  ]
}
```

Supported requirement types: `file_exists`, `executable`, `optional`

## Troubleshooting

### "API key must be set" Error

**Solution**: Ensure `OPENROUTER_API_KEY` is set as environment variable or GitHub secret

### "File not found" Errors

**Solution**: Check that:

- Workspace root is correctly set (repository root, not subfolder)
- File paths in problems don't have project prefixes like "ProjectName:"
- Tools have been run on the correct subfolder

### "Max iterations reached"

**Cause**: LLM couldn't reach conclusion within 5 tool calls
**Solution**: This triggers automatic fallback with conservative defaults (not applicable, low confidence)

### Empty Analysis Summary

**Cause**: No problems detected, or all problems filtered out
**Solution**: Check that scanning tools ran successfully and `problems.json` contains issues

## Contributing

Contributions welcome! Areas of interest:

- Additional tool implementations
- Support for more languages and frameworks
- Improved prompt engineering
- Performance optimizations

## License

[Add your license here]

## Credits

Built with:

- [OpenRouter](https://openrouter.ai) for AI model access
- [OpenAI Python SDK](https://github.com/openai/openai-python) for API client
- [SonarQube](https://www.sonarqube.org/) for code quality analysis
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/) for vulnerability scanning
- [CycloneDX](https://cyclonedx.org/) for SBOM generation
