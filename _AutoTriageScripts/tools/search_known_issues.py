"""
search_known_issues tool - Search for related human reviews using keywords

This tool searches the known_issues database using keywords/concepts to find
potentially relevant human reviews. The LLM should generate search terms based
on the problem context (vulnerability name, package name, technology, etc.).

IMPORTANT: Call this tool FIRST before any other investigation to find if humans
have reviewed similar or related issues.
"""

from pathlib import Path
from typing import Dict, Any, List
import re

from .base_tool import BaseTool


class SearchKnownIssuesTool(BaseTool):
    """Search for related human reviews using keywords."""
    
    # Tool metadata
    name = "search_known_issues"
    description = "Search known issues database using keywords to find related human reviews. Generate search terms from the problem context (package names, vulnerability types, technologies, file paths). Returns list of potentially relevant reviews."
    
    parameters = {
        "search_terms": {
            "type": "array",
            "description": "Keywords to search for (e.g., ['PyYAML', 'arbitrary code execution'], ['Docker', 'version tag'], ['dependency', 'not used']). Generate terms from problem context.",
            "required": True
        },
        "problem_id": {
            "type": "string",
            "description": "The specific problem ID if known (will be prioritized in results)",
            "required": False
        }
    }
    
    returns = {
        "success": "boolean - Whether the search was successful",
        "found_count": "number - How many matches were found",
        "matches": "array - List of matching issues with relevance scores",
        "message": "string - Guidance message"
    }
    
    requirements = []  # No special requirements
    
    example = {
        "call": {
            "tool": "search_known_issues",
            "parameters": {
                "search_terms": ["PyYAML", "vulnerability", "not used", "transitive dependency"],
                "problem_id": "CVE-2020-14343"
            }
        },
        "result": {
            "success": True,
            "found_count": 2,
            "matches": [
                {
                    "problem_id": "CVE-2020-14343",
                    "title": "PyYAML arbitrary code execution vulnerability",
                    "status": "not_applicable",
                    "relevance_score": 0.95,
                    "match_reasons": ["Exact ID match", "Contains: PyYAML, vulnerability"],
                    "human_reasoning": "PyYAML is only a transitive dependency...",
                    "reviewed_by": "Security Team",
                    "review_date": "2025-11-13"
                },
                {
                    "problem_id": "CVE-2021-12345",
                    "title": "Another PyYAML issue",
                    "status": "not_applicable",
                    "relevance_score": 0.65,
                    "match_reasons": ["Contains: PyYAML"],
                    "human_reasoning": "PyYAML not imported...",
                    "reviewed_by": "Security Team",
                    "review_date": "2025-10-15"
                }
            ],
            "message": "Found 2 potential matches. Review them to see if any are relevant to your current investigation."
        }
    }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search known issues using keywords.
        
        Args:
            params: Dict with 'search_terms' (array) and optional 'problem_id'
        
        Returns:
            Dict with list of matching issues and relevance scores
        """
        search_terms = params.get("search_terms", [])
        problem_id = params.get("problem_id")
        
        if not search_terms:
            return {
                "success": False,
                "error": "search_terms parameter is required (array of keywords)"
            }
        
        # Ensure search_terms is a list
        if isinstance(search_terms, str):
            search_terms = [search_terms]
        
        # Known issues directory
        known_issues_dir = self.workspace_root / "_AutoTriageScripts" / "known_issues"
        
        if not known_issues_dir.exists():
            return {
                "success": True,
                "found_count": 0,
                "matches": [],
                "message": "Known issues database not initialized. Proceed with normal investigation."
            }
        
        # Search all YAML files
        matches = []
        
        try:
            import yaml
        except ImportError:
            return {
                "success": False,
                "error": "PyYAML library not available. Cannot search known issues database."
            }
        
        for yaml_file in known_issues_dir.glob("*.yaml"):
            # Skip template and hidden files
            if yaml_file.name.startswith(".") or yaml_file.name.startswith("_"):
                continue
            
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                # Calculate relevance score
                score, match_reasons = self._calculate_relevance(
                    data, search_terms, problem_id
                )
                
                if score > 0:
                    # This issue matches
                    match_info = {
                        "problem_id": data.get("problem_id", "unknown"),
                        "title": data.get("title", "No title"),
                        "status": data.get("status", "unknown"),
                        "relevance_score": round(score, 2),
                        "match_reasons": match_reasons,
                        "human_reasoning": self._truncate(data.get("human_reasoning", ""), 200),
                        "reviewed_by": data.get("reviewed_by", "Unknown"),
                        "review_date": data.get("review_date", "Unknown")
                    }
                    
                    # Include context and evidence if available
                    if data.get("context"):
                        match_info["context"] = data["context"][:3]  # First 3 items
                    
                    if data.get("evidence"):
                        match_info["evidence"] = data["evidence"][:3]  # First 3 items
                    
                    matches.append(match_info)
                    
            except Exception as e:
                # Skip files that can't be parsed
                continue
        
        # Sort by relevance score (highest first)
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Limit to top 5 matches to avoid overwhelming the LLM
        matches = matches[:5]
        
        if not matches:
            return {
                "success": True,
                "found_count": 0,
                "matches": [],
                "message": "No matching human reviews found. Proceed with normal investigation."
            }
        
        return {
            "success": True,
            "found_count": len(matches),
            "matches": matches,
            "message": f"Found {len(matches)} potential match(es). Review them to see if any are relevant. Pay special attention to high-scoring matches."
        }
    
    def _calculate_relevance(
        self, 
        data: Dict[str, Any], 
        search_terms: List[str], 
        problem_id: str = None
    ) -> tuple[float, List[str]]:
        """
        Calculate relevance score for an issue.
        
        Returns:
            Tuple of (score, list of match reasons)
        """
        score = 0.0
        match_reasons = []
        
        # Build searchable text (all fields combined, lowercase)
        searchable_fields = [
            data.get("problem_id", ""),
            data.get("title", ""),
            data.get("human_reasoning", ""),
            " ".join(data.get("context", [])),
            " ".join(data.get("evidence", [])),
            data.get("status", ""),
        ]
        searchable_text = " ".join(searchable_fields).lower()
        
        # Exact problem ID match (highest priority)
        if problem_id:
            file_id = data.get("problem_id", "").lower()
            query_id = problem_id.lower()
            
            # Try exact match and common variations
            id_variations = [
                query_id,
                query_id.replace(":", "-"),
                query_id.replace(":", "_"),
                query_id.replace("/", "-"),
            ]
            
            for variation in id_variations:
                if variation in file_id or file_id in variation:
                    score += 10.0  # Very high weight for ID match
                    match_reasons.append("Exact or partial ID match")
                    break
        
        # Search term matching
        terms_found = []
        for term in search_terms:
            term_lower = term.lower().strip()
            if not term_lower:
                continue
            
            # Check for exact phrase
            if term_lower in searchable_text:
                # Calculate frequency
                frequency = searchable_text.count(term_lower)
                
                # Weight by field importance
                title_weight = 3.0 if term_lower in data.get("title", "").lower() else 0
                reasoning_weight = 2.0 if term_lower in data.get("human_reasoning", "").lower() else 0
                context_weight = 1.5 if term_lower in " ".join(data.get("context", [])).lower() else 0
                evidence_weight = 1.5 if term_lower in " ".join(data.get("evidence", [])).lower() else 0
                
                term_score = (title_weight + reasoning_weight + context_weight + evidence_weight) * min(frequency, 3)
                score += term_score
                terms_found.append(term)
        
        if terms_found:
            match_reasons.append(f"Contains: {', '.join(terms_found[:5])}")
        
        # Bonus for status-related terms
        status = data.get("status", "").lower()
        status_terms = {
            "false positive": ["false", "positive", "not applicable"],
            "accepted risk": ["accept", "risk", "known risk"],
            "mitigated": ["mitigate", "fix", "workaround"],
        }
        
        for status_type, terms in status_terms.items():
            if status_type.replace(" ", "_") == status:
                for term in search_terms:
                    if any(st in term.lower() for st in terms):
                        score += 0.5
                        break
        
        # Normalize score (cap at 10.0)
        score = min(score, 10.0)
        
        return score, match_reasons
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + "..."

