"""
Parallel LLM Team Architecture - "Swarm Intelligence" Approach
Implements 5 specialist LLMs working in parallel + 1 master synthesizer
"""
import asyncio
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class ParallelLLMTeam:
    """Manages a team of specialist LLMs working in parallel"""
    
    def __init__(self, session):
        """
        Initialize the parallel team with a CallSession
        
        Args:
            session: CallSession instance with agent config, history, etc.
        """
        self.session = session
        self.grok_client = None
        self.gpt_client = None
        
    async def _ensure_clients(self):
        """Ensure LLM clients are initialized"""
        if not self.grok_client:
            import openai
            # Get Grok API key from session
            try:
                grok_key = await self.session.get_api_key("grok")
            except ValueError as e:
                logger.error(f"Failed to get Grok API key: {e}")
                return None
            
            # Create OpenAI client with xAI base URL for Grok
            self.grok_client = openai.AsyncOpenAI(
                api_key=grok_key,
                base_url="https://api.x.ai/v1"
            )
    
    async def _call_llm(self, messages: List[Dict], model: str = "grok-4-fast-non-reasoning", 
                       temperature: float = 0.3, max_tokens: int = 200) -> str:
        """Helper to call LLM and get response"""
        try:
            await self._ensure_clients()
            
            if not self.grok_client:
                logger.error("Grok client not initialized")
                return ""
            
            # Direct API call using OpenAI library
            response = await self.grok_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            
            logger.error("Invalid LLM response format")
            return ""
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    # ==================== SPECIALIST 1: Intent Classifier ====================
    async def intent_classifier(self, user_message: str, preprocessing_hint: str = "") -> str:
        """Ultra-fast intent classification"""
        start = time.time()
        
        prompt = f"""Intent? "{user_message}"
trust|price|time|question|ready"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self._call_llm(messages, temperature=0, max_tokens=3)
        
        elapsed = int((time.time() - start) * 1000)
        
        # Map to full intent names
        if "trust" in result.lower() or "scam" in result.lower():
            logger.info(f"🎯 Intent: trust_objection ({elapsed}ms)")
            return "trust_objection"
        elif "price" in result.lower() or "cost" in result.lower():
            return "price_objection"
        elif "time" in result.lower() or "busy" in result.lower():
            return "time_objection"
        elif "ready" in result.lower() or "yes" in result.lower():
            return "ready_to_proceed"
        else:
            logger.info(f"🎯 Intent: general_question ({elapsed}ms)")
            return "general_question"
    
    # ==================== SPECIALIST 2: DISC Analyzer ====================
    async def disc_analyzer(self, user_message: str, history: List[Dict]) -> str:
        """Ultra-fast DISC detection"""
        start = time.time()
        
        prompt = f"""DISC? "{user_message}"
D|I|S|C"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self._call_llm(messages, temperature=0, max_tokens=2)
        
        elapsed = int((time.time() - start) * 1000)
        
        # Extract letter
        if result and len(result) > 0:
            letter = result[0].upper()
            if letter in ['D', 'I', 'S', 'C']:
                logger.info(f"🧠 DISC: {letter} ({elapsed}ms)")
                return letter
        
        logger.info(f"🧠 DISC: C (default, {elapsed}ms)")
        return "C"
    
    # ==================== SPECIALIST 3: KB Searcher ====================
    async def kb_searcher(self, user_message: str, intent: str) -> List[str]:
        """
        Knowledge base retrieval
        Returns: List of relevant proof points/information
        """
        try:
            # Use existing RAG service if available
            from rag_service import retrieve_relevant_chunks
            
            kb_name = self.session.agent_config.get('knowledge_base', '')
            if not kb_name or retrieve_relevant_chunks is None:
                logger.info("📚 KB Searcher: No KB configured, returning empty")
                return []
            
            # Search KB based on intent + message
            search_query = f"{intent}: {user_message}"
            
            chunks = await retrieve_relevant_chunks(
                kb_name=kb_name,
                query=search_query,
                top_k=2,
                db=self.session.db
            )
            
            results = []
            for chunk in chunks:
                content = chunk.get('content', '')
                if content and len(content) > 0:
                    # Truncate to first 150 chars for concise proof points
                    results.append(content[:150] + "..." if len(content) > 150 else content)
            
            logger.info(f"📚 KB Searcher: Found {len(results)} proof points")
            return results
            
        except Exception as e:
            logger.error(f"Error in KB searcher: {e}")
            return []
    
    # ==================== SPECIALIST 4: Objection Handler ====================
    async def objection_handler(self, intent: str, disc: str, preprocessing_hint: str = "") -> str:
        """Ultra-fast tactic selection"""
        start = time.time()
        
        prompt = f"""Tactic? {intent}/{disc}
evidence|social|authority|defer"""
        
        messages = [{"role": "user", "content": prompt}]
        result = await self._call_llm(messages, temperature=0, max_tokens=3)
        
        elapsed = int((time.time() - start) * 1000)
        
        # Map short result to tactic
        tactic = result.lower()
        if "evidence" in tactic:
            tactic = "evidence"
        elif "social" in tactic:
            tactic = "social-proof"
        elif "authority" in tactic:
            tactic = "authority"
        elif "defer" in tactic:
            tactic = "defer"
        else:
            tactic = "evidence"
        
        logger.info(f"🎭 Tactic: {tactic} ({elapsed}ms)")
        return tactic
    
    # ==================== SPECIALIST 5: Transition Evaluator ====================
    async def transition_evaluator(self, user_message: str, current_node: Dict, 
                                   intent: str, variables: Dict) -> str:
        """
        Use the ACTUAL transition logic from calling_service.py
        Returns: Node ID to transition to (or "LOOP" to stay)
        """
        start = time.time()
        
        transitions = current_node.get('data', {}).get('transitions', [])
        
        if not transitions:
            logger.info("🔀 Transition: No transitions, LOOP")
            return "LOOP"
        
        # 🚀 OPTIMIZATION: Cache common affirmative/negative responses (like calling_service does)
        user_message_lower = user_message.lower().strip()
        common_affirmatives = ["yeah", "yes", "yep", "sure", "okay", "ok", "yea", "ya", "uh huh", "absolutely", "definitely", "sounds good"]
        common_negatives = ["no", "nope", "nah", "not interested", "don't want", "no thanks"]
        
        starts_with_affirmative = any(user_message_lower.startswith(aff) for aff in common_affirmatives)
        starts_with_negative = any(user_message_lower.startswith(neg) for neg in common_negatives)
        
        if user_message_lower in common_affirmatives or starts_with_affirmative:
            # Take first transition (usually the positive/yes path)
            if transitions:
                first_trans = transitions[0]
                target = first_trans.get("nextNode") or first_trans.get("target", "LOOP")
                elapsed = int((time.time() - start) * 1000)
                logger.info(f"🔀 Transition: {target} (cached affirmative, {elapsed}ms)")
                return target
        
        elif user_message_lower in common_negatives or starts_with_negative:
            # Look for negative/objection transition
            for trans in transitions:
                condition = trans.get("condition", "").lower()
                if "no" in condition or "not interested" in condition or "objection" in condition:
                    target = trans.get("nextNode") or trans.get("target", "LOOP")
                    elapsed = int((time.time() - start) * 1000)
                    logger.info(f"🔀 Transition: {target} (cached negative, {elapsed}ms)")
                    return target
            # No explicit negative path, stay on current node
            logger.info("🔀 Transition: LOOP (no negative path)")
            return "LOOP"
        
        # Build valid transition options (check variables like calling_service does)
        valid_transitions = []
        for trans in transitions:
            check_vars = trans.get('check_variables', [])
            
            # If transition requires variables, check if they're present
            if check_vars:
                all_present = all(variables.get(var) is not None for var in check_vars)
                if not all_present:
                    continue  # Skip this transition
            
            # This transition is valid
            valid_transitions.append(trans)
        
        if not valid_transitions:
            logger.info("🔀 Transition: No valid transitions (vars missing), LOOP")
            return "LOOP"
        
        # If only 1 valid transition, take it immediately (like calling_service does)
        if len(valid_transitions) == 1:
            target = valid_transitions[0].get('nextNode') or valid_transitions[0].get('target', 'LOOP')
            elapsed = int((time.time() - start) * 1000)
            logger.info(f"🔀 Transition: {target} (only option, {elapsed}ms)")
            return target
        
        # Multiple transitions - DECOMPOSE: Check each transition individually
        # Instead of asking "which one?", ask "does this match?" for EACH transition
        # This breaks down the complex task into simple binary decisions
        
        # Build conversation context
        full_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.session.conversation_history[-5:]
        ])
        
        # Check each transition individually with simple YES/NO questions
        for i, trans in enumerate(valid_transitions):
            condition = trans.get('condition', '')
            
            # Ultra-simple binary question for THIS specific transition
            simple_prompt = f"""Recent conversation:
{full_context}
User just said: "{user_message}"

Does this match: "{condition}"?

Answer YES or NO:"""
            
            messages = [{"role": "user", "content": simple_prompt}]
            result = await self._call_llm(messages, temperature=0, max_tokens=5)
            
            # If YES, take this transition immediately
            if "YES" in result.upper():
                target = trans.get('nextNode') or trans.get('target', 'LOOP')
                elapsed = int((time.time() - start) * 1000)
                logger.info(f"🔀 Transition: {target} (matched condition {i}, {elapsed}ms)")
                return target
        
        # None of the transitions matched, stay on current node
        elapsed = int((time.time() - start) * 1000)
        logger.info(f"🔀 Transition: LOOP (no conditions matched, {elapsed}ms)")
        return "LOOP"
    
    # ==================== MASTER SYNTHESIZER ====================
    async def master_synthesizer(self, user_message: str, team_results: Dict, 
                                 current_node: Dict) -> str:
        """
        Return the node's script/content directly (like regular approach does)
        Specialists provide context but response is the node's actual script
        """
        # Specialists provide context but we use node script directly
        # intent = team_results.get('intent', 'general_question')
        # disc = team_results.get('disc', 'C')
        # kb_results = team_results.get('kb_results', [])
        # tactic = team_results.get('tactic', 'defer')
        
        # Get the node's script/content - THIS IS WHAT WE SHOULD SAY
        node_data = current_node.get('data', {})
        node_content = node_data.get('content', '') or node_data.get('script', '')
        
        if not node_content:
            logger.warning("No node content found, generating generic response")
            return "Could you tell me more?"
        
        # CRITICAL FIX: Just return the node's script directly
        # The regular approach uses the node script as-is, so we should too
        # This ensures 100% identical responses and conversation context
        
        # Simple placeholder replacement if needed
        response = node_content
        
        # Replace common placeholders
        response = response.replace('{{customer_name}}', self.session.session_variables.get('customer_name', '[name]'))
        
        # If node content is very long (>500 chars), it's probably instructions not a script
        # In that case, extract just the core script part
        if len(node_content) > 500:
            # Look for script markers or just take first sentence
            lines = node_content.split('\n')
            for line in lines:
                if len(line) > 20 and not line.startswith('#') and not line.startswith('-'):
                    response = line.strip()
                    break
        
        logger.info("✨ Master Synthesizer: Using node script directly")
        return response
    
    # ==================== MAIN PARALLEL PROCESSING ====================
    async def process_parallel(self, user_message: str, current_node: Dict) -> Dict:
        """
        Run all specialists in parallel, then synthesize
        
        Returns:
            Dict with keys: response, next_node, latency_breakdown
        """
        start_time = time.time()
        
        # Get preprocessing context if available
        preprocessing_hint = ""
        if hasattr(self.session, 'preprocessing_context'):
            preprocessing_hint = self.session.preprocessing_context
        
        logger.info(f"🚀 Starting Parallel LLM Team for: {user_message[:50]}...")
        
        # PHASE 1: Run 5 specialists in PARALLEL
        parallel_start = time.time()
        
        logger.info("🚀 Launching 5 specialists in parallel...")
        
        try:
            # Create all tasks upfront
            task1 = self.intent_classifier(user_message, preprocessing_hint)
            task2 = self.disc_analyzer(user_message, self.session.conversation_history)
            task3 = self.kb_searcher(user_message, preprocessing_hint)
            task4 = self.objection_handler("", "", preprocessing_hint)
            task5 = self.transition_evaluator(user_message, current_node, "", self.session.session_variables)
            
            # Execute all in parallel
            t1 = time.time()
            results = await asyncio.gather(
                task1, task2, task3, task4, task5,
                return_exceptions=True
            )
            gather_time = int((time.time() - t1) * 1000)
            
            logger.info(f"✅ All 5 specialists completed in {gather_time}ms")
            
            # Unpack results
            intent = results[0] if not isinstance(results[0], Exception) else "general_question"
            disc = results[1] if not isinstance(results[1], Exception) else "C"
            kb_results = results[2] if not isinstance(results[2], Exception) else []
            # tactic_temp = results[3] if not isinstance(results[3], Exception) else "defer"
            next_node_raw = results[4]
            
            if isinstance(next_node_raw, Exception):
                logger.error(f"Transition evaluator error: {next_node_raw}")
                next_node = "LOOP"
            else:
                next_node = next_node_raw if next_node_raw else "LOOP"
                logger.info(f"🔀 Transition result: '{next_node}'")
            
            # Re-run objection handler with intent now available
            tactic = await self.objection_handler(intent, disc, preprocessing_hint)
            
            parallel_time = int((time.time() - parallel_start) * 1000)
            
            logger.info(f"⏱️ Parallel specialists completed in {parallel_time}ms")
            
        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            # Fallback values
            intent = "general_question"
            disc = "C - Analytical"
            kb_results = []
            tactic = "defer-to-call"
            next_node = "LOOP"
            parallel_time = 0
        
        # PHASE 2: Master Synthesizer
        synthesis_start = time.time()
        
        team_results = {
            'intent': intent,
            'disc': disc,
            'kb_results': kb_results,
            'tactic': tactic,
            'next_node': next_node
        }
        
        response = await self.master_synthesizer(user_message, team_results, current_node)
        
        synthesis_time = int((time.time() - synthesis_start) * 1000)
        
        total_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"⏱️ Master synthesis completed in {synthesis_time}ms")
        logger.info(f"⏱️ Total parallel team time: {total_time}ms")
        
        return {
            'response': response,
            'next_node': next_node,
            'team_results': team_results,
            'latency_breakdown': {
                'parallel_specialists_ms': parallel_time,
                'master_synthesis_ms': synthesis_time,
                'total_ms': total_time
            }
        }
