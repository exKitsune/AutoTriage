# Known Issues Database

This directory contains human reviews of security and quality issues with documented context and reasoning.

## 🎯 Purpose

When security scanners or AI analysis identifies issues, they often lack organizational context:

- Is this a false positive we've seen before?
- Do we have mitigations in place?
- Is this an accepted risk?
- Why did we decide not to fix this?

This database captures that institutional knowledge so we don't re-analyze the same issues repeatedly.

---

## 📋 Usage

### Browse Existing Issues

```bash
# Show summary statistics
python manage_known_issues.py summary

# List all issues
python manage_known_issues.py list

# List only false positives
python manage_known_issues.py list --status not_applicable

# Show detailed view with reasoning previews
python manage_known_issues.py list --details

# Show full details of a specific issue
python manage_known_issues.py show CVE-2020-14343

# Search for issues
python manage_known_issues.py search "PyYAML"
python manage_known_issues.py search "Docker"
```

### Add New Issue

```bash
# Interactive mode (recommended)
python manage_known_issues.py add

# Or manually copy template
cp .template.yaml CVE-2020-14343.yaml
# Edit with your preferred editor
```

---

## 📁 File Format

Each issue is a single YAML file named with the problem ID.

### File Naming

- **CVEs**: `CVE-2020-14343.yaml`
- **SonarQube**: Use the issue key, replace colons: `docker-S6596.yaml`
- **Custom IDs**: Any format, use dashes for special chars

### Required Fields

```yaml
problem_id: "CVE-2020-14343"
title: "Short description"
status: not_applicable # See status options below
human_reasoning: |
  Your detailed reasoning here.
  Why did you make this decision?
  What did you investigate?
reviewed_by: "Your Name / Team Name"
review_date: "2025-11-13"
```

### Status Options

- **`not_applicable`** - False positive, issue doesn't apply to this codebase
- **`accepted_risk`** - Real issue but we consciously accept the risk
- **`mitigated`** - Real issue but we have mitigations/compensating controls
- **`wont_fix`** - Real issue but we won't fix it (document why)

### Optional Fields

```yaml
context:
  - "Additional context the AI doesn't have"
  - "Deployment-specific information"
  - "Organizational decisions"

evidence:
  - "Commands you ran to verify"
  - "Files you checked"
  - "Tests you performed"

expires: "2026-11-13"  # When to re-evaluate this decision
re_evaluate_on: "Major version upgrade" or "New usage detected"
```

---

## 🔍 How AI Uses This

When analyzing an issue, the AI will:

1. **First call** `check_known_issues` tool with the problem ID
2. If found, **read your reasoning and context**
3. **Build upon your decision** in its analysis
4. If it disagrees, **explain why** with evidence

This saves time and ensures consistency across analyses.

---

## 📝 Examples

### Example 1: False Positive (Unused Dependency)

```yaml
problem_id: CVE-2020-14343
title: "PyYAML arbitrary code execution vulnerability"
status: not_applicable

human_reasoning: |
  PyYAML 5.3.1 is only a transitive dependency of our testing framework.
  It's never used in production code. Verified:
  1. Not in production requirements.txt
  2. Not in production Docker images  
  3. No imports in src/ directory

  The vulnerable full_load() is never called. We only use safe_load() in tests.

context:
  - "Confirmed with DevOps team on 2025-11-13"
  - "Production containers built with --no-dev flag"
  - "CI/CD pipeline excludes dev dependencies"

evidence:
  - "grep -r 'full_load' found 0 matches in src/"
  - "grep -r 'import yaml' found matches only in tests/"
  - "Checked poetry.lock - PyYAML marked as dev-only"

reviewed_by: "Security Team (Jane Doe)"
review_date: "2025-11-13"
expires: "2026-11-13"
re_evaluate_on: "PyYAML added to production dependencies"
```

### Example 2: Accepted Risk

```yaml
problem_id: docker-S6596
title: "Docker image should use specific version tag"
status: accepted_risk

human_reasoning: |
  We use ubuntu:latest intentionally in our development Dockerfile.

  This is ONLY used for local development environments, never in production.
  Production images use pinned versions in production.Dockerfile.

  Using :latest for dev gives developers the newest tools without
  manually updating tags frequently. Trade-off accepted for dev productivity.

context:
  - "Discussed in architecture review 2025-11-10"
  - "Production Dockerfile uses ubuntu:22.04 (pinned)"
  - "Dev environments are ephemeral and rebuilt frequently"

evidence:
  - "Checked production.Dockerfile - uses ubuntu:22.04"
  - "CI/CD only builds from production.Dockerfile"
  - "Local dev clearly labeled in docker-compose.yml"

reviewed_by: "Architecture Team"
review_date: "2025-11-13"
re_evaluate_on: "Change to development environment strategy"
```

### Example 3: Mitigated

```yaml
problem_id: CVE-2021-44228
title: "Log4Shell - Log4j RCE vulnerability"
status: mitigated

human_reasoning: |
  We use Log4j 2.14.1 which is vulnerable to CVE-2021-44228.
  However, we have multiple layers of mitigation:

  1. JVM flag: -Dlog4j2.formatMsgNoLookups=true (blocks exploitation)
  2. Network segmentation: App servers cannot make outbound connections
  3. WAF rules: Block JNDI injection patterns
  4. Upgrade planned for Q1 2026 but mitigations eliminate risk now

context:
  - "Mitigations verified by penetration test 2025-11-01"
  - "No vulnerable code paths found in security audit"
  - "Upgrade blocked by dependency on legacy library"

evidence:
  - "JVM flags verified in kubernetes deployment configs"
  - "Network policy blocks outbound LDAP/DNS"
  - "WAF blocks tested with known Log4Shell payloads"
  - "Pentest report: Log4Shell not exploitable"

reviewed_by: "Security Team + Infrastructure Team"
review_date: "2025-11-13"
expires: "2026-03-31"
re_evaluate_on: "Log4j upgraded or mitigations removed"
```

---

## 🔄 Maintenance

### Regular Reviews

- Review expired issues monthly
- Re-evaluate decisions when context changes
- Update reasoning if new information emerges
- Remove if issue is fixed

### Git Workflow

```bash
# Add new review
git add known_issues/CVE-2020-14343.yaml
git commit -m "docs: Mark CVE-2020-14343 as not applicable"
git push

# Update existing review
git commit -am "docs: Update PyYAML review with new context"
git push
```

### Collaboration

- Reviews are code - treat them like code
- Get peer review for "accepted_risk" decisions
- Document all "wont_fix" decisions thoroughly
- Update when teammates discover new info

---

## ⚙️ Integration with AI Analysis

The `check_known_issues` tool will automatically query this database during analysis.

**AI Behavior:**

- ✅ Respects your decisions
- ✅ Includes your reasoning in its analysis
- ✅ Can disagree if it finds new evidence
- ✅ Saves analysis time and API costs

**Output Example:**

```
Investigation: Found existing human review dated 2025-11-13. Security team
determined this is a false positive because PyYAML is only used in tests.
Verified their assessment by confirming PyYAML is marked dev-only in poetry.lock.
```

---

## 📊 Best Practices

1. **Be Specific**: Document exact commands you ran, files you checked
2. **Be Honest**: If accepting risk, document why and the trade-offs
3. **Set Expiration**: Most decisions should be re-evaluated eventually
4. **Add Context**: Include info the AI can't access (deployment, architecture, business decisions)
5. **Review Regularly**: Check expired issues monthly
6. **Collaborate**: Get team input on important decisions
7. **Update When Wrong**: If new info changes your decision, update the file

---

## 🎓 Training the AI

The more detailed your reasoning:

- The better the AI understands your decision process
- The more likely it will make similar decisions automatically
- The easier for new team members to understand
- The better audit trail for compliance

Think of these files as teaching the AI your organization's security philosophy!

---

## ❓ FAQ

**Q: Should I document every false positive?**
A: Document recurring ones or those that need explanation. One-off obvious false positives don't need documentation.

**Q: What if I disagree with a previous review?**
A: Update the file with new reasoning and your name. Git history preserves the discussion.

**Q: Can I delete old reviews?**
A: Yes, if the issue no longer applies (e.g., dependency removed). But consider keeping for historical context.

**Q: Do these affect automated analysis?**
A: Yes! The AI reads these FIRST and incorporates your reasoning into its analysis.

---

## 🚀 Quick Start

```bash
# 1. Add your first issue
python manage_known_issues.py add

# 2. See what you created
python manage_known_issues.py list

# 3. View full details
python manage_known_issues.py show <your-issue-id>

# 4. Run analysis - AI will use your documented knowledge!
python analyze_dependencies.py
```
