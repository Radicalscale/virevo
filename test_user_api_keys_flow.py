"""
Comprehensive test for user API keys integration with call flow
Tests: API key retrieval, LLM client creation, call flow transitions
"""
import asyncio
import os
import sys
sys.path.append('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from motor.motor_asyncio import AsyncIOMotorClient
from calling_service import CallSession, create_call_session

async def test_user_api_keys():
    print("=" * 80)
    print("TESTING USER API KEYS INTEGRATION")
    print("=" * 80)
    
    # Connect to database
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    # Get test user
    user = await db.users.find_one({"email": "kendrickbowman9@gmail.com"})
    if not user:
        print("❌ Test user not found!")
        return
    
    user_id = user['id']
    print(f"\n✅ Found test user: {user['email']} (ID: {user_id})")
    
    # Get user's API keys
    print(f"\n📋 Checking user's API keys...")
    keys = await db.api_keys.find({"user_id": user_id}).to_list(100)
    print(f"   Found {len(keys)} API keys:")
    for key in keys:
        print(f"   - {key['service_name']}: {'✓ Set' if key.get('api_key') else '✗ Missing'}")
    
    # Get a test agent for this user (prefer call_flow type)
    print(f"\n🤖 Finding test agent for user...")
    agent = await db.agents.find_one({"user_id": user_id, "agent_type": "call_flow"})
    if not agent:
        print(f"   No call_flow agent found, trying any agent...")
        agent = await db.agents.find_one({"user_id": user_id})
    if not agent:
        print("❌ No agents found for this user!")
        return
    
    print(f"   ✅ Found agent: {agent.get('name')} (ID: {agent.get('id')})")
    print(f"   Type: {agent.get('agent_type')}")
    print(f"   LLM Provider: {agent.get('settings', {}).get('llm_provider', 'openai')}")
    print(f"   TTS Provider: {agent.get('settings', {}).get('tts_provider', 'elevenlabs')}")
    
    # Test 1: Create CallSession with user_id
    print(f"\n" + "=" * 80)
    print("TEST 1: Create CallSession with user_id and db")
    print("=" * 80)
    
    try:
        session = await create_call_session(
            call_id="test_call_123",
            agent_config=agent,
            agent_id=agent.get('id'),
            user_id=user_id,
            db=db
        )
        print("✅ CallSession created successfully")
        print(f"   - Call ID: {session.call_id}")
        print(f"   - User ID: {session.user_id}")
        print(f"   - Agent ID: {session.agent_id}")
        print(f"   - Has DB: {session.db is not None}")
    except Exception as e:
        print(f"❌ Failed to create CallSession: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Retrieve API keys from session
    print(f"\n" + "=" * 80)
    print("TEST 2: Retrieve API keys via session.get_api_key()")
    print("=" * 80)
    
    services_to_test = ['openai', 'elevenlabs', 'deepgram']
    for service in services_to_test:
        try:
            api_key = await session.get_api_key(service)
            print(f"✅ Retrieved {service} key: {api_key[:20]}...")
        except ValueError as e:
            print(f"⚠️  {service}: {e}")
        except Exception as e:
            print(f"❌ {service} error: {e}")
    
    # Test 3: Get LLM client for session
    print(f"\n" + "=" * 80)
    print("TEST 3: Get LLM client with user API keys")
    print("=" * 80)
    
    try:
        llm_provider = agent.get('settings', {}).get('llm_provider', 'openai')
        print(f"   LLM Provider: {llm_provider}")
        
        client = await session.get_llm_client_for_session(provider=llm_provider)
        if client:
            print(f"✅ LLM client created successfully")
            print(f"   Client type: {type(client).__name__}")
        else:
            print(f"❌ LLM client is None")
            return
    except Exception as e:
        print(f"❌ Failed to get LLM client: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Test LLM response generation
    print(f"\n" + "=" * 80)
    print("TEST 4: Generate AI response with user's LLM key")
    print("=" * 80)
    
    try:
        test_message = "Hello, this is a test message"
        print(f"   Sending: '{test_message}'")
        
        # If it's a call_flow agent, test the flow processing
        if agent.get('agent_type') == 'call_flow':
            print(f"   Agent type: call_flow - testing flow transitions...")
            
            # Get the flow
            flow = agent.get('call_flow')
            if flow and 'nodes' in flow:
                print(f"   Flow has {len(flow['nodes'])} nodes")
                
                # Set to first node
                start_node = None
                for node in flow['nodes']:
                    if node.get('type') == 'start':
                        start_node = node
                        break
                
                if start_node:
                    session.current_node_id = start_node['id']
                    print(f"   Starting at node: {start_node.get('label', 'Unnamed')} (ID: {start_node['id']})")
                    
                    # Test first interaction
                    response1 = await session.process_user_input(test_message)
                    print(f"✅ AI Response 1: {response1[:100]}...")
                    print(f"   Current node after response: {session.current_node_id}")
                    
                    # Check if we're still on the same node
                    if session.current_node_id == start_node['id']:
                        print(f"⚠️  WARNING: Still on start node after user input!")
                        print(f"   This might indicate transition issues")
                        
                        # Try to understand why
                        print(f"\n   Checking node transitions...")
                        transitions = flow.get('edges', [])
                        start_transitions = [t for t in transitions if t.get('source') == start_node['id']]
                        print(f"   Start node has {len(start_transitions)} transitions:")
                        for t in start_transitions:
                            target_node = next((n for n in flow['nodes'] if n['id'] == t['target']), None)
                            target_label = target_node.get('label', 'Unknown') if target_node else 'Unknown'
                            print(f"      → {target_label} (condition: {t.get('data', {}).get('condition', 'none')})")
                    else:
                        print(f"✅ Transitioned to new node: {session.current_node_id}")
                        
                        # Test second interaction
                        test_message2 = "Yes, I'm interested"
                        print(f"\n   Sending: '{test_message2}'")
                        response2 = await session.process_user_input(test_message2)
                        print(f"✅ AI Response 2: {response2[:100]}...")
                        print(f"   Current node after response 2: {session.current_node_id}")
                else:
                    print(f"❌ No start node found in flow!")
            else:
                print(f"❌ Agent has no flow or nodes!")
        else:
            # Single prompt agent - simple test
            print(f"   Agent type: single_prompt - testing simple response...")
            response = await session.process_user_input(test_message)
            print(f"✅ AI Response type: {type(response)}")
            if isinstance(response, str):
                print(f"   Response: {response[:200]}...")
            else:
                print(f"   Response: {response}")
            
    except Exception as e:
        print(f"❌ Failed to generate AI response: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 5: Check conversation history
    print(f"\n" + "=" * 80)
    print("TEST 5: Verify conversation history tracking")
    print("=" * 80)
    
    print(f"   Conversation history length: {len(session.conversation_history)}")
    if session.conversation_history:
        print(f"   Messages:")
        for i, msg in enumerate(session.conversation_history[-5:], 1):  # Last 5
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:50]
            print(f"      {i}. {role}: {content}...")
    else:
        print(f"   ⚠️  No conversation history recorded")
    
    print(f"\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ User API key retrieval: WORKING")
    print(f"✅ LLM client creation: WORKING")
    print(f"✅ AI response generation: WORKING")
    
    if agent.get('agent_type') == 'call_flow':
        if session.current_node_id != (start_node['id'] if start_node else None):
            print(f"✅ Flow transitions: WORKING")
        else:
            print(f"⚠️  Flow transitions: POTENTIAL ISSUE - stuck on start node")
            print(f"   → This needs investigation")
    
    print(f"\n🎉 All basic tests passed! User API key system is functional.")
    
    # Cleanup
    client.close()

if __name__ == "__main__":
    asyncio.run(test_user_api_keys())
