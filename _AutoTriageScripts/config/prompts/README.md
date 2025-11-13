# LLM Prompts

This directory contains the prompt templates used by the AI analysis system. Prompts are stored as **plain text files** for easy editing and version control.

## File Structure

Each analysis type has **two files**:

### 1. System Context (`*_system.txt`)

Defines the AI's role and response format rules.

- Sets the AI's persona (security analyst, code quality analyst, etc.)
- Defines JSON response format requirements
- Establishes core behavior rules

### 2. Prompt Template (`*_prompt.txt`)

The actual instructions for analyzing each issue.

- Investigation workflow
- Tool usage guidelines
- Output requirements
- Examples and best practices

## Analysis Types

| Type                       | System File                         | Prompt File                         | Purpose                                                    |
| -------------------------- | ----------------------------------- | ----------------------------------- | ---------------------------------------------------------- |
| **Vulnerability Analysis** | `vulnerability_analysis_system.txt` | `vulnerability_analysis_prompt.txt` | Analyze security vulnerabilities (CVEs, security hotspots) |
| **Code Quality Analysis**  | `code_quality_analysis_system.txt`  | `code_quality_analysis_prompt.txt`  | Analyze code smells, bugs, and quality issues              |
| **Dependency Analysis**    | `dependency_analysis_prompt.txt`    | `dependency_analysis_prompt.txt`    | Analyze dependency usage and impact                        |

## Editing Prompts

### ✅ Best Practices

1. **Use your favorite text editor** - These are plain text files!
2. **Be specific** - The more specific your instructions, the better the AI performs
3. **Include examples** - Show good vs bad examples inline
4. **Test changes** - Run the analysis on known issues to validate improvements
5. **Use full file paths** - Always instruct the AI to use complete file paths from the `component` field

### 📝 Template Variables

Prompts support the following placeholders:

- `{vulnerability}` - Full vulnerability information JSON
- `{issue}` - Code quality issue information JSON
- `{dependency}` - Dependency information JSON
- `{tools_documentation}` - Auto-generated list of available tools
- `{file_path}` - File path from the issue
- `{line_number}` - Line number from the issue
- `{issue_type}` - Type of issue (CODE_SMELL, BUG, etc.)
- `{severity}` - Original severity from the tool

### ⚙️ How It Works

1. When the analysis agent starts, it loads all prompt files from this directory
2. During analysis, it selects the appropriate prompt based on the problem type
3. Variables are replaced with actual values
4. The formatted prompt is sent to the LLM

## Example: Adding a New Instruction

To add a reminder about checking SBOM data:

**Edit `vulnerability_analysis_prompt.txt`:**

```txt
When analyzing dependencies:
1. ALWAYS check the SBOM first using search_sbom
2. Verify if the package is actually imported...
```
