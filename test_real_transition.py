import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
db_name = 'test_database'
backend_url = 'https://api.li-ai.org'

async def main():
    client_db = AsyncIOMotorClient(mongo_url)
    db = client_db[db_name]
    
    # Find agent
    agent = await db.agents.find_one({"name": "JK First Caller-copy-copy"})
    agent_id = agent['id']
    
    print("Found agent:", agent['name'])
    print("Agent ID:", agent_id)
    print()
    
    # Find the node with your example transition
    call_flow = agent['call_flow']
    target_node = None
    for node in call_flow:
        transitions = node.get('data', {}).get('transitions', [])
        for trans in transitions:
            if 'User agrees (yes/sure/okay/agreeing to hear more' in trans.get('condition', ''):
                target_node = node
                print("Found target node!")
                print(f"Node: {node['label']}")
                print(f"Node ID: {node['id']}")
                print(f"Transition condition: {trans['condition']}")
                print(f"Next node: {trans['nextNode']}")
                print()
                break
        if target_node:
            break
    
    if not target_node:
        print("Could not find target node")
        return
    
    # Get auth cookie by checking sessions collection
    sessions = await db.sessions.find().sort('_id', -1).limit(1).to_list(length=1)
    if not sessions:
        print("No sessions found - need to login first")
        return
    
    # Test through the API
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        # Start test session
        print("Starting test session...")
        response = await http_client.post(
            f"{backend_url}/api/agents/{agent_id}/test/start",
            json={},
            cookies={"session": sessions[0].get('session_id', '')}
        )
        
        if response.status_code != 200:
            print(f"Error starting session: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        session_id = data.get('session_id')
        print(f"Session ID: {session_id}")
        print()
        
        # Send test message
        print("Sending test message: 'yes sure'")
        response = await http_client.post(
            f"{backend_url}/api/agents/{agent_id}/test/message",
            json={
                "message": "yes sure",
                "session_id": session_id
            },
            cookies={"session": sessions[0].get('session_id', '')}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        print("Response:")
        print(f"  Current node: {result.get('current_node_label')}")
        print(f"  Agent response: {result.get('agent_response')[:100]}")
        print()
    
    client_db.close()

asyncio.run(main())
