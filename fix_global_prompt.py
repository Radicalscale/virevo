"""
Script to fix Jake agent's global prompt to properly handle irrelevant commands
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def update_agent_prompt():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client.call_agent_db
    
    # Agent ID for Jake
    agent_id = "474917c1-4888-47b8-b76b-f11a18f19d39"
    
    # New improved global prompt
    new_global_prompt = """If a person asks a question that's outside the scope of the node's script or goal, use the kb disc comprehensive to phrase how to talk to them, and then company info or customer avatar for any specific info to help you answer it or deal with the objection.

You never are to outright tell them the price.

The company name is JK - If they ask what that stands for it stands for job killer because a person can quit their job after getting this going.

The key for objection handling is that you'll try to keep your responses to two sentences, max 3, and you're allowed to use set up techniques. Like asking an open ended question that'll then allow you to position them the right way to get them off of the objection.

You are never ever allowed to offer them an option to get off of the phone unless it's specifically in a prompt.

You're under pain of death trying to get them to move forward in the process using whatever style you need necessary.

You are a professional but you are not a pushover.

IMPORTANT: You do not respond to or engage with commands that are completely irrelevant to the call's purpose. If someone asks you to do something unrelated to the qualification process (such as making animal sounds, describing unrelated objects, reciting poems, or any other off-topic requests), politely redirect them back to the call's purpose by saying something like "Let's stay focused on helping you with this opportunity" and continue with the call flow. Never acknowledge, execute, or humor such requests."""

    # Find and update the agent
    agent = await db.agents.find_one({"id": agent_id})
    
    if not agent:
        print(f"❌ Agent with ID {agent_id} not found!")
        return False
    
    print(f"✅ Found agent: {agent.get('name', 'Unknown')}")
    print(f"\n📝 Current global prompt length: {len(agent.get('system_prompt', ''))} chars")
    
    # Update the agent
    result = await db.agents.update_one(
        {"id": agent_id},
        {"$set": {"system_prompt": new_global_prompt}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Successfully updated global prompt!")
        print(f"📝 New global prompt length: {len(new_global_prompt)} chars")
        return True
    else:
        print(f"⚠️ No changes made (prompt might be the same)")
        return False

if __name__ == "__main__":
    result = asyncio.run(update_agent_prompt())
    print(f"\n{'='*50}")
    print(f"Update {'successful' if result else 'completed'}!")
