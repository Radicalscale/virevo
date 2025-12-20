from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

QA_LABEL = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"

# New Goal: "No Calendar" Frame + Explicit Script
NEW_GOAL = """Determine what has already been done in this node by being aware of the conversation context and then do the next step.

## SYSTEM OVERRIDE: NO CALENDAR ACCESS
- You DO NOT have access to a calendar.
- You CANNOT book appointments, schedule times, or lock in slots.
- IF the User asks to book/schedule (e.g. "Can we book Tuesday?"):
  - You MUST say exactly this deflection script: <speak>Sure, but first we need to cover a few things before that to make sure this is the right fit. Then we can swing back to that.</speak>
  - After saying the script, IMMEDIATELY return to the qualification questions.

Steps:
- Highlight site value: each site earns five hundred to two thousand monthly, aim for ten sites.
- Ask twenty thousand value question only as specified: "With that in mind, would you honestly be upset if you had an extra twenty thousand a month coming in?"
- If user skeptical of twenty thousand question, refocus on desire for extra money and re-ask once.
- If twenty thousand question asked at least one time and response shows compliance (e.g., "No, who would be?", "That would be great", "Of course not", "Who would?") without skepticism, immediately stop talking and transition to next node.
- Follow the SYSTEM OVERRIDE if user asks to book. Do not deviate."""

def update():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    updated = False
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        if label == QA_LABEL:
            print(f"🔧 Final Tweak for {label}")
            n['data']['goal'] = NEW_GOAL
            updated = True
            
    if updated:
        if 'call_flow' in agent:
            DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"call_flow": nodes}})
        else:
            DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"flow.nodes": nodes}})
        print("✅ Update Saved.")
    else:
        print("❌ Node not found.")

if __name__ == "__main__":
    update()
