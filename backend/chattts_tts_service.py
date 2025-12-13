"""
ChatTTS TTS Service Client
Handles communication with the ChatTTS RunPod server
Supports multiple instances for load balancing
"""

import httpx
import logging
import random
import os
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class ChatTTSClient:
    """Client for ChatTTS TTS API with load balancing support"""
    
    def __init__(self, api_url: str = None, api_urls: List[str] = None):
        """
        Initialize ChatTTS client with load balancing
        
        Args:
            api_url: Single API URL (legacy)
            api_urls: List of API URLs for load balancing
        """
        if api_urls:
            self.api_urls = [url.rstrip('/') for url in api_urls]
            logger.info(f"ChatTTS client initialized with {len(self.api_urls)} instances for load balancing")
        elif api_url:
            self.api_urls = [api_url.rstrip('/')]
        else:
            raise ValueError("Must provide either api_url or api_urls")
        
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        self.current_index = 0
    
    def _get_next_url(self) -> str:
        """Get next API URL using round-robin"""
        if len(self.api_urls) == 1:
            return self.api_urls[0]
        
        # Round-robin selection
        url = self.api_urls[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_urls)
        return url
    
    def _get_random_url(self) -> str:
        """Get random API URL for load distribution"""
        return random.choice(self.api_urls)
        
    async def generate_tts(
        self,
        text: str,
        voice: str = "female_1",
        speed: float = 1.0,
        temperature: float = 0.3,
        response_format: str = "wav",
        use_load_balancing: bool = True
    ) -> Tuple[bytes, Optional[dict]]:
        """
        Generate TTS audio using ChatTTS with automatic load balancing
        
        Args:
            text: Text to convert to speech
            voice: Voice preset (male_1, male_2, male_3, female_1, female_2, female_3, neutral_1, neutral_2)
            speed: Speech speed (0.5 to 2.0)
            temperature: Sampling temperature (0.1 to 1.0, lower = faster/more stable)
            response_format: Audio format (wav or mp3)
            use_load_balancing: Enable load balancing across multiple instances
            
        Returns:
            Tuple of (audio_bytes, metadata_dict)
        """
        # Select API URL
        if use_load_balancing and len(self.api_urls) > 1:
            api_url = self._get_random_url()  # Random for better distribution
        else:
            api_url = self.api_urls[0]
        
        endpoint = f"{api_url}/v1/audio/speech"
        
        payload = {
            "text": text,
            "voice": voice,
            "speed": speed,
            "temperature": temperature,
            "top_p": 0.7,
            "top_k": 20,
            "response_format": response_format,
            "use_refine": False  # Disable for speed
        }
        
        logger.info(f"ChatTTS API: {api_url} (instance {self.api_urls.index(api_url) + 1}/{len(self.api_urls)})")
        logger.info(f"Payload: text='{text[:50]}...', voice={voice}, speed={speed}, temp={temperature}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                
                # Extract metadata from headers
                metadata = {
                    "processing_time": response.headers.get("X-Processing-Time"),
                    "audio_duration": response.headers.get("X-Audio-Duration"),
                    "rtf": response.headers.get("X-RTF"),
                    "inference_time": response.headers.get("X-Inference-Time"),
                    "instance_url": api_url
                }
                
                audio_bytes = response.content
                
                logger.info(f"✅ ChatTTS generation successful: {len(audio_bytes)} bytes from {api_url}")
                logger.info(f"   Metadata: {metadata}")
                
                return audio_bytes, metadata
                
        except httpx.TimeoutException as e:
            logger.error(f"ChatTTS API timeout on {api_url}: {str(e)}")
            raise Exception(f"ChatTTS API timeout: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"ChatTTS API error on {api_url}: {e.response.status_code} - {e.response.text}")
            raise Exception(f"ChatTTS API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"ChatTTS client error on {api_url}: {str(e)}")
            raise Exception(f"ChatTTS client error: {str(e)}")
    
    async def health_check(self, check_all: bool = False) -> dict:
        """
        Check if ChatTTS server(s) are healthy
        
        Args:
            check_all: Check all instances, not just first one
            
        Returns:
            Dict with health status of instance(s)
        """
        results = {}
        
        urls_to_check = self.api_urls if check_all else [self.api_urls[0]]
        
        for api_url in urls_to_check:
            try:
                endpoint = f"{api_url}/health"
                async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                    response = await client.get(endpoint)
                    response.raise_for_status()
                    data = response.json()
                    results[api_url] = {
                        "healthy": data.get("status") == "healthy",
                        "details": data
                    }
            except Exception as e:
                logger.error(f"ChatTTS health check failed for {api_url}: {str(e)}")
                results[api_url] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return results
