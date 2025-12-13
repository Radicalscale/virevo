"""
Node Sequence Tester - Tests node flows with exact same code paths as live calls
"""
import asyncio
import json
import logging
import time
import re
import aiohttp
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
import os

logger = logging.getLogger(__name__)

class NodeTester:
    """
    Tests node sequences using the exact same logic as live calls.
    Provides transparent visibility into all intermediate values.
    """
    
    def __init__(self, agent_config: Dict, llm_client = None, llm_provider: str = "openai", llm_model: str = None):
        self.agent_config = agent_config
        self.call_flow = agent_config.get("call_flow", [])
        self.session_variables: Dict[str, Any] = {}
        self.conversation_history: List[Dict] = []
        self.llm_client = llm_client
        self.llm_provider = llm_provider
        self.llm_model = llm_model or self._get_default_model(llm_provider)
        
        # Build node lookup
        self.nodes_by_id = {}
        for node in self.call_flow:
            node_id = node.get("id")
            if node_id:
                self.nodes_by_id[node_id] = node
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        defaults = {
            "openai": "gpt-4o-mini",
            "grok": "grok-2-latest",
            "groq": "llama-3.1-70b-versatile",
            "anthropic": "claude-3-sonnet-20240229"
        }
        return defaults.get(provider, "gpt-4o-mini")
    
    async def _get_llm_client(self):
        """Get LLM client"""
        if self.llm_client:
            return self.llm_client
        raise ValueError(f"No LLM client available for provider: {self.llm_provider}")
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node by ID"""
        return self.nodes_by_id.get(node_id)
    
    def get_node_label(self, node: Dict) -> str:
        """Get human-readable node label"""
        if not node:
            return "Unknown"
        # Label can be at node.label (top level) or node.data.label
        data = node.get("data", {})
        return node.get("label") or data.get("label") or node.get("id", "Unknown")
    
    async def test_single_node(
        self,
        node_id: str,
        user_response: str,
        initial_variables: Optional[Dict] = None
    ) -> Dict:
        """
        Test a single node with a simulated user response.
        Returns detailed breakdown of what happened.
        """
        result = {
            "node_id": node_id,
            "node_label": "",
            "user_response": user_response,
            "success": False,
            "extraction": None,
            "transition": None,
            "webhook_preview": None,
            "errors": [],
            "warnings": []
        }
        
        # Initialize variables
        if initial_variables:
            self.session_variables = initial_variables.copy()
            # Sync customer_name and callerName at initialization
            if "customer_name" in self.session_variables and "callerName" not in self.session_variables:
                self.session_variables["callerName"] = self.session_variables["customer_name"]
            elif "callerName" in self.session_variables and "customer_name" not in self.session_variables:
                self.session_variables["customer_name"] = self.session_variables["callerName"]
        
        # Get node
        node = self.get_node(node_id)
        if not node:
            result["errors"].append(f"Node '{node_id}' not found")
            return result
        
        data = node.get("data", {})
        result["node_label"] = self.get_node_label(node)
        result["node_content"] = data.get("content", "")[:200]
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": data.get("content", "")
        })
        self.conversation_history.append({
            "role": "user", 
            "content": user_response
        })
        
        # 1. Test Variable Extraction
        extract_variables = data.get("extract_variables", [])
        if extract_variables:
            extraction_result = await self._test_extraction(
                extract_variables, 
                user_response
            )
            result["extraction"] = extraction_result
            
            # Check for sync issues (with null safety)
            if extraction_result and isinstance(extraction_result, dict):
                extracted = extraction_result.get("extracted", {}) or {}
                if "customer_name" in extracted or "callerName" in extracted:
                    self._check_name_sync(extraction_result, result)
        
        # 2. Test Transition Logic (BEFORE webhook, since some transitions depend on pre-webhook state)
        transitions = data.get("transitions", [])
        pre_webhook_transition = None
        
        # 3. Execute Webhook (handle both nested webhook object and flat webhook_url format)
        webhook = data.get("webhook", {})
        node_type = node.get("type", "")
        webhook_result = None
        
        # Check for function node format (webhook_url at data level)
        if node_type == "function" and data.get("webhook_url"):
            logger.info(f"🔧 Function node detected - building webhook from flat format")
            webhook = self._build_webhook_from_function_node(data)
        
        if webhook and webhook.get("url"):
            webhook_result = await self._execute_webhook(webhook)
            result["webhook"] = webhook_result
            result["webhook_execution"] = webhook_result  # Alias for clarity
            
            # Check for variable issues
            if webhook_result.get("missing_variables"):
                for missing in webhook_result["missing_variables"]:
                    result["warnings"].append(
                        f"⚠️ Webhook missing variable: {missing.get('expected_variable')}"
                    )
            
            # If webhook failed, add error
            if webhook_result.get("error"):
                result["errors"].append(f"Webhook error: {webhook_result['error']}")
            
            # Show webhook status
            if webhook_result.get("executed"):
                status = webhook_result.get("response_status", "unknown")
                if status >= 400:
                    result["errors"].append(f"Webhook returned error status: {status}")
                
                # Store webhook response in session variables for transition evaluation
                response_variable = data.get("response_variable", "webhook_response")
                self.session_variables[response_variable] = webhook_result.get("response_data")
                logger.info(f"💾 Stored webhook response in variable: {response_variable}")
        
        # 4. Evaluate transitions AFTER webhook (for function nodes, use LLM with webhook response)
        if transitions:
            if node_type == "function" and webhook_result:
                # For function nodes, evaluate transitions based on webhook response using LLM
                logger.info(f"🔧 Function node - using LLM-based transition evaluation with webhook response")
                transition_result = await self._evaluate_function_node_transition(
                    transitions, 
                    user_response, 
                    webhook_result
                )
            else:
                # For conversation nodes, use standard transition evaluation
                transition_result = await self._test_transitions(transitions)
            
            result["transition"] = transition_result
            
            # Note if transition changed due to webhook
            if pre_webhook_transition and pre_webhook_transition.get("next_node_id") != transition_result.get("next_node_id"):
                result["transition"]["note"] = "Transition changed after webhook response"
        
        result["success"] = len(result["errors"]) == 0
        result["variables_after"] = self.session_variables.copy()
        
        return result
    
    async def test_node_sequence(
        self,
        node_ids: List[str],
        responses: List[str],
        initial_variables: Optional[Dict] = None
    ) -> Dict:
        """
        Test a sequence of nodes with corresponding responses.
        """
        if len(node_ids) != len(responses):
            return {
                "success": False,
                "error": f"Mismatch: {len(node_ids)} nodes but {len(responses)} responses"
            }
        
        # Initialize
        if initial_variables:
            self.session_variables = initial_variables.copy()
            # Sync customer_name and callerName at initialization
            if "customer_name" in self.session_variables and "callerName" not in self.session_variables:
                self.session_variables["callerName"] = self.session_variables["customer_name"]
            elif "callerName" in self.session_variables and "customer_name" not in self.session_variables:
                self.session_variables["customer_name"] = self.session_variables["callerName"]
        else:
            self.session_variables = {}
        self.conversation_history = []
        
        results = {
            "success": True,
            "initial_variables": self.session_variables.copy(),
            "steps": [],
            "final_variables": {},
            "issues_found": [],
            "summary": {}
        }
        
        for i, (node_id, response) in enumerate(zip(node_ids, responses)):
            step_result = await self.test_single_node(
                node_id=node_id,
                user_response=response,
                initial_variables=None  # Don't reset, carry forward
            )
            
            step_result["step_number"] = i + 1
            results["steps"].append(step_result)
            
            # Collect issues
            results["issues_found"].extend(step_result.get("errors", []))
            results["issues_found"].extend(step_result.get("warnings", []))
            
            if not step_result["success"]:
                results["success"] = False
        
        results["final_variables"] = self.session_variables.copy()
        results["summary"] = {
            "total_steps": len(node_ids),
            "variables_extracted": len([s for s in results["steps"] if (s.get("extraction") or {}).get("extracted")]),
            "webhooks_tested": len([s for s in results["steps"] if s.get("webhook_preview")]),
            "issues_count": len(results["issues_found"])
        }
        
        return results
    
    async def _test_extraction(
        self,
        variables_to_extract: List[Dict],
        user_message: str
    ) -> Dict:
        """
        Test variable extraction using EXACT same logic as calling_service.py
        """
        result = {
            "variables_requested": [v.get("name") for v in variables_to_extract],
            "extracted": {},
            "raw_llm_response": "",
            "calculations_shown": [],
            "extraction_time_ms": 0,
            "errors": []
        }
        
        try:
            # Build the EXACT same prompt as calling_service.py
            existing_vars_str = ""
            if self.session_variables:
                existing_vars_str = "\n\nEXISTING VARIABLES (use these exact values for calculations):\n"
                for k, v in self.session_variables.items():
                    existing_vars_str += f"  {k} = {v}\n"
            
            recent_conversation = ""
            for msg in self.conversation_history[-10:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                recent_conversation += f"{role}: {content}\n"
            
            extraction_prompt = "Extract the following information from the recent conversation:\n\n"
            for var in variables_to_extract:
                var_name = var.get("name", "")
                var_description = var.get("description", "")
                var_hint = var.get("extraction_hint", "")
                if var_name:
                    extraction_prompt += f"- {var_name}: {var_description}\n"
                    if var_hint:
                        extraction_prompt += f"  Hint: {var_hint}\n"
            
            extraction_prompt += existing_vars_str
            extraction_prompt += f"\n\nRecent conversation:\n{recent_conversation}\n"
            extraction_prompt += f"Current user message: {user_message}\n\n"
            extraction_prompt += """IMPORTANT INSTRUCTIONS:
1. Look through the ENTIRE conversation above, not just the current message.
2. If a variable description mentions CALCULATING from other variables (e.g., "convert to monthly", "add X + Y", "divide by 12"), you MUST PERFORM THE MATH:
   - Use the EXISTING VARIABLES values above for calculations
   - Example: if business_income=120000 and side_hustle=24000, then (120000 + 24000) / 12 = 144000 / 12 = 12000
3. For monetary values, extract just the number (e.g., "50000" not "$50,000" or "50k").
4. If someone says "50k" or "fifty thousand", convert to 50000.
5. For monthly conversions: yearly / 12 = monthly. For yearly from monthly: monthly * 12 = yearly.
6. Return numbers as plain integers without commas or currency symbols.
7. DOUBLE-CHECK YOUR ARITHMETIC before returning.

Return ONLY a JSON object with the extracted values. If a value cannot be determined, use null. Format:
"""
            extraction_prompt += "{"
            for i, var in enumerate(variables_to_extract):
                var_name = var.get("name", "")
                if var_name:
                    extraction_prompt += f'"{var_name}": <value>'
                    if i < len(variables_to_extract) - 1:
                        extraction_prompt += ", "
            extraction_prompt += "}"
            
            result["prompt_used"] = extraction_prompt
            result["llm_provider"] = self.llm_provider
            result["llm_model"] = self.llm_model
            
            # Call LLM using the configured provider
            start_time = time.time()
            client = await self._get_llm_client()
            
            if self.llm_provider == "anthropic":
                # Anthropic has different API
                response = await client.messages.create(
                    model=self.llm_model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": extraction_prompt}]
                )
                extraction_response = response.content[0].text.strip()
            else:
                # OpenAI-compatible API (openai, grok, groq)
                response = await client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": extraction_prompt}],
                    temperature=0.0,
                    max_tokens=500
                )
                extraction_response = response.choices[0].message.content.strip()
            
            result["extraction_time_ms"] = int((time.time() - start_time) * 1000)
            result["raw_llm_response"] = extraction_response
            
            # Parse response (same as calling_service.py)
            if extraction_response.startswith("```"):
                extraction_response = extraction_response.split("```")[1]
                if extraction_response.startswith("json"):
                    extraction_response = extraction_response[4:]
            extraction_response = extraction_response.strip()
            
            extracted_vars = json.loads(extraction_response)
            result["extracted"] = extracted_vars or {}
            
            # Store in session variables with sync logic
            if extracted_vars and isinstance(extracted_vars, dict):
                for var_name, var_value in extracted_vars.items():
                    if var_value is not None:
                        self.session_variables[var_name] = var_value
                        
                        # Sync customer_name and callerName
                        if var_name == "customer_name":
                            self.session_variables["callerName"] = var_value
                            result["calculations_shown"].append(f"Synced: callerName = customer_name = {var_value}")
                        elif var_name == "callerName":
                            self.session_variables["customer_name"] = var_value
                            result["calculations_shown"].append(f"Synced: customer_name = callerName = {var_value}")
                
                # Show any calculations that were done
                for var in variables_to_extract:
                    var_name = var.get("name", "")
                    var_desc = var.get("description", "") or ""
                    if any(word in var_desc.lower() for word in ["calculate", "divide", "multiply", "add", "subtract", "/"]):
                        if var_name in extracted_vars:
                            result["calculations_shown"].append(
                                f"{var_name}: {var_desc} → {extracted_vars[var_name]}"
                            )
            
        except json.JSONDecodeError as e:
            result["errors"].append(f"JSON parse error: {e}")
        except Exception as e:
            result["errors"].append(f"Extraction error: {str(e)}")
        
        return result
    
    async def _test_transitions(self, transitions: List[Dict]) -> Dict:
        """
        Test transition conditions using EXACT same logic as calling_service.py
        """
        result = {
            "conditions_evaluated": [],
            "selected_transition": None,
            "next_node_id": None,
            "next_node_label": None,
            "errors": []
        }
        
        for transition in transitions:
            condition = transition.get("condition", "")
            target_node = transition.get("target_node_id") or transition.get("targetNodeId")
            transition_type = transition.get("type", "conditional")
            
            # Get target node label
            target_node_obj = self.get_node(target_node)
            target_node_label = self.get_node_label(target_node_obj) if target_node_obj else target_node
            
            eval_result = {
                "condition": condition,
                "type": transition_type,
                "target_node": target_node,
                "target_node_label": target_node_label,
                "result": None,
                "variables_used": []
            }
            
            # Handle different transition types
            if transition_type == "auto_after_response":
                eval_result["result"] = True
                eval_result["note"] = "Auto-transition after user response"
                result["selected_transition"] = eval_result
                result["next_node_id"] = target_node
                result["next_node_label"] = target_node_label
                result["conditions_evaluated"].append(eval_result)
                break
            
            if not condition or condition.lower() == "default" or condition.lower() == "else":
                eval_result["result"] = "default"
                result["conditions_evaluated"].append(eval_result)
                continue
            
            # Evaluate condition (same logic as calling_service.py)
            try:
                # Replace variables in condition
                eval_condition = condition
                var_pattern = r'\{\{(\w+)\}\}'
                matches = re.findall(var_pattern, condition)
                
                for var_name in matches:
                    var_value = self.session_variables.get(var_name)
                    eval_result["variables_used"].append({
                        "name": var_name,
                        "value": var_value,
                        "found": var_value is not None
                    })
                    
                    if var_value is None:
                        eval_result["result"] = False
                        eval_result["error"] = f"Variable '{var_name}' not found"
                        break
                    
                    # Replace in condition
                    if isinstance(var_value, str):
                        eval_condition = eval_condition.replace(f"{{{{{var_name}}}}}", f'"{var_value}"')
                    else:
                        eval_condition = eval_condition.replace(f"{{{{{var_name}}}}}", str(var_value))
                
                if eval_result.get("error"):
                    result["conditions_evaluated"].append(eval_result)
                    continue
                
                eval_result["condition_after_substitution"] = eval_condition
                
                # Safe eval
                eval_result["result"] = self._safe_eval_condition(eval_condition)
                
                if eval_result["result"] == True:
                    result["selected_transition"] = eval_result
                    result["next_node_id"] = target_node
                    result["next_node_label"] = target_node_label
                    result["conditions_evaluated"].append(eval_result)
                    break
                    
            except Exception as e:
                eval_result["error"] = str(e)
                eval_result["result"] = False
            
            result["conditions_evaluated"].append(eval_result)
        
        # If no condition matched, use default
        if not result["selected_transition"]:
            for eval_res in result["conditions_evaluated"]:
                if eval_res["result"] == "default":
                    result["selected_transition"] = eval_res
                    result["next_node_id"] = eval_res["target_node"]
                    result["next_node_label"] = eval_res.get("target_node_label", eval_res["target_node"])
                    break
        
        return result
    
    def _safe_eval_condition(self, condition: str) -> bool:
        """Safely evaluate a condition string"""
        # Clean up the condition
        condition = condition.strip()
        
        # Handle common operators
        allowed_names = {
            "True": True,
            "False": False,
            "true": True,
            "false": False,
            "None": None,
            "null": None
        }
        
        try:
            # Use eval with restricted globals
            return eval(condition, {"__builtins__": {}}, allowed_names)
        except:
            # Try simple comparisons
            if ">=" in condition:
                parts = condition.split(">=")
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) >= float(parts[1].strip())
                    except:
                        pass
            elif "<=" in condition:
                parts = condition.split("<=")
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) <= float(parts[1].strip())
                    except:
                        pass
            elif ">" in condition:
                parts = condition.split(">")
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) > float(parts[1].strip())
                    except:
                        pass
            elif "<" in condition:
                parts = condition.split("<")
                if len(parts) == 2:
                    try:
                        return float(parts[0].strip()) < float(parts[1].strip())
                    except:
                        pass
            elif "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    left = parts[0].strip().strip('"\'')
                    right = parts[1].strip().strip('"\'')
                    return left == right
            elif "!=" in condition:
                parts = condition.split("!=")
                if len(parts) == 2:
                    left = parts[0].strip().strip('"\'')
                    right = parts[1].strip().strip('"\'')
                    return left != right
            
            return False
    
    def _build_webhook_from_function_node(self, data: Dict) -> Dict:
        """
        Build webhook config from function node data format.
        Function nodes store webhook config at the data level (webhook_url, webhook_body, etc.)
        instead of nested webhook object.
        """
        webhook_body_template = data.get("webhook_body", "")
        
        # Parse the webhook_body JSON schema to build body_schema
        body_schema = []
        if webhook_body_template:
            try:
                # The webhook_body is a JSON Schema definition
                schema = json.loads(webhook_body_template)
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                
                for prop_name, prop_def in properties.items():
                    body_schema.append({
                        "name": prop_name,
                        "source": "variable",  # All are from session variables
                        "variable": prop_name,  # Use same name as the property
                        "required": prop_name in required,
                        "description": prop_def.get("description", "")
                    })
            except json.JSONDecodeError:
                logger.warning(f"Could not parse webhook_body as JSON: {webhook_body_template[:100]}...")
        
        return {
            "url": data.get("webhook_url", ""),
            "method": data.get("webhook_method", "POST"),
            "headers": data.get("webhook_headers", {}),
            "body_schema": body_schema,
            "timeout": data.get("webhook_timeout", 30),
            "response_variable": data.get("response_variable", "webhook_response")
        }
    
    async def _evaluate_function_node_transition(
        self, 
        transitions: List[Dict], 
        user_message: str,
        webhook_result: Dict
    ) -> Dict:
        """
        Evaluate transitions for function nodes using LLM.
        Function node transitions are based on webhook response, not user message.
        This mirrors the logic in calling_service._follow_transition for function nodes.
        """
        result = {
            "conditions_evaluated": [],
            "selected_transition": None,
            "next_node_id": None,
            "next_node_label": None,
            "evaluation_method": "llm_webhook_based",
            "webhook_response_used": True,
            "errors": []
        }
        
        if not transitions:
            result["errors"].append("No transitions defined")
            return result
        
        # Build transition options for LLM evaluation
        transition_options = []
        for i, trans in enumerate(transitions):
            condition = trans.get("condition", "")
            next_node_id = trans.get("nextNode") or trans.get("target_node_id") or trans.get("targetNodeId")
            
            if condition and next_node_id:
                # Get target node label
                target_node_obj = self.get_node(next_node_id)
                target_node_label = self.get_node_label(target_node_obj) if target_node_obj else next_node_id
                
                transition_options.append({
                    "index": i,
                    "condition": condition,
                    "next_node_id": next_node_id,
                    "next_node_label": target_node_label
                })
        
        if not transition_options:
            result["errors"].append("No valid transition conditions found")
            return result
        
        # Build evaluation prompt - EXACTLY like calling_service.py does for function nodes
        options_text = ""
        for i, opt in enumerate(transition_options):
            options_text += f"\nOption {i}:\n"
            options_text += f"  Condition: {opt['condition']}\n"
        
        # Get conversation context
        full_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.conversation_history[-10:]
        ])
        
        # Format webhook response for the prompt
        webhook_data = webhook_result.get("response_data") or webhook_result
        webhook_context = f"""
WEBHOOK RESPONSE (CRITICAL - base your decision primarily on this):
{json.dumps(webhook_data, indent=2, default=str)}

This is a WEBHOOK/FUNCTION node. The transitions should be evaluated based on the WEBHOOK RESPONSE above, NOT the user's message.
- If the webhook response indicates success/booking/completion → choose the positive transition
- If the webhook response indicates failure/unavailability/error → choose the negative transition
- Look for keys like "status", "success", "booked", "available", "message" in the response
"""
        
        eval_prompt = f"""You are analyzing a webhook response to determine which transition path to take.

CONVERSATION HISTORY (for context only):
{full_context}

{webhook_context}

TRANSITION OPTIONS:
{options_text}

Your task:
1. Carefully analyze the WEBHOOK RESPONSE above
2. Match the webhook result to the appropriate transition condition
3. For booking/scheduling webhooks:
   - If the response shows appointment was "booked", "confirmed", "scheduled", or "success" → choose the positive/booked transition
   - If the response shows "unavailable", "full", "failed", "error", or offers alternative times → choose the negative/unavailable transition
4. Look at ALL fields in the webhook response: status, message, success, booked, available, etc.

CRITICAL: Your decision should be based on the WEBHOOK RESPONSE, not what the user said.

Respond with ONLY the number (0, 1, 2, etc.) of the BEST matching transition.
If absolutely none match, respond with "-1".

Your response (just the number):"""
        
        result["prompt_used"] = eval_prompt
        result["webhook_data_evaluated"] = webhook_data
        
        try:
            client = await self._get_llm_client()
            
            if self.llm_provider == "anthropic":
                response = await client.messages.create(
                    model=self.llm_model,
                    max_tokens=10,
                    messages=[
                        {"role": "user", "content": eval_prompt}
                    ]
                )
                ai_response = response.content[0].text.strip()
            else:
                response = await client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing webhook responses and determining which transition path to take based on the response data."},
                        {"role": "user", "content": eval_prompt}
                    ],
                    temperature=0,
                    max_tokens=10,
                    stream=False
                )
                ai_response = response.choices[0].message.content.strip()
            
            result["llm_response"] = ai_response
            logger.info(f"🤖 LLM transition decision for function node: '{ai_response}'")
            
            try:
                selected_index = int(ai_response)
                
                if selected_index >= 0 and selected_index < len(transition_options):
                    selected = transition_options[selected_index]
                    result["selected_transition"] = {
                        "condition": selected["condition"],
                        "index": selected_index,
                        "result": True
                    }
                    result["next_node_id"] = selected["next_node_id"]
                    result["next_node_label"] = selected["next_node_label"]
                    logger.info(f"✅ Selected transition {selected_index}: {selected['condition'][:50]}... -> {selected['next_node_label']}")
                elif selected_index == -1:
                    result["errors"].append("LLM could not match any transition condition to webhook response")
                else:
                    result["errors"].append(f"Invalid transition index: {selected_index}")
                
            except ValueError:
                result["errors"].append(f"Could not parse LLM response as number: {ai_response}")
            
            # Record all conditions evaluated
            for opt in transition_options:
                result["conditions_evaluated"].append({
                    "condition": opt["condition"],
                    "target_node": opt["next_node_id"],
                    "target_node_label": opt["next_node_label"],
                    "selected": opt["index"] == selected_index if 'selected_index' in dir() else False
                })
                
        except Exception as e:
            result["errors"].append(f"LLM evaluation error: {str(e)}")
            logger.error(f"Error evaluating function node transition: {e}")
        
        return result

    def _build_webhook_payload(self, webhook: Dict) -> Dict:
        """
        Build webhook payload using EXACT same logic as calling_service.py
        """
        result = {
            "url": webhook.get("url", ""),
            "method": webhook.get("method", "POST"),
            "headers": webhook.get("headers", {}),
            "body": {},
            "missing_variables": [],
            "variable_values": {}
        }
        
        body_schema = webhook.get("body_schema", [])
        
        for field in body_schema:
            field_name = field.get("name", "")
            source = field.get("source", "variable")
            
            if source == "variable":
                var_name = field.get("variable", field_name)
                var_value = self.session_variables.get(var_name)
                
                result["variable_values"][field_name] = {
                    "source_variable": var_name,
                    "value": var_value,
                    "found": var_value is not None
                }
                
                if var_value is not None:
                    result["body"][field_name] = var_value
                else:
                    result["body"][field_name] = None
                    result["missing_variables"].append({
                        "field": field_name,
                        "expected_variable": var_name
                    })
            
            elif source == "static":
                result["body"][field_name] = field.get("value", "")
            
            elif source == "conversation":
                # Build conversation string
                conv_text = "\n".join([
                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                    for msg in self.conversation_history[-10:]
                ])
                result["body"][field_name] = conv_text
        
        return result
    
    async def _execute_webhook(self, webhook: Dict) -> Dict:
        """
        Actually execute the webhook and return the response.
        This mimics what happens during a live call.
        """
        # Build payload
        payload_info = self._build_webhook_payload(webhook)
        
        result = {
            "payload_sent": payload_info["body"],
            "url": payload_info["url"],
            "method": payload_info["method"],
            "missing_variables": payload_info["missing_variables"],
            "variable_values": payload_info["variable_values"],
            "response": None,
            "response_status": None,
            "response_data": None,
            "error": None,
            "executed": False
        }
        
        url = payload_info["url"]
        if not url:
            result["error"] = "No webhook URL configured"
            return result
        
        # Replace any remaining {{variables}} in URL
        for var_name, var_value in self.session_variables.items():
            if var_value is not None:
                url = url.replace(f"{{{{{var_name}}}}}", str(var_value))
        
        result["url"] = url
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                method = payload_info["method"].upper()
                headers = {"Content-Type": "application/json"}
                headers.update(payload_info.get("headers", {}))
                
                # Replace variables in headers too
                for key, val in headers.items():
                    if isinstance(val, str):
                        for var_name, var_value in self.session_variables.items():
                            if var_value is not None:
                                headers[key] = headers[key].replace(f"{{{{{var_name}}}}}", str(var_value))
                
                if method == "GET":
                    async with session.get(url, headers=headers) as resp:
                        result["response_status"] = resp.status
                        result["response"] = await resp.text()
                        result["executed"] = True
                else:
                    async with session.post(url, json=payload_info["body"], headers=headers) as resp:
                        result["response_status"] = resp.status
                        result["response"] = await resp.text()
                        result["executed"] = True
                
                # Try to parse as JSON
                try:
                    result["response_data"] = json.loads(result["response"])
                except:
                    result["response_data"] = result["response"]
                
                # Extract any variables from response if configured
                webhook_response_vars = webhook.get("response_variables", [])
                if webhook_response_vars and isinstance(result["response_data"], dict):
                    for var_config in webhook_response_vars:
                        var_name = var_config.get("name")
                        json_path = var_config.get("path", var_name)
                        if var_name and json_path:
                            # Simple path extraction (supports dot notation)
                            value = result["response_data"]
                            for key in json_path.split("."):
                                if isinstance(value, dict):
                                    value = value.get(key)
                                else:
                                    value = None
                                    break
                            if value is not None:
                                self.session_variables[var_name] = value
                                logger.info(f"Extracted '{var_name}' = '{value}' from webhook response")
                
        except asyncio.TimeoutError:
            result["error"] = "Webhook timed out after 30 seconds"
        except Exception as e:
            result["error"] = f"Webhook error: {str(e)}"
        
        return result
    
    def _check_name_sync(self, extraction_result: Dict, node_result: Dict):
        """Check if customer_name and callerName are properly synced"""
        if not extraction_result:
            return
            
        extracted = extraction_result.get("extracted", {}) or {}
        
        customer_name = self.session_variables.get("customer_name")
        caller_name = self.session_variables.get("callerName")
        
        if customer_name and not caller_name:
            node_result["warnings"].append(
                f"⚠️ customer_name='{customer_name}' but callerName is not set"
            )
        elif caller_name and not customer_name:
            node_result["warnings"].append(
                f"⚠️ callerName='{caller_name}' but customer_name is not set"
            )
        elif customer_name != caller_name:
            node_result["warnings"].append(
                f"⚠️ Name mismatch: customer_name='{customer_name}' vs callerName='{caller_name}'"
            )
    
    def _check_webhook_variables(self, webhook_result: Dict, node_result: Dict):
        """Check for common webhook variable issues"""
        body = webhook_result.get("body", {})
        missing = webhook_result.get("missing_variables", [])
        
        # Check for case sensitivity issues
        for field_info in missing:
            expected_var = field_info.get("expected_variable", "")
            
            # Check if there's a case-insensitive match
            for var_name in self.session_variables.keys():
                if var_name.lower() == expected_var.lower() and var_name != expected_var:
                    node_result["warnings"].append(
                        f"⚠️ Case mismatch: webhook expects '{expected_var}' but found '{var_name}'"
                    )
        
        # Check callerName/customer_name specifically
        if "callerName" in body and body["callerName"] is None:
            if self.session_variables.get("customer_name"):
                node_result["errors"].append(
                    f"❌ callerName is null but customer_name='{self.session_variables['customer_name']}' exists - sync failed!"
                )


async def run_node_test(
    agent_config: Dict,
    node_ids: List[str],
    responses: List[str],
    initial_variables: Optional[Dict] = None
) -> Dict:
    """
    Convenience function to run a node sequence test.
    """
    tester = NodeTester(agent_config)
    
    if len(node_ids) == 1:
        return await tester.test_single_node(
            node_id=node_ids[0],
            user_response=responses[0],
            initial_variables=initial_variables
        )
    else:
        return await tester.test_node_sequence(
            node_ids=node_ids,
            responses=responses,
            initial_variables=initial_variables
        )
