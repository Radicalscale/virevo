"""
Director Service - Real Implementation
Integrated with MongoDB tenant keys and live API calls (GPT-4o, Grok 4)
Sandboxes are persisted to MongoDB for stateless operation.
"""
import os
import copy
import uuid
import asyncio
import json
import httpx
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient


class DirectorService:
    """
    The DirectorService orchestrates the 'Director Studio' functionality.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.openai_api_key: Optional[str] = None
        self.grok_api_key: Optional[str] = None
        self.elevenlabs_api_key: Optional[str] = None
        self.db = None
        
    async def _init_db(self):
        """Initialize MongoDB connection and load API keys for this tenant."""
        if self.db is not None:
            return
            
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        self.db = client['test_database']
        
        # Load tenant's API keys from the api_keys collection
        keys = await self.db.api_keys.find({"user_id": self.user_id}).to_list(length=50)
        
        for key_doc in keys:
            service_name = key_doc.get('service_name', '').lower()
            if not key_doc.get('is_active', False):
                continue
                
            if service_name == 'grok' or service_name == 'xai':
                self.grok_api_key = key_doc.get('api_key')
                print(f"[Director] ✅ Grok/xAI API key loaded")
            elif service_name == 'openai':
                self.openai_api_key = key_doc.get('api_key')
                print(f"[Director] ✅ OpenAI API key loaded")
            elif service_name == 'elevenlabs':
                self.elevenlabs_api_key = key_doc.get('api_key')
                print(f"[Director] ✅ ElevenLabs API key loaded")
        
        # Fallback to environment variables if not in DB
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not self.grok_api_key:
            self.grok_api_key = os.environ.get('GROK_API_KEY') or os.environ.get('XAI_API_KEY')
        if not self.elevenlabs_api_key:
            self.elevenlabs_api_key = os.environ.get('ELEVEN_API_KEY')

    async def create_sandbox(self, agent_id: str) -> str:
        """
        Creates a safe clone of an agent for testing.
        Stores the sandbox in MongoDB for persistence.
        """
        await self._init_db()
        
        # Load real agent from database
        original_agent = await self.db.agents.find_one({"id": agent_id, "user_id": self.user_id})
        if not original_agent:
            raise ValueError(f"Agent {agent_id} not found for this user")
        
        # Remove MongoDB _id before cloning
        original_agent.pop('_id', None)
        
        sandbox_id = f"sandbox_{agent_id}_{str(uuid.uuid4())[:8]}"
        
        # Store sandbox in MongoDB (director_sandboxes collection)
        sandbox_doc = {
            "sandbox_id": sandbox_id,
            "user_id": self.user_id,
            "agent_id": agent_id,
            "config": copy.deepcopy(original_agent),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await self.db.director_sandboxes.insert_one(sandbox_doc)
        
        print(f"[Director] Created Sandbox {sandbox_id} from Agent {agent_id}")
        return sandbox_id

    async def get_sandbox_config(self, sandbox_id: str) -> Optional[Dict]:
        """Load sandbox from MongoDB."""
        await self._init_db()
        sandbox = await self.db.director_sandboxes.find_one({
            "sandbox_id": sandbox_id,
            "user_id": self.user_id
        })
        if sandbox:
            return sandbox.get('config')
        return None

    async def _save_sandbox_config(self, sandbox_id: str, config: Dict):
        """Save updated sandbox config to MongoDB."""
        await self._init_db()
        await self.db.director_sandboxes.update_one(
            {"sandbox_id": sandbox_id, "user_id": self.user_id},
            {"$set": {"config": config, "updated_at": datetime.utcnow()}}
        )

    async def update_sandbox_node(self, sandbox_id: str, node_id: str, updates: Dict):
        """Manually update a node in the sandbox."""
        await self._init_db()
        
        config = await self.get_sandbox_config(sandbox_id)
        if not config:
            raise ValueError("Sandbox not found")
        
        call_flow = config.get('call_flow', [])
        node_id_str = str(node_id)
        
        for node in call_flow:
            if str(node.get('id')) == node_id_str:
                node['data'] = {**node.get('data', {}), **updates}
                print(f"[Director] Updated Node {node_id} in {sandbox_id}")
                await self._save_sandbox_config(sandbox_id, config)
                return
        
        raise ValueError(f"Node {node_id} not found in sandbox")

    async def evolve_node(self, sandbox_id: str, node_id: str, generations: int = 3):
        """
        Starts the Evolutionary Optimization loop for a specific node.
        Returns FULL data including all variants, audio, and scores.
        """
        await self._init_db()
        
        print(f"[Director] Starting Evolution for {node_id} in {sandbox_id} ({generations} gens)")
        
        evolution_log = []  # Full history for UI
        
        try:
            config = await self.get_sandbox_config(sandbox_id)
            if not config:
                raise ValueError("Sandbox not found")
            
            call_flow = config.get('call_flow', [])
            node_id_str = str(node_id)
            
            # Get agent settings for voice
            agent_settings = config.get('settings', {})
            elevenlabs_settings = agent_settings.get('elevenlabs_settings', {})
            voice_id = elevenlabs_settings.get('voice_id', '21m00Tcm4TlvDq8ikWAM')
            
            # Find the target node
            target_node = None
            for node in call_flow:
                if str(node.get('id')) == node_id_str:
                    target_node = node
                    break
            
            if not target_node:
                print(f"[Director] ❌ Node {node_id} not found. Available: {[n.get('id') for n in call_flow[:5]]}")
                raise ValueError(f"Node {node_id} not found in call flow")
            
            node_data = target_node.get('data', {})
            node_label = target_node.get('label') or node_data.get('label') or node_id
            print(f"[Director] Evolving node: {node_label}")
            
            # 1. Generate Chaos Scenario using Grok
            scenario = await self._call_grok_for_scenario(node_data)
            print(f"[Director] Scenario: {scenario[:80]}...")
            
            best_score = 0
            best_variant = node_data
            best_variant_data = None
            
            for gen in range(generations):
                print(f"--- Generation {gen + 1} ---")
                generation_results = []
                
                # 2. Mutation Phase
                variants = await self._generate_mutations(node_data)
                
                # 3. Battle Royale (Test each variant with REAL audio)
                for i, variant in enumerate(variants):
                    try:
                        audio_bytes, text_output, latency = await self._run_streaming_test(variant, scenario, voice_id)
                        score = await self._call_openai_judge(audio_bytes, text_output, latency, scenario)
                        
                        # Encode audio to base64 for frontend
                        import base64
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else None
                        
                        variant_result = {
                            "variant_type": variant.get('_variant_type', 'Unknown'),
                            "content": variant.get('content', ''),
                            "voice_settings": variant.get('voice_settings', {}),
                            "audio_base64": audio_base64,
                            "latency_ms": int(latency * 1000),
                            "score": score
                        }
                        generation_results.append(variant_result)
                        print(f"[Director] Variant {i+1} ({variant.get('_variant_type')}): Score {score.get('total', 0)}")
                        
                    except Exception as var_err:
                        print(f"[Director] Variant {i+1} error: {var_err}")
                        generation_results.append({
                            "variant_type": variant.get('_variant_type', 'Unknown'),
                            "content": variant.get('content', ''),
                            "voice_settings": variant.get('voice_settings', {}),
                            "error": str(var_err),
                            "score": {"total": 0}
                        })
                
                evolution_log.append({
                    "generation": gen + 1,
                    "variants": generation_results
                })
                
                # 4. Selection
                if generation_results:
                    winner = max(generation_results, key=lambda x: x["score"].get("total", 0))
                    winner_score = winner["score"].get("total", 0)
                    print(f"[Director] Generation {gen+1} Winner: {winner['variant_type']} Score {winner_score}")
                    
                    if winner_score > best_score:
                        best_score = winner_score
                        best_variant_data = winner
                        # Find the actual variant dict to save
                        for v in variants:
                            if v.get('_variant_type') == winner['variant_type']:
                                best_variant = v
                                break
            
            # Apply winner to sandbox
            for node in call_flow:
                if str(node.get('id')) == node_id_str:
                    node['data'] = best_variant
                    break
            
            config['call_flow'] = call_flow
            await self._save_sandbox_config(sandbox_id, config)
            
            print(f"[Director] ✅ Evolution complete for {node_label}. Best score: {best_score}")
            
            return {
                "node_id": node_id,
                "node_label": node_label,
                "scenario": scenario,
                "generations": evolution_log,
                "best_variant": best_variant_data,
                "best_score": best_score
            }
            
        except Exception as e:
            print(f"[Director] ❌ Evolution error: {e}")
            print(traceback.format_exc())
            raise

    async def _call_grok_for_scenario(self, node_context: Dict) -> str:
        """Use Grok 4 to generate a chaos scenario."""
        if not self.grok_api_key:
            print("[Director] ⚠️ No Grok API key, using fallback scenario")
            return "User is skeptical and asking tough questions about the offer."
        
        system_prompt = """You are a chaos engineer for AI voice agents.
Generate a single difficult, edge-case user persona for testing.
Be creative: interruptions, mumbling, anger, sarcasm, background noise.
Output ONLY the persona description in 1-2 sentences."""
        
        content = node_context.get('content', '')[:300]
        user_prompt = f"Generate a chaos scenario for testing this voice agent response: {content}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.grok_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-4-0709",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.9,
                        "max_tokens": 200
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    scenario = result['choices'][0]['message']['content'].strip()
                    return scenario
                else:
                    print(f"[Grok] API Error {response.status_code}: {response.text[:100]}")
                    return "User is skeptical and rushed, asking tough questions."
        except Exception as e:
            print(f"[Grok] Error: {e}")
            return "User is skeptical and asking tough questions."

    async def _call_openai_judge(self, audio: bytes, text: str, latency: float, scenario: str) -> Dict:
        """Use GPT-4o to judge the performance."""
        if not self.openai_api_key:
            print("[Director] ⚠️ No OpenAI API key, using fallback judgment")
            return {"total": 7.0, "latency": 7, "tonality": 7, "humanity": 7, "reasoning": ["Fallback"]}
        
        system_prompt = """You are an AI Director judging a voice agent's performance.
Evaluate based on:
1. LATENCY (1-10): Was there dead air? >1s is bad.
2. TONALITY (1-10): Did the text read naturally?
3. HUMANITY (1-10): Does it feel like a real person wrote this?

Respond with JSON only: {"latency": X, "tonality": X, "humanity": X, "total": X, "reasoning": ["..."]}"""

        user_prompt = f"""Scenario: {scenario}
Agent's Response: "{text[:500]}"
Measured Latency: {latency:.2f}s

Judge this response."""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    judgment = json.loads(result['choices'][0]['message']['content'])
                    return judgment
                else:
                    print(f"[OpenAI] API Error {response.status_code}")
                    return {"total": 5.0, "reasoning": ["API error"]}
        except Exception as e:
            print(f"[OpenAI] Error: {e}")
            return {"total": 5.0, "reasoning": [str(e)]}

    def _extract_speech_content(self, content: str) -> str:
        """Extract only the speakable content from node (Agent says: '...')"""
        import re
        
        # Find all "Agent says: "..." patterns
        pattern = r'Agent says:\s*["\'](.+?)["\']'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            # Join all speech parts for TTS testing
            return " ".join(matches)
        
        # Fallback: if no Agent says pattern, look for content in quotes
        quote_pattern = r'"([^"]{20,})"'
        quote_matches = re.findall(quote_pattern, content)
        if quote_matches:
            return " ".join(quote_matches[:3])  # Max 3 quotes
        
        # Last resort: return first 200 chars if no patterns found
        return content[:200] if content else "Hello, how can I help you today?"

    async def _generate_mutations(self, base_node_data: Dict) -> List[Dict]:
        """Generate 3 intelligent variant rewrites using GPT-5.2."""
        content = base_node_data.get('content', '') or ''
        
        if not self.openai_api_key:
            print("[Director] ⚠️ No OpenAI key, using fallback mutations")
            return self._fallback_mutations(base_node_data)
        
        variants = []
        variant_configs = [
            {
                "type": "Diplomat",
                "personality": "polite, patient, and understanding",
                "speech_style": "softer, more accommodating, uses phrases like 'I understand' and 'take your time'",
                "voice_settings": {"stability": 0.6, "similarity_boost": 0.7, "style": 0.1, "speed": 0.9}
            },
            {
                "type": "The Closer",
                "personality": "direct, confident, and action-oriented",
                "speech_style": "concise, assertive, uses urgency and clear calls to action",
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.0, "speed": 1.15}
            },
            {
                "type": "The Empath",
                "personality": "warm, emotionally intelligent, and relatable",
                "speech_style": "uses pauses for effect, emotional hooks, personal connection",
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.35, "speed": 1.0}
            }
        ]
        
        for config in variant_configs:
            try:
                # Pass full node data for comprehensive optimization
                rewritten_content = await self._rewrite_node_with_gpt(content, config, base_node_data)
                variant = copy.deepcopy(base_node_data)
                variant['content'] = rewritten_content
                variant['voice_settings'] = config['voice_settings']
                variant['_variant_type'] = config['type']
                variant['_speech_only'] = self._extract_speech_content(rewritten_content)
                variants.append(variant)
                print(f"[Director] ✅ Generated {config['type']} variant")
            except Exception as e:
                print(f"[Director] ❌ Error generating {config['type']}: {e}")
                # Add fallback variant
                variant = copy.deepcopy(base_node_data)
                variant['_variant_type'] = config['type']
                variant['_speech_only'] = self._extract_speech_content(content)
                variants.append(variant)
        
        return variants
    
    async def _rewrite_node_with_gpt(self, original_content: str, variant_config: Dict, full_node_data: Dict = None) -> str:
        """Use GPT-4o to intelligently rewrite the ENTIRE node including all features."""
        
        # Build comprehensive optimization prompt
        system_prompt = f"""You are an expert voice agent optimizer.
Rewrite the given node with a {variant_config['personality']} personality.

You must optimize ALL of the following:

1. **CONTENT** (Agent says + instructions):
   - Rewrite 'Agent says:' speech to be {variant_config['speech_style']}
   - Keep ## headers, - bullets, numbered lists structure
   - Adjust tactics to match personality

2. **GOALS** (if present):
   - Adjust goal wording to match personality approach

3. **TRANSITIONS** (if present):
   - Keep same target nodes, but adjust condition wording if needed

4. **VARIABLE EXTRACTION** (if present):
   - Improve variable descriptions for clarity
   - Optimize re-prompt messages to match personality

5. **VOICE SETTINGS**:
   - Suggest stability, speed, style values (0.0-1.0) that match the personality:
     - Diplomat: stability=0.6, speed=0.9, style=0.1
     - Closer: stability=0.4, speed=1.15, style=0.0
     - Empath: stability=0.55, speed=1.0, style=0.35

CRITICAL RULES:
- Preserve ALL transition logic keywords
- Keep ALL variable names exactly the same
- Output ONLY the rewritten content text, no JSON or explanations
- If uncertain about something, keep the original"""

        # Include full node context if available
        node_context = ""
        if full_node_data:
            transitions = full_node_data.get('transitions', [])
            variables = full_node_data.get('extract_variables', [])
            goal = full_node_data.get('goal', '')
            
            if goal:
                node_context += f"\n\n--- CURRENT GOAL ---\n{goal}"
            if transitions:
                node_context += f"\n\n--- CURRENT TRANSITIONS ---\n{json.dumps(transitions, indent=2)}"
            if variables:
                node_context += f"\n\n--- CURRENT VARIABLES ---\n{json.dumps(variables, indent=2)}"

        user_prompt = f"""Rewrite this node as a {variant_config['type']} variant:

--- CONTENT ---
{original_content[:4000]}{node_context}"""

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    rewritten = result['choices'][0]['message']['content'].strip()
                    return rewritten
                else:
                    print(f"[GPT-5.2] Error {response.status_code}: {response.text[:100]}")
                    return original_content
        except Exception as e:
            print(f"[GPT-5.2] Error: {e}")
            return original_content

    def _fallback_mutations(self, base_node_data: Dict) -> List[Dict]:
        """Fallback mutations when GPT is unavailable."""
        content = base_node_data.get('content', '') or ''
        speech = self._extract_speech_content(content)
        
        mutants = [copy.deepcopy(base_node_data) for _ in range(3)]
        
        mutants[0]['_variant_type'] = "Diplomat"
        mutants[0]['_speech_only'] = speech
        mutants[0]['voice_settings'] = {"stability": 0.6, "speed": 0.9}
        
        mutants[1]['_variant_type'] = "The Closer"
        mutants[1]['_speech_only'] = speech
        mutants[1]['voice_settings'] = {"stability": 0.4, "speed": 1.1}
        
        mutants[2]['_variant_type'] = "The Empath"
        mutants[2]['_speech_only'] = speech
        mutants[2]['voice_settings'] = {"stability": 0.5, "speed": 1.0}
        
        return mutants
        
        return mutants

    async def _run_streaming_test(self, node_data: Dict, scenario: str, voice_id: str = None):
        """
        Generate REAL audio via ElevenLabs for SPEECH CONTENT ONLY.
        Uses _speech_only field if available, otherwise extracts from content.
        """
        import time
        
        # Use extracted speech content, not full node
        text = node_data.get('_speech_only') or self._extract_speech_content(node_data.get('content', ''))
        
        if not text:
            return b'', '', 0.5
        
        print(f"[Director] 🎤 TTS for speech: {text[:80]}...")
        
        voice_settings = node_data.get('voice_settings', {})
        voice_id = voice_id or '21m00Tcm4TlvDq8ikWAM'  # Default Rachel voice
        
        if not self.elevenlabs_api_key:
            print("[Director] ⚠️ No ElevenLabs key, using simulated audio")
            await asyncio.sleep(0.2)
            return b'SIMULATED_AUDIO', text, 0.3
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
                
                data = {
                    "text": text[:1000],  # Limit text length for speed
                    "model_id": "eleven_flash_v2_5",  # Fastest model
                    "voice_settings": {
                        "stability": voice_settings.get('stability', 0.5),
                        "similarity_boost": 0.75,
                        "speed": voice_settings.get('speed', 1.0)
                    },
                    "optimize_streaming_latency": 4
                }
                
                headers = {
                    "xi-api-key": self.elevenlabs_api_key,
                    "Content-Type": "application/json"
                }
                
                chunks = []
                first_chunk_time = None
                
                async with client.stream('POST', url, headers=headers, json=data) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes():
                            if first_chunk_time is None:
                                first_chunk_time = time.time() - start_time
                            chunks.append(chunk)
                    else:
                        print(f"[Director] ElevenLabs error: {response.status_code}")
                        return b'', text, 1.0
                
                audio_data = b''.join(chunks)
                ttfb = first_chunk_time or (time.time() - start_time)
                
                print(f"[Director] 🎙️ TTS complete: {len(audio_data)} bytes, TTFB: {ttfb:.3f}s")
                return audio_data, text, ttfb
                
        except Exception as e:
            print(f"[Director] TTS error: {e}")
            return b'', text, 1.0

    async def promote_sandbox(self, sandbox_id: str) -> bool:
        """
        Promotes the sandbox config back to the live agent in the database.
        """
        await self._init_db()
        
        config = await self.get_sandbox_config(sandbox_id)
        if not config:
            raise ValueError("Sandbox not found")
        
        agent_id = config.get('id')
        
        result = await self.db.agents.update_one(
            {"id": agent_id, "user_id": self.user_id},
            {"$set": config}
        )
        
        if result.modified_count > 0:
            print(f"[Director] ✅ Promoted Sandbox {sandbox_id} to Live Agent {agent_id}")
            await self.db.director_sandboxes.delete_one({
                "sandbox_id": sandbox_id,
                "user_id": self.user_id
            })
            return True
        else:
            print(f"[Director] ❌ Failed to promote sandbox")
            return False
