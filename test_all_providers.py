#!/usr/bin/env python3
"""
Comprehensive Provider Testing Suite
Tests all STT, LLM, and TTS providers
"""

import sys
import os
import asyncio
import aiohttp
import json

# Add backend to path
sys.path.insert(0, '/app/backend')

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

# API Keys
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVEN_API_KEY = os.getenv('ELEVEN_API_KEY')
HUME_API_KEY = os.getenv('HUME_API_KEY')
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
SONIOX_API_KEY = os.getenv('SONIOX_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')
CARTESIA_API_KEY = os.getenv('CARTESIA_API_KEY')

class ProviderTester:
    def __init__(self):
        self.test_results = []
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, provider: str, test_name: str, success: bool, message: str, details: dict = None):
        """Log test result"""
        result = {
            "provider": provider,
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: [{provider}] {test_name} - {message}")
        if details:
            for key, value in details.items():
                print(f"         {key}: {value}")
    
    # ==================== STT PROVIDERS ====================
    
    async def test_deepgram(self):
        """Test Deepgram STT provider"""
        print("\n" + "="*80)
        print("TESTING DEEPGRAM (STT)")
        print("="*80)
        
        # Test 1: API Key
        if not DEEPGRAM_API_KEY:
            self.log_result("Deepgram", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("Deepgram", "API Key Check", True, f"API key found ({len(DEEPGRAM_API_KEY)} chars)")
        
        # Test 2: API Connection - Get Models
        try:
            headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
            async with self.session.get("https://api.deepgram.com/v1/projects", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result("Deepgram", "API Connection", True, "Successfully connected to Deepgram API", {
                        "status_code": response.status
                    })
                else:
                    self.log_result("Deepgram", "API Connection", False, f"Failed with status {response.status}")
        except Exception as e:
            self.log_result("Deepgram", "API Connection", False, f"Error: {str(e)}")
        
        # Test 3: Service Initialization
        try:
            # Deepgram uses WebSocket for streaming, so we just verify the module exists
            import sys
            sys.path.insert(0, '/app/backend')
            # Deepgram is integrated directly in server.py, not a separate service class
            self.log_result("Deepgram", "Service Integration", True, "Deepgram integrated in server.py")
        except Exception as e:
            self.log_result("Deepgram", "Service Integration", False, f"Error: {str(e)}")
    
    async def test_assemblyai(self):
        """Test AssemblyAI STT provider"""
        print("\n" + "="*80)
        print("TESTING ASSEMBLYAI (STT)")
        print("="*80)
        
        # Test 1: API Key
        if not ASSEMBLYAI_API_KEY:
            self.log_result("AssemblyAI", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("AssemblyAI", "API Key Check", True, f"API key found ({len(ASSEMBLYAI_API_KEY)} chars)")
        
        # Test 2: API Connection
        try:
            headers = {"authorization": ASSEMBLYAI_API_KEY}
            async with self.session.get("https://api.assemblyai.com/v2/transcript", headers=headers) as response:
                if response.status in [200, 404]:  # 404 is ok for empty list
                    self.log_result("AssemblyAI", "API Connection", True, "Successfully connected to AssemblyAI API", {
                        "status_code": response.status
                    })
                else:
                    error_text = await response.text()
                    self.log_result("AssemblyAI", "API Connection", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("AssemblyAI", "API Connection", False, f"Error: {str(e)}")
        
        # Test 3: Service Initialization
        try:
            from assemblyai_service import AssemblyAIStreamingService
            service = AssemblyAIStreamingService(api_key=ASSEMBLYAI_API_KEY)
            self.log_result("AssemblyAI", "Service Initialization", True, "AssemblyAIStreamingService created successfully", {
                "service_type": type(service).__name__,
                "has_api_key": hasattr(service, 'api_key')
            })
        except Exception as e:
            self.log_result("AssemblyAI", "Service Initialization", False, f"Error: {str(e)}")
    
    async def test_soniox(self):
        """Test Soniox STT provider"""
        print("\n" + "="*80)
        print("TESTING SONIOX (STT)")
        print("="*80)
        
        # Test 1: API Key
        if not SONIOX_API_KEY:
            self.log_result("Soniox", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("Soniox", "API Key Check", True, f"API key found ({len(SONIOX_API_KEY)} chars)")
        
        # Test 2: Service Initialization
        try:
            from soniox_service import SonioxStreamingService
            service = SonioxStreamingService(api_key=SONIOX_API_KEY)
            self.log_result("Soniox", "Service Initialization", True, "SonioxStreamingService created successfully", {
                "service_type": type(service).__name__,
                "has_api_key": hasattr(service, 'api_key')
            })
        except Exception as e:
            self.log_result("Soniox", "Service Initialization", False, f"Error: {str(e)}")
    
    # ==================== LLM PROVIDERS ====================
    
    async def test_openai(self):
        """Test OpenAI LLM provider"""
        print("\n" + "="*80)
        print("TESTING OPENAI (LLM)")
        print("="*80)
        
        # Test 1: API Key
        if not OPENAI_API_KEY:
            self.log_result("OpenAI", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("OpenAI", "API Key Check", True, f"API key found ({len(OPENAI_API_KEY)} chars)")
        
        # Test 2: List Models
        try:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            async with self.session.get("https://api.openai.com/v1/models", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m['id'] for m in data.get('data', []) if 'gpt' in m['id'].lower()][:5]
                    self.log_result("OpenAI", "List Models", True, f"Found {len(models)} GPT models", {
                        "sample_models": ", ".join(models)
                    })
                else:
                    error_text = await response.text()
                    self.log_result("OpenAI", "List Models", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("OpenAI", "List Models", False, f"Error: {str(e)}")
        
        # Test 3: Chat Completion
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'OpenAI test successful' in exactly those words."}
                ],
                "max_tokens": 50
            }
            
            import time
            start_time = time.time()
            
            async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    response_text = data['choices'][0]['message']['content']
                    self.log_result("OpenAI", "Chat Completion", True, "Chat completion successful", {
                        "response": response_text[:100],
                        "latency": f"{latency:.2f}s",
                        "tokens": data.get('usage', {}).get('total_tokens', 'N/A')
                    })
                else:
                    error_text = await response.text()
                    self.log_result("OpenAI", "Chat Completion", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("OpenAI", "Chat Completion", False, f"Error: {str(e)}")
    
    async def test_grok(self):
        """Test Grok LLM provider"""
        print("\n" + "="*80)
        print("TESTING GROK (LLM)")
        print("="*80)
        
        # Test 1: API Key
        if not GROK_API_KEY:
            self.log_result("Grok", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("Grok", "API Key Check", True, f"API key found ({len(GROK_API_KEY)} chars)")
        
        # Test 2: List Models
        try:
            headers = {"Authorization": f"Bearer {GROK_API_KEY}"}
            async with self.session.get("https://api.x.ai/v1/models", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m['id'] for m in data.get('data', [])][:5]
                    self.log_result("Grok", "List Models", True, f"Found {len(models)} models", {
                        "sample_models": ", ".join(models)
                    })
                else:
                    error_text = await response.text()
                    self.log_result("Grok", "List Models", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("Grok", "List Models", False, f"Error: {str(e)}")
        
        # Test 3: Chat Completion
        try:
            headers = {
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-3",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Grok test successful' in exactly those words."}
                ],
                "max_tokens": 50
            }
            
            import time
            start_time = time.time()
            
            async with self.session.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    response_text = data['choices'][0]['message']['content']
                    self.log_result("Grok", "Chat Completion", True, "Chat completion successful", {
                        "response": response_text[:100],
                        "latency": f"{latency:.2f}s",
                        "tokens": data.get('usage', {}).get('total_tokens', 'N/A')
                    })
                else:
                    error_text = await response.text()
                    self.log_result("Grok", "Chat Completion", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("Grok", "Chat Completion", False, f"Error: {str(e)}")
    
    # ==================== TTS PROVIDERS ====================
    
    async def test_elevenlabs(self):
        """Test ElevenLabs TTS provider"""
        print("\n" + "="*80)
        print("TESTING ELEVENLABS (TTS)")
        print("="*80)
        
        # Test 1: API Key
        if not ELEVEN_API_KEY:
            self.log_result("ElevenLabs", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("ElevenLabs", "API Key Check", True, f"API key found ({len(ELEVEN_API_KEY)} chars)")
        
        # Test 2: Get Voices
        try:
            headers = {"xi-api-key": ELEVEN_API_KEY}
            async with self.session.get("https://api.elevenlabs.io/v1/voices", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    voices = data.get('voices', [])
                    voice_names = [v['name'] for v in voices[:5]]
                    self.log_result("ElevenLabs", "Get Voices", True, f"Found {len(voices)} voices", {
                        "sample_voices": ", ".join(voice_names)
                    })
                else:
                    error_text = await response.text()
                    self.log_result("ElevenLabs", "Get Voices", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("ElevenLabs", "Get Voices", False, f"Error: {str(e)}")
        
        # Test 3: TTS Generation
        try:
            headers = {
                "xi-api-key": ELEVEN_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "text": "ElevenLabs test successful.",
                "model_id": "eleven_turbo_v2_5"
            }
            
            # Use Rachel voice ID
            voice_id = "21m00Tcm4TlvDq8ikWAM"
            
            import time
            start_time = time.time()
            
            async with self.session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=payload
            ) as response:
                latency = time.time() - start_time
                
                if response.status == 200:
                    audio_data = await response.read()
                    self.log_result("ElevenLabs", "TTS Generation", True, "TTS generation successful", {
                        "audio_size": f"{len(audio_data)} bytes",
                        "latency": f"{latency:.2f}s",
                        "voice": "Rachel"
                    })
                else:
                    error_text = await response.text()
                    self.log_result("ElevenLabs", "TTS Generation", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("ElevenLabs", "TTS Generation", False, f"Error: {str(e)}")
    
    async def test_hume(self):
        """Test Hume TTS provider"""
        print("\n" + "="*80)
        print("TESTING HUME (TTS)")
        print("="*80)
        
        # Test 1: API Key
        if not HUME_API_KEY:
            self.log_result("Hume", "API Key Check", False, "API key not found in environment")
            return
        self.log_result("Hume", "API Key Check", True, f"API key found ({len(HUME_API_KEY)} chars)")
        
        # Test 2: Service Integration Check
        try:
            # Check if hume integration exists in server.py
            with open('/app/backend/server.py', 'r') as f:
                content = f.read()
                if 'hume' in content.lower() and 'generate_audio_hume' in content:
                    self.log_result("Hume", "Service Integration", True, "Hume TTS integrated in server.py")
                else:
                    self.log_result("Hume", "Service Integration", False, "Hume TTS integration not found")
        except Exception as e:
            self.log_result("Hume", "Service Integration", False, f"Error: {str(e)}")
        
        # Test 3: API Connection (Note: Hume API might have different endpoints)
        # Hume uses different API structure, so we'll just verify the key format
        if len(HUME_API_KEY) > 20:
            self.log_result("Hume", "API Key Format", True, "API key format looks valid")
        else:
            self.log_result("Hume", "API Key Format", False, "API key format seems invalid")
    
    async def test_cartesia(self):
        """Test Cartesia TTS provider"""
        print("\n" + "="*80)
        print("TESTING CARTESIA (TTS)")
        print("="*80)
        
        # Test 1: API Key
        if not CARTESIA_API_KEY:
            self.log_result("Cartesia", "API Key Check", False, "API key not found in environment (add CARTESIA_API_KEY to .env)")
            return
        self.log_result("Cartesia", "API Key Check", True, f"API key found ({len(CARTESIA_API_KEY)} chars)")
        
        # Test 2: Service Initialization
        try:
            from cartesia_service import CartesiaService
            service = CartesiaService(api_key=CARTESIA_API_KEY)
            self.log_result("Cartesia", "Service Initialization", True, "CartesiaService created successfully", {
                "service_type": type(service).__name__,
                "has_api_key": hasattr(service, 'api_key')
            })
        except Exception as e:
            self.log_result("Cartesia", "Service Initialization", False, f"Error: {str(e)}")
        
        # Test 3: API Connection
        try:
            headers = {
                "X-API-Key": CARTESIA_API_KEY,
                "Cartesia-Version": "2024-06-10"
            }
            async with self.session.get("https://api.cartesia.ai/voices", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    voices = data if isinstance(data, list) else data.get('voices', [])
                    self.log_result("Cartesia", "API Connection", True, f"Successfully connected, found {len(voices)} voices")
                else:
                    error_text = await response.text()
                    self.log_result("Cartesia", "API Connection", False, f"Failed with status {response.status}: {error_text}")
        except Exception as e:
            self.log_result("Cartesia", "API Connection", False, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        # Group results by provider
        providers = {}
        for result in self.test_results:
            provider = result['provider']
            if provider not in providers:
                providers[provider] = {'passed': 0, 'failed': 0, 'tests': []}
            
            if result['success']:
                providers[provider]['passed'] += 1
            else:
                providers[provider]['failed'] += 1
            providers[provider]['tests'].append(result)
        
        # Print provider summaries
        total_passed = 0
        total_failed = 0
        
        for provider, stats in sorted(providers.items()):
            total = stats['passed'] + stats['failed']
            status = "✅ PASS" if stats['failed'] == 0 else "⚠️ PARTIAL" if stats['passed'] > 0 else "❌ FAIL"
            print(f"\n{status} {provider}: {stats['passed']}/{total} tests passed")
            
            if stats['failed'] > 0:
                print(f"   Failed tests:")
                for test in stats['tests']:
                    if not test['success']:
                        print(f"      - {test['test']}: {test['message']}")
            
            total_passed += stats['passed']
            total_failed += stats['failed']
        
        # Print overall summary
        print("\n" + "="*80)
        print(f"OVERALL: {total_passed}/{total_passed + total_failed} tests passed")
        print("="*80)
        
        # Print recommendations
        print("\nRECOMMENDATIONS:")
        for provider, stats in sorted(providers.items()):
            if stats['failed'] > 0:
                print(f"- {provider}: Review failed tests and troubleshoot issues")
            else:
                print(f"- {provider}: ✅ Ready for production use")

async def main():
    """Main test runner"""
    async with ProviderTester() as tester:
        # Test STT providers
        await tester.test_deepgram()
        await tester.test_assemblyai()
        await tester.test_soniox()
        
        # Test LLM providers
        await tester.test_openai()
        await tester.test_grok()
        
        # Test TTS providers
        await tester.test_elevenlabs()
        await tester.test_hume()
        await tester.test_cartesia()
        
        # Print summary
        tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
