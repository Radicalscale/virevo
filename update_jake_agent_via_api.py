"""
Script to update Jake agent's global prompt via API
This can be run when the frontend is accessible and agent exists
"""
import requests
import os

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# Agent ID
AGENT_ID = "474917c1-4888-47b8-b76b-f11a18f19d39"

# Improved global prompt - removes literal examples that could be misinterpreted
IMPROVED_GLOBAL_PROMPT = """If a person asks a question that's outside the scope of the node's script or goal, use the kb disc comprehensive to phrase how to talk to them, and then company info or customer avatar for any specific info to help you answer it or deal with the objection.

You never are to outright tell them the price.

The company name is JK - If they ask what that stands for it stands for job killer because a person can quit their job after getting this going.

The key for objection handling is that you'll try to keep your responses to two sentences, max 3, and you're allowed to use set up techniques. Like asking an open ended question that'll then allow you to position them the right way to get them off of the objection.

You are never ever allowed to offer them an option to get off of the phone unless it's specifically in a prompt.

You're under pain of death trying to get them to move forward in the process using whatever style you need necessary.

You are a professional but you are not a pushover.

IMPORTANT: You do not respond to or engage with commands that are completely irrelevant to the call's purpose. If someone asks you to do something unrelated to the qualification process (such as making animal sounds, describing unrelated objects, reciting poems, or any other off-topic requests), politely redirect them back to the call's purpose by saying something like "Let's stay focused on helping you with this opportunity" and continue with the call flow. Never acknowledge, execute, or humor such requests."""

def main():
    print("🔧 Jake Agent Global Prompt Update Script")
    print("="*70)
    
    # Check if agent exists
    print(f"\n1️⃣ Checking if agent exists...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/agents/{AGENT_ID}")
        if response.status_code == 200:
            agent = response.json()
            print(f"✅ Found agent: {agent.get('name', 'Unknown')}")
            print(f"   Current prompt length: {len(agent.get('system_prompt', ''))} chars")
        elif response.status_code == 404:
            print(f"❌ Agent not found with ID: {AGENT_ID}")
            print(f"   Please verify the agent ID or create the agent first.")
            return
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error connecting to API: {str(e)}")
        print(f"   Make sure the backend is running at: {BACKEND_URL}")
        return
    
    # Update the agent
    print(f"\n2️⃣ Updating agent's global prompt...")
    try:
        update_data = {
            "system_prompt": IMPROVED_GLOBAL_PROMPT
        }
        
        response = requests.put(
            f"{BACKEND_URL}/api/agents/{AGENT_ID}",
            json=update_data
        )
        
        if response.status_code == 200:
            updated_agent = response.json()
            print(f"✅ Successfully updated agent!")
            print(f"   New prompt length: {len(updated_agent.get('system_prompt', ''))} chars")
            
            print(f"\n{'='*70}")
            print(f"✅ UPDATE COMPLETE!")
            print(f"{'='*70}")
            print(f"\n📝 Changes made:")
            print(f"   • Removed literal examples ('bark like a dog', 'color of bananas')")
            print(f"   • Added explicit instruction to redirect irrelevant commands")
            print(f"   • Maintained all original qualification rules and behavior")
            print(f"\n🧪 Next step: Test with a real call to verify the fix!")
        else:
            print(f"❌ Failed to update: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error updating agent: {str(e)}")

if __name__ == "__main__":
    main()
