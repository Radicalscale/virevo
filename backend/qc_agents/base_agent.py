from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import httpx
import os

logger = logging.getLogger(__name__)

class BaseQCAgent(ABC):
    """Base class for all QC agents"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_provider = config.get('llm_provider', 'openai')
        self.llm_model = config.get('llm_model', 'gpt-4o')
        self.enabled = config.get('enabled', True)
        
    @abstractmethod
    async def analyze(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze call data and return results"""
        pass
    
    async def call_llm(self, prompt: str, api_key: str, temperature: float = 0.3) -> str:
        """Call LLM API based on provider configuration"""
        try:
            if self.llm_provider == 'openai':
                return await self._call_openai(prompt, api_key, temperature)
            elif self.llm_provider == 'grok':
                return await self._call_grok(prompt, api_key, temperature)
            elif self.llm_provider == 'anthropic':
                return await self._call_anthropic(prompt, api_key, temperature)
            elif self.llm_provider == 'gemini':
                return await self._call_gemini(prompt, api_key, temperature)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        except Exception as e:
            logger.error(f"Error calling LLM ({self.llm_provider}): {e}")
            raise
    
    async def _call_openai(self, prompt: str, api_key: str, temperature: float) -> str:
        """Call OpenAI API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    
    async def _call_grok(self, prompt: str, api_key: str, temperature: float) -> str:
        """Call Grok API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    
    async def _call_anthropic(self, prompt: str, api_key: str, temperature: float) -> str:
        """Call Anthropic Claude API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            return response.json()['content'][0]['text']
    
    async def _call_gemini(self, prompt: str, api_key: str, temperature: float) -> str:
        """Call Google Gemini API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{self.llm_model}:generateContent",
                headers={"x-goog-api-key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperature}
                }
            )
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text']
    
    def extract_user_responses(self, transcript: str) -> str:
        """Extract only user/caller utterances from transcript"""
        user_lines = []
        for line in transcript.split('\n'):
            if line.startswith('User:') or line.startswith('Caller:'):
                user_lines.append(line.split(':', 1)[1].strip())
        return ' '.join(user_lines)
    
    def extract_agent_responses(self, transcript: str) -> str:
        """Extract only agent utterances from transcript"""
        agent_lines = []
        for line in transcript.split('\n'):
            if line.startswith('Agent:') or line.startswith('Assistant:'):
                agent_lines.append(line.split(':', 1)[1].strip())
        return ' '.join(agent_lines)
