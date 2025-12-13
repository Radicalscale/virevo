"""
Script to update all LLM client calls in calling_service.py to use session-based API keys
"""
import re

# Read the file
with open('/app/backend/calling_service.py', 'r') as f:
    content = f.read()

# Pattern 1: Replace get_openai_client() calls with await self.get_llm_client_for_session("openai")
# But only when inside CallSession methods (has self.)
pattern1 = r'(\s+)client = get_openai_client\(\)'
replacement1 = r'\1client = await self.get_llm_client_for_session("openai")'
content = re.sub(pattern1, replacement1, content)

# Pattern 2: Replace grok client calls with session-based approach
pattern2 = r'client = await get_llm_client\("grok", api_key=grok_key\)'
replacement2 = r'client = await self.get_llm_client_for_session("grok")'
content = re.sub(pattern2, replacement2, content)

# Pattern 3: Replace openai get_llm_client calls
pattern3 = r'client = await get_llm_client\("openai"\)'
replacement3 = r'client = await self.get_llm_client_for_session("openai")'
content = re.sub(pattern3, replacement3, content)

# Pattern 4: Remove unnecessary grok_key retrieval lines that are no longer needed
# This pattern looks for grok_key retrieval followed by the client call
pattern4 = r'grok_key = await get_api_key\("grok"\)\s+client = await self\.get_llm_client_for_session\("grok"\)'
replacement4 = r'client = await self.get_llm_client_for_session("grok")'
content = re.sub(pattern4, replacement4, content)

# Similar for grok_key from settings
pattern5 = r'grok_key = settings\.get\(["\']grok_api_key["\']\)\s+client = await self\.get_llm_client_for_session\("grok"\)'
replacement5 = r'client = await self.get_llm_client_for_session("grok")'
content = re.sub(pattern5, replacement5, content)

# Write the file back
with open('/app/backend/calling_service.py', 'w') as f:
    f.write(content)

print("✅ Updated all LLM client calls in calling_service.py")
print("   - Replaced get_openai_client() calls")
print("   - Replaced get_llm_client() calls with session-based approach")
print("   - Removed unnecessary grok_key retrieval")
