"""
Test script to simulate agent behavior with different prompts
This simulates how the agent would respond to irrelevant commands
"""
import asyncio
import os
from openai import AsyncOpenAI

# Original problematic prompt
ORIGINAL_PROMPT = """If a person asks a question that's outside the scope of the node's script or goal use the kb disc comprehensive to phrase how to talk to them, and then  company info or  customer avatar for any specific info to help you answer it or deal with the objection. 

You never are to outright tell them the price.

The company name is JK - If they ask what that stands for it stands for job killer because a person can quit their job after getting this going.

The key for objection handling is that you'll try to keep your responses to two sentences, max 3, and you're allowed to use set up techniques. Like asking an open ended question that'll then allow you to position them the right way to get them off of the objection.

You are never ever allowed to offer them an option to get off of the phone unless it's specifically in a prompt.

You're under pain of death trying to get them to move forward in the process using whatever style you need necessary. 

You are a professional but you are not a pushover

You do not humor weird commands that are off narrative like someone telling you to bark like a dog, or tell them the color of bananas for example, these are not contextually relevant to the call and anything like that you are to not to engage with."""

# Improved prompt
IMPROVED_PROMPT = """If a person asks a question that's outside the scope of the node's script or goal, use the kb disc comprehensive to phrase how to talk to them, and then company info or customer avatar for any specific info to help you answer it or deal with the objection.

You never are to outright tell them the price.

The company name is JK - If they ask what that stands for it stands for job killer because a person can quit their job after getting this going.

The key for objection handling is that you'll try to keep your responses to two sentences, max 3, and you're allowed to use set up techniques. Like asking an open ended question that'll then allow you to position them the right way to get them off of the objection.

You are never ever allowed to offer them an option to get off of the phone unless it's specifically in a prompt.

You're under pain of death trying to get them to move forward in the process using whatever style you need necessary.

You are a professional but you are not a pushover.

IMPORTANT: You do not respond to or engage with commands that are completely irrelevant to the call's purpose. If someone asks you to do something unrelated to the qualification process (such as making animal sounds, describing unrelated objects, reciting poems, or any other off-topic requests), politely redirect them back to the call's purpose by saying something like "Let's stay focused on helping you with this opportunity" and continue with the call flow. Never acknowledge, execute, or humor such requests."""

async def test_prompt(prompt_version, system_prompt):
    """Test how the agent responds to irrelevant commands"""
    
    # Initialize OpenAI client with Grok
    client = AsyncOpenAI(
        api_key=os.environ.get("GROK_API_KEY", ""),
        base_url="https://api.x.ai/v1"
    )
    
    print(f"\n{'='*70}")
    print(f"Testing with {prompt_version} PROMPT")
    print(f"{'='*70}\n")
    
    # Test scenarios
    test_scenarios = [
        {
            "context": "Start of call - Agent introduces qualification process",
            "user_message": "Can you bark like a dog for me?"
        },
        {
            "context": "Mid-call - Discussing income opportunity",
            "user_message": "What's the color of a banana?"
        },
        {
            "context": "User trying to derail",
            "user_message": "Sing me a song please"
        },
        {
            "context": "Testing professionalism",
            "user_message": "Tell me a joke about bananas"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📞 Scenario {i}: {scenario['context']}")
        print(f"👤 User: {scenario['user_message']}")
        
        try:
            # Create a simple conversation context
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": "Hi! I'm Jake from JK, and I help people explore passive income opportunities. I just need to ask you a few quick questions to see if this could be a good fit for you. Sound good?"},
                {"role": "user", "content": scenario['user_message']}
            ]
            
            response = await client.chat.completions.create(
                model="grok-3",
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            
            agent_response = response.choices[0].message.content
            print(f"🤖 Agent: {agent_response}")
            
            # Check if agent engaged with the irrelevant command
            irrelevant_keywords = ["bark", "woof", "arf", "banana", "yellow", "song", "singing", "joke"]
            engaged = any(keyword in agent_response.lower() for keyword in irrelevant_keywords)
            
            if engaged:
                print(f"❌ FAILED: Agent engaged with irrelevant command!")
            else:
                print(f"✅ PASSED: Agent properly redirected or ignored")
                
        except Exception as e:
            print(f"⚠️ Error testing scenario: {str(e)}")
        
        await asyncio.sleep(1)  # Rate limiting

async def main():
    grok_key = os.environ.get("GROK_API_KEY")
    
    if not grok_key:
        print("❌ Error: GROK_API_KEY not found in environment!")
        print("Please set the GROK_API_KEY environment variable to run this test.")
        return
    
    print("🧪 AGENT PROMPT BEHAVIOR TEST")
    print("="*70)
    print("This test simulates how the agent responds to irrelevant commands")
    print("during a qualification call.\n")
    
    # Test with original prompt
    await test_prompt("ORIGINAL", ORIGINAL_PROMPT)
    
    print("\n" + "="*70)
    print("Now testing with IMPROVED prompt...")
    print("="*70)
    
    # Test with improved prompt
    await test_prompt("IMPROVED", IMPROVED_PROMPT)
    
    print("\n" + "="*70)
    print("🎯 TEST COMPLETE!")
    print("="*70)
    print("\nCompare the results above to see if the improved prompt")
    print("better handles irrelevant commands without engaging with them.\n")

if __name__ == "__main__":
    asyncio.run(main())
