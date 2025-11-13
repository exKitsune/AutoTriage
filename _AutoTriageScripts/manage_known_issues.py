#!/usr/bin/env python3
"""
Known Issues Management CLI

Manage human-reviewed security and quality issues with documented context.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


class KnownIssuesManager:
    """Manager for known issues database."""
    
    def __init__(self, known_issues_dir: Path = None):
        if known_issues_dir is None:
            script_dir = Path(__file__).parent
            known_issues_dir = script_dir / "known_issues"
        
        self.known_issues_dir = Path(known_issues_dir)
        self.known_issues_dir.mkdir(exist_ok=True)
    
    def list_all(self, status_filter: str = None) -> List[Dict[str, Any]]:
        """List all known issues."""
        issues = []
        
        for yaml_file in sorted(self.known_issues_dir.glob("*.yaml")):
            if yaml_file.name.startswith("."):  # Skip .template.yaml
                continue
            
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                    if data:  # Skip empty files
                        data["_filename"] = yaml_file.name
                        
                        # Apply filter if specified
                        if status_filter is None or data.get("status") == status_filter:
                            issues.append(data)
            except Exception as e:
                print(f"Warning: Could not load {yaml_file.name}: {e}", file=sys.stderr)
        
        return issues
    
    def show_summary(self):
        """Show summary statistics of known issues."""
        issues = self.list_all()
        
        if not issues:
            print("\n📂 Known Issues: Empty")
            print("No known issues documented yet.\n")
            return
        
        # Statistics
        total = len(issues)
        by_status = Counter(issue.get("status", "unknown") for issue in issues)
        
        # Check for expired reviews
        expired = []
        expiring_soon = []
        today = datetime.now()
        
        for issue in issues:
            if issue.get("expires"):
                try:
                    expire_date = datetime.strptime(issue["expires"], "%Y-%m-%d")
                    days_until = (expire_date - today).days
                    
                    if days_until < 0:
                        expired.append(issue)
                    elif days_until < 30:
                        expiring_soon.append(issue)
                except:
                    pass
        
        print(f"\n{'='*70}")
        print(f"📊 Known Issues Summary")
        print(f"{'='*70}\n")
        
        print(f"Total Reviews: {total}")
        print(f"\nBy Status:")
        for status, count in by_status.most_common():
            emoji = {
                "not_applicable": "✅",
                "accepted_risk": "⚠️",
                "mitigated": "🛡️",
                "wont_fix": "🚫"
            }.get(status, "❓")
            print(f"  {emoji} {status}: {count}")
        
        if expired:
            print(f"\n⏰ Expired Reviews: {len(expired)}")
            for issue in expired[:5]:  # Show first 5
                print(f"  - {issue.get('problem_id', 'unknown')} (expired {issue.get('expires')})")
            if len(expired) > 5:
                print(f"  ... and {len(expired) - 5} more")
        
        if expiring_soon:
            print(f"\n⚠️  Expiring Soon (within 30 days): {len(expiring_soon)}")
            for issue in expiring_soon[:5]:
                print(f"  - {issue.get('problem_id', 'unknown')} (expires {issue.get('expires')})")
            if len(expiring_soon) > 5:
                print(f"  ... and {len(expiring_soon) - 5} more")
        
        print(f"\n{'='*70}\n")
    
    def list_issues(self, status_filter: str = None, show_details: bool = False):
        """List known issues in a readable format."""
        issues = self.list_all(status_filter)
        
        if not issues:
            if status_filter:
                print(f"\nNo issues found with status: {status_filter}\n")
            else:
                print("\nNo known issues documented yet.\n")
            return
        
        print(f"\n{'='*70}")
        if status_filter:
            print(f"Known Issues (Status: {status_filter})")
        else:
            print(f"Known Issues (All)")
        print(f"{'='*70}\n")
        
        for issue in issues:
            status = issue.get("status", "unknown")
            problem_id = issue.get("problem_id", "unknown")
            title = issue.get("title", "No title")
            reviewed_by = issue.get("reviewed_by", "Unknown")
            review_date = issue.get("review_date", "Unknown")
            
            emoji = {
                "not_applicable": "✅",
                "accepted_risk": "⚠️",
                "mitigated": "🛡️",
                "wont_fix": "🚫"
            }.get(status, "❓")
            
            print(f"{emoji} {problem_id}")
            print(f"   {title}")
            print(f"   Status: {status} | Reviewed by: {reviewed_by} | Date: {review_date}")
            
            if show_details:
                reasoning = issue.get("human_reasoning", "")
                if reasoning:
                    # Show first 100 chars of reasoning
                    reasoning_preview = reasoning.strip().split('\n')[0][:100]
                    if len(reasoning) > 100:
                        reasoning_preview += "..."
                    print(f"   Reasoning: {reasoning_preview}")
            
            print()
        
        print(f"Total: {len(issues)} issue(s)\n")
    
    def show_issue(self, problem_id: str):
        """Show detailed information about a specific issue."""
        # Try exact match first
        yaml_file = self.known_issues_dir / f"{problem_id}.yaml"
        
        if not yaml_file.exists():
            # Try with sanitized ID
            sanitized_id = problem_id.replace(":", "_").replace("/", "_")
            yaml_file = self.known_issues_dir / f"{sanitized_id}.yaml"
        
        if not yaml_file.exists():
            print(f"\n❌ Issue not found: {problem_id}\n")
            print("💡 Use 'list' command to see all known issues\n")
            return
        
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        
        print(f"\n{'='*70}")
        print(f"📋 Known Issue Details")
        print(f"{'='*70}\n")
        
        print(f"Problem ID: {data.get('problem_id', 'N/A')}")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")
        print(f"Reviewed by: {data.get('reviewed_by', 'N/A')}")
        print(f"Review Date: {data.get('review_date', 'N/A')}")
        
        if data.get('expires'):
            print(f"Expires: {data['expires']}")
        
        if data.get('re_evaluate_on'):
            print(f"Re-evaluate on: {data['re_evaluate_on']}")
        
        print(f"\n--- Human Reasoning ---")
        print(data.get('human_reasoning', 'N/A'))
        
        if data.get('context'):
            print(f"\n--- Additional Context ---")
            for item in data['context']:
                print(f"  • {item}")
        
        if data.get('evidence'):
            print(f"\n--- Evidence ---")
            for item in data['evidence']:
                print(f"  • {item}")
        
        print(f"\n{'='*70}")
        print(f"File: {yaml_file.name}")
        print(f"{'='*70}\n")
    
    def add_issue(self, interactive: bool = True):
        """Add a new known issue."""
        if interactive:
            return self._add_interactive()
        else:
            print("Non-interactive mode not yet implemented. Use --interactive")
            return False
    
    def _add_interactive(self):
        """Add issue interactively."""
        print(f"\n{'='*70}")
        print("Add New Known Issue")
        print(f"{'='*70}\n")
        
        # Gather information
        problem_id = input("Problem ID (e.g., CVE-2020-14343): ").strip()
        if not problem_id:
            print("❌ Problem ID is required")
            return False
        
        title = input("Title: ").strip()
        
        print("\nStatus options:")
        print("  1. not_applicable - False positive, doesn't apply")
        print("  2. accepted_risk - Real issue but we accept the risk")
        print("  3. mitigated - Real issue but we have mitigations")
        print("  4. wont_fix - Real issue but won't fix")
        status_choice = input("Choose status (1-4): ").strip()
        
        status_map = {
            "1": "not_applicable",
            "2": "accepted_risk",
            "3": "mitigated",
            "4": "wont_fix"
        }
        status = status_map.get(status_choice, "not_applicable")
        
        print("\nHuman reasoning (explain your decision):")
        print("(Enter your text, then press Ctrl+D on Unix or Ctrl+Z on Windows when done)")
        reasoning_lines = []
        try:
            while True:
                line = input()
                reasoning_lines.append(line)
        except EOFError:
            pass
        reasoning = "\n".join(reasoning_lines).strip()
        
        if not reasoning:
            print("\n❌ Reasoning is required")
            return False
        
        reviewed_by = input("\nReviewed by (name/team): ").strip() or "Unknown"
        
        # Optional fields
        add_more = input("\nAdd additional context/evidence? (y/n): ").strip().lower()
        context = []
        evidence = []
        
        if add_more == 'y':
            print("\nContext items (one per line, empty line to finish):")
            while True:
                item = input("  • ").strip()
                if not item:
                    break
                context.append(item)
            
            print("\nEvidence items (one per line, empty line to finish):")
            while True:
                item = input("  • ").strip()
                if not item:
                    break
                evidence.append(item)
        
        # Create data structure
        data = {
            "problem_id": problem_id,
            "title": title,
            "status": status,
            "human_reasoning": reasoning,
            "reviewed_by": reviewed_by,
            "review_date": datetime.now().strftime("%Y-%m-%d"),
        }
        
        if context:
            data["context"] = context
        if evidence:
            data["evidence"] = evidence
        
        # Create filename
        safe_id = problem_id.replace(":", "_").replace("/", "_").replace(" ", "-")
        filename = f"{safe_id}.yaml"
        filepath = self.known_issues_dir / filename
        
        if filepath.exists():
            overwrite = input(f"\n⚠️  File already exists: {filename}\nOverwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                print("❌ Cancelled")
                return False
        
        # Save file
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"\n✅ Created: {filepath}")
        print(f"💡 You can edit {filename} to add more details")
        print()
        
        return True
    
    def search(self, query: str):
        """Search known issues by text."""
        issues = self.list_all()
        matches = []
        
        query_lower = query.lower()
        
        for issue in issues:
            # Search in various fields
            searchable = [
                issue.get("problem_id", ""),
                issue.get("title", ""),
                issue.get("human_reasoning", ""),
                " ".join(issue.get("context", [])),
                " ".join(issue.get("evidence", []))
            ]
            
            searchable_text = " ".join(searchable).lower()
            
            if query_lower in searchable_text:
                matches.append(issue)
        
        if not matches:
            print(f"\nNo issues found matching: {query}\n")
            return
        
        print(f"\n{'='*70}")
        print(f"Search Results for: {query}")
        print(f"{'='*70}\n")
        
        for issue in matches:
            problem_id = issue.get("problem_id", "unknown")
            title = issue.get("title", "No title")
            status = issue.get("status", "unknown")
            
            print(f"📋 {problem_id} - {title}")
            print(f"   Status: {status}")
            print()
        
        print(f"Found {len(matches)} match(es)\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage known issues database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show summary statistics
  python manage_known_issues.py summary
  
  # List all known issues
  python manage_known_issues.py list
  
  # List only false positives
  python manage_known_issues.py list --status not_applicable
  
  # Show details of a specific issue
  python manage_known_issues.py show CVE-2020-14343
  
  # Search for issues
  python manage_known_issues.py search "PyYAML"
  
  # Add a new issue
  python manage_known_issues.py add
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Summary command
    subparsers.add_parser("summary", help="Show summary statistics")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List known issues")
    list_parser.add_argument("--status", choices=["not_applicable", "accepted_risk", "mitigated", "wont_fix"],
                            help="Filter by status")
    list_parser.add_argument("--details", action="store_true", help="Show more details")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show details of a specific issue")
    show_parser.add_argument("problem_id", help="Problem ID to show")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search issues by text")
    search_parser.add_argument("query", help="Search query")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new known issue")
    add_parser.add_argument("--interactive", action="store_true", default=True,
                           help="Interactive mode (default)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = KnownIssuesManager()
    
    # Execute command
    if args.command == "summary":
        manager.show_summary()
    
    elif args.command == "list":
        manager.list_issues(status_filter=args.status, show_details=args.details)
    
    elif args.command == "show":
        manager.show_issue(args.problem_id)
    
    elif args.command == "search":
        manager.search(args.query)
    
    elif args.command == "add":
        manager.add_issue(interactive=args.interactive)


if __name__ == "__main__":
    main()

