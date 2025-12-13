#!/usr/bin/env python3
"""
Test what text is being generated and sent to TTS
"""

import asyncio
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession
import os

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def test_node_12():
    """Test what happens when processing node 12 (Work Background)"""
    
    agent = await db.agents.find_one({'id': '474917c1-4888-47b8-b76b-f11a18f19d39'})
    
    # Create a session
    session = CallSession(
        call_id="test_node_12",
        agent_config=agent,
        agent_id=agent.get('id')
    )
    
    # Set up variables
    session.session_variables['customer_name'] = 'Kendrick'
    session.session_variables['customer_email'] = 'kendrickbowman9@gmail.com'
    session.session_variables['from_number'] = '+14048000152'
    session.session_variables['to_number'] = '+17708336397'
    session.session_variables['phone_number'] = '+17708336397'
    
    # Parse flow
    session.flow_nodes = {node['id']: node for node in agent.get('call_flow', [])}
    session.flow_edges = agent.get('call_flow_edges', [])
    session.agent_type = agent.get('agent_type', 'call_flow')
    
    # Manually set to node 12
    session.current_node_id = '12'
    
    print("="*80)
    print("TESTING NODE 12 (Work Background)")
    print("="*80)
    
    # Get the node
    node = session.flow_nodes.get('12')
    print(f"\nNode Label: {node.get('label')}")
    print(f"Node Type: {node.get('type')}")
    print(f"Node Mode: {node.get('data', {}).get('mode')}")
    
    content = node.get('data', {}).get('content', '')
    print(f"\nOriginal Content: {repr(content)}")
    print(f"Content Length: {len(content)} chars")
    print(f"Content Bytes: {content.encode('utf-8')}")
    
    # Process it through the session
    print(f"\n{'='*80}")
    print("PROCESSING THROUGH SESSION")
    print(f"{'='*80}\n")
    
    response = await session.process_user_input("No")
    
    print(f"\nResponse Type: {type(response)}")
    print(f"Response: {response}")
    
    if isinstance(response, dict):
        text = response.get('text', '')
        print(f"\nExtracted Text: {repr(text)}")
        print(f"Text Length: {len(text)} chars")
        print(f"Text Bytes: {text.encode('utf-8')}")
        
        # Check for any weird characters
        for i, char in enumerate(text):
            if ord(char) > 127 or ord(char) < 32:
                if char not in ['\n', '\r', '\t']:
                    print(f"⚠️ Non-ASCII or control char at position {i}: {repr(char)} (ord={ord(char)})")

if __name__ == "__main__":
    asyncio.run(test_node_12())
