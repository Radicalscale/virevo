"""
AI Node Fixer - Iteratively analyzes, tests, and fixes node sequences
Uses the same approach as a human developer would: examine, test, identify issues, fix, re-test
"""
import asyncio
import json
import logging
import time
import copy
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class FixerStatus(str, Enum):
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    TESTING = "testing"
    IDENTIFYING_ISSUES = "identifying_issues"
    PROPOSING_FIX = "proposing_fix"
    APPLYING_FIX = "applying_fix"
    RETESTING = "retesting"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class FixerUpdate:
    """Progress update sent to frontend"""
    status: FixerStatus
    iteration: int
    max_iterations: int
    message: str
    details: Optional[Dict] = None
    node_changes: Optional[List[Dict]] = None
    test_results: Optional[Dict] = None

class AINodeFixer:
    """
    AI-powered node sequence fixer that iteratively:
    1. Analyzes nodes (prompts, goals, transitions, variables)
    2. Tests with simulated responses
    3. Identifies issues from test failures
    4. Proposes and applies fixes
    5. Re-tests until working or max iterations reached
    """
    
    def __init__(
        self, 
        agent_config: Dict,
        llm_client,
        llm_provider: str,
        llm_model: str,
        max_iterations: int = 5
    ):
        self.agent_config = agent_config
        self.llm_client = llm_client
        self.llm_provider = llm_provider
        self.llm_model = llm_model  # Use exactly what agent has configured
        self.max_iterations = max_iterations
        self.cancelled = False
        
        # Working copy of nodes (we modify this, not the original)
        self.working_nodes = {}
        self.original_nodes = {}
        self.changes_made = []
        
    def cancel(self):
        """Cancel the fixing operation"""
        self.cancelled = True
        
    async def fix_sequence(
        self,
        node_ids: List[str],
        test_responses: List[str],
        expected_behavior: str = "",
        initial_variables: Optional[Dict] = None
    ) -> AsyncGenerator[FixerUpdate, None]:
        """
        Main entry point - iteratively fix a node sequence.
        Yields progress updates for real-time UI feedback.
        """
        from node_tester import NodeTester
        
        iteration = 0
        
        # Initialize
        yield FixerUpdate(
            status=FixerStatus.INITIALIZING,
            iteration=0,
            max_iterations=self.max_iterations,
            message="Initializing AI Node Fixer...",
            details={"node_count": len(node_ids)}
        )
        
        # Create working copies of nodes
        call_flow = self.agent_config.get("call_flow", [])
        for node in call_flow:
            node_id = str(node.get("id"))
            self.original_nodes[node_id] = copy.deepcopy(node)
            self.working_nodes[node_id] = copy.deepcopy(node)
        
        # Verify all requested nodes exist
        missing = [nid for nid in node_ids if str(nid) not in self.working_nodes]
        if missing:
            yield FixerUpdate(
                status=FixerStatus.FAILED,
                iteration=0,
                max_iterations=self.max_iterations,
                message=f"Nodes not found: {missing}"
            )
            return
        
        while iteration < self.max_iterations and not self.cancelled:
            iteration += 1
            
            # Step 1: Analyze nodes
            yield FixerUpdate(
                status=FixerStatus.ANALYZING,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message=f"Analyzing {len(node_ids)} nodes for potential issues..."
            )
            
            analysis = await self._analyze_nodes(node_ids, expected_behavior)
            
            if self.cancelled:
                yield FixerUpdate(
                    status=FixerStatus.CANCELLED,
                    iteration=iteration,
                    max_iterations=self.max_iterations,
                    message="Operation cancelled by user"
                )
                return
            
            # Step 2: Test current state
            yield FixerUpdate(
                status=FixerStatus.TESTING,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message="Running test with simulated responses...",
                details={"analysis_summary": analysis.get("summary", "")}
            )
            
            # Create tester with working nodes
            working_agent = copy.deepcopy(self.agent_config)
            working_agent["call_flow"] = list(self.working_nodes.values())
            
            tester = NodeTester(
                working_agent, 
                llm_client=self.llm_client,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model
            )
            
            test_result = await tester.test_node_sequence(
                node_ids=node_ids,
                responses=test_responses,
                initial_variables=initial_variables
            )
            
            if self.cancelled:
                yield FixerUpdate(
                    status=FixerStatus.CANCELLED,
                    iteration=iteration,
                    max_iterations=self.max_iterations,
                    message="Operation cancelled by user"
                )
                return
            
            # Step 3: Check if tests pass
            issues = self._identify_issues(test_result, expected_behavior)
            
            yield FixerUpdate(
                status=FixerStatus.IDENTIFYING_ISSUES,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message=f"Found {len(issues)} issue(s)" if issues else "All tests passing!",
                test_results=test_result,
                details={"issues": issues}
            )
            
            if not issues:
                # Success! Return the fixed nodes
                yield FixerUpdate(
                    status=FixerStatus.SUCCESS,
                    iteration=iteration,
                    max_iterations=self.max_iterations,
                    message="All tests passing! Node sequence is working correctly.",
                    test_results=test_result,
                    node_changes=self.changes_made,
                    details={"total_changes": len(self.changes_made)}
                )
                return
            
            # Step 4: Propose fixes
            yield FixerUpdate(
                status=FixerStatus.PROPOSING_FIX,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message="AI is analyzing issues and proposing fixes..."
            )
            
            fixes = await self._propose_fixes(node_ids, issues, test_result, analysis)
            
            if not fixes:
                yield FixerUpdate(
                    status=FixerStatus.FAILED,
                    iteration=iteration,
                    max_iterations=self.max_iterations,
                    message="Could not determine appropriate fixes for the identified issues.",
                    details={"issues": issues}
                )
                return
            
            # Step 5: Apply fixes
            yield FixerUpdate(
                status=FixerStatus.APPLYING_FIX,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message=f"Applying {len(fixes)} fix(es)...",
                details={"fixes": fixes}
            )
            
            for fix in fixes:
                self._apply_fix(fix)
                self.changes_made.append(fix)
            
            # Loop continues to re-test
            yield FixerUpdate(
                status=FixerStatus.RETESTING,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message="Re-testing with applied fixes..."
            )
        
        # Max iterations reached
        if self.cancelled:
            yield FixerUpdate(
                status=FixerStatus.CANCELLED,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message="Operation cancelled by user"
            )
        else:
            yield FixerUpdate(
                status=FixerStatus.FAILED,
                iteration=iteration,
                max_iterations=self.max_iterations,
                message=f"Could not fix all issues after {self.max_iterations} iterations.",
                node_changes=self.changes_made,
                details={"partial_fixes": len(self.changes_made)}
            )
    
    async def _analyze_nodes(self, node_ids: List[str], expected_behavior: str) -> Dict:
        """Use LLM to analyze nodes for potential issues"""
        
        nodes_info = []
        for node_id in node_ids:
            node = self.working_nodes.get(str(node_id), {})
            data = node.get("data", {})
            nodes_info.append({
                "id": node_id,
                "label": node.get("label") or data.get("label") or node_id,
                "type": node.get("type") or data.get("type"),
                "content": data.get("content", "")[:500],
                "extract_variables": data.get("extract_variables", []),
                "transitions": data.get("transitions", []),
                "webhook": data.get("webhook", {})
            })
        
        prompt = f"""Analyze these voice agent nodes for potential issues:

NODES:
{json.dumps(nodes_info, indent=2)}

EXPECTED BEHAVIOR:
{expected_behavior or "User should be able to progress through the conversation and have variables correctly extracted."}

Look for:
1. Variable extraction issues (unclear descriptions, missing hints, case sensitivity)
2. Transition logic problems (overlapping conditions, missing defaults, unreachable paths)
3. Prompt/content issues (unclear questions, missing context)
4. Webhook payload problems (missing variables, wrong variable names)
5. Flow issues (dead ends, circular references)

Return a JSON object with:
{{
  "summary": "Brief overall assessment",
  "potential_issues": [
    {{
      "node_id": "...",
      "issue_type": "extraction|transition|content|webhook|flow",
      "description": "...",
      "severity": "high|medium|low"
    }}
  ],
  "recommendations": ["..."]
}}"""

        try:
            if self.llm_provider == "anthropic":
                response = await self.llm_client.messages.create(
                    model=self.llm_model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2000
                )
                result_text = response.choices[0].message.content
            
            # Parse JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            return json.loads(result_text.strip())
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {"summary": "Analysis failed", "potential_issues": [], "recommendations": []}
    
    def _identify_issues(self, test_result: Dict, expected_behavior: str) -> List[Dict]:
        """Identify issues from test results"""
        issues = []
        
        # Check for explicit issues
        if test_result.get("issues_found"):
            for issue in test_result["issues_found"]:
                issues.append({
                    "type": "test_failure",
                    "description": issue,
                    "source": "test_result"
                })
        
        # Check each step for problems
        for step in test_result.get("steps", []):
            # Extraction errors
            extraction = step.get("extraction", {})
            if extraction.get("errors"):
                for err in extraction["errors"]:
                    issues.append({
                        "type": "extraction_error",
                        "node_id": step.get("node_id"),
                        "description": err,
                        "source": "extraction"
                    })
            
            # Missing extractions
            if extraction.get("variables_requested"):
                extracted = extraction.get("extracted", {})
                for var in extraction["variables_requested"]:
                    if var not in extracted or extracted[var] is None:
                        issues.append({
                            "type": "missing_variable",
                            "node_id": step.get("node_id"),
                            "description": f"Variable '{var}' was not extracted",
                            "source": "extraction"
                        })
            
            # Webhook missing variables
            webhook = step.get("webhook_preview", {})
            if webhook.get("missing_variables"):
                for missing in webhook["missing_variables"]:
                    issues.append({
                        "type": "webhook_missing_var",
                        "node_id": step.get("node_id"),
                        "description": f"Webhook missing variable: {missing.get('expected_variable')}",
                        "source": "webhook"
                    })
            
            # Transition issues
            transition = step.get("transition", {})
            if transition.get("errors"):
                for err in transition["errors"]:
                    issues.append({
                        "type": "transition_error",
                        "node_id": step.get("node_id"),
                        "description": err,
                        "source": "transition"
                    })
            
            # Step-level errors/warnings
            for err in step.get("errors", []):
                issues.append({
                    "type": "step_error",
                    "node_id": step.get("node_id"),
                    "description": err,
                    "source": "step"
                })
            
            for warn in step.get("warnings", []):
                issues.append({
                    "type": "warning",
                    "node_id": step.get("node_id"),
                    "description": warn,
                    "source": "step"
                })
        
        return issues
    
    async def _propose_fixes(
        self, 
        node_ids: List[str], 
        issues: List[Dict], 
        test_result: Dict,
        analysis: Dict
    ) -> List[Dict]:
        """Use LLM to propose specific fixes for identified issues"""
        
        # Get current node state
        nodes_state = {}
        for node_id in node_ids:
            node = self.working_nodes.get(str(node_id), {})
            nodes_state[str(node_id)] = {
                "label": node.get("label") or node.get("data", {}).get("label"),
                "data": node.get("data", {})
            }
        
        prompt = f"""Based on test results and identified issues, propose specific fixes for these voice agent nodes.

CURRENT NODE STATE:
{json.dumps(nodes_state, indent=2)}

IDENTIFIED ISSUES:
{json.dumps(issues, indent=2)}

TEST RESULTS SUMMARY:
- Success: {test_result.get('success')}
- Final variables: {json.dumps(test_result.get('final_variables', {}))}

ANALYSIS RECOMMENDATIONS:
{json.dumps(analysis.get('recommendations', []))}

For each issue, propose a specific fix. Return a JSON array of fixes:
[
  {{
    "node_id": "the node ID to fix",
    "fix_type": "extract_variables|transition|content|webhook|variable_sync",
    "field_path": "data.extract_variables[0].description",  // dot notation path to the field
    "old_value": "the current value (for reference)",
    "new_value": "the proposed new value",
    "reason": "why this fix addresses the issue"
  }}
]

Common fixes:
- For extraction issues: improve variable description, add extraction_hint
- For case sensitivity: ensure variable names match exactly
- For webhook missing vars: add variable sync logic or fix variable names
- For transitions: fix conditions, add default paths

Return ONLY the JSON array, no explanation."""

        try:
            if self.llm_provider == "anthropic":
                response = await self.llm_client.messages.create(
                    model=self.llm_model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
            else:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2000
                )
                result_text = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            fixes = json.loads(result_text.strip())
            return fixes if isinstance(fixes, list) else []
            
        except Exception as e:
            logger.error(f"Fix proposal error: {e}")
            return []
    
    def _apply_fix(self, fix: Dict):
        """Apply a fix to the working nodes"""
        node_id = str(fix.get("node_id"))
        field_path = fix.get("field_path", "")
        new_value = fix.get("new_value")
        
        if node_id not in self.working_nodes:
            logger.warning(f"Cannot apply fix: node {node_id} not found")
            return
        
        node = self.working_nodes[node_id]
        
        # Parse field path and set value
        try:
            parts = field_path.split(".")
            obj = node
            
            for i, part in enumerate(parts[:-1]):
                # Handle array indexing like "extract_variables[0]"
                if "[" in part:
                    key = part.split("[")[0]
                    idx = int(part.split("[")[1].rstrip("]"))
                    obj = obj.get(key, [])[idx]
                else:
                    if part not in obj:
                        obj[part] = {}
                    obj = obj[part]
            
            # Set the final value
            final_part = parts[-1]
            if "[" in final_part:
                key = final_part.split("[")[0]
                idx = int(final_part.split("[")[1].rstrip("]"))
                obj[key][idx] = new_value
            else:
                obj[final_part] = new_value
                
            logger.info(f"Applied fix to {node_id}: {field_path} = {new_value}")
            
        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
    
    def get_fixed_nodes(self) -> List[Dict]:
        """Get the fixed nodes (working copies with changes applied)"""
        return list(self.working_nodes.values())
    
    def get_changes_summary(self) -> List[Dict]:
        """Get summary of all changes made"""
        return self.changes_made
