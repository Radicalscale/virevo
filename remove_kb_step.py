from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

QA_LABEL = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"

# New Goal: Call Control + Narrative ONLY. No KB.
NEW_GOAL = """Determine what has already been done in this node by being aware of the conversation context and then do the next step.

## CRITICAL CALL CONTROL (HIGHEST PRIORITY)
- IF the User asks to book an appointment, schedule a time, or offers a time slot (e.g. "Can we book Tuesday?"):
  - YOU MUST REFUSE gently and pivot back to qualification.
  - RESPONSE MUST BE VERBATIM: <speak>Sure, but first we need to cover a few things before that to make sure this is the right fit. Then we can swing back to that.</speak>
  - DO NOT say "Perfect", "Locked in", or agree to the time.
  - Immediatey return to the previous question (e.g. "What part caught your interest?").

Steps:
- Highlight site value: each site earns five hundred to two thousand monthly, aim for ten sites.
- Ask twenty thousand value question only as specified: "With that in mind, would you honestly be upset if you had an extra twenty thousand a month coming in?"
- If user skeptical of twenty thousand question, refocus on desire for extra money and re-ask once.
- If twenty thousand question asked at least one time and response shows compliance (e.g., "No, who would be?", "That would be great", "Of course not", "Who would?") without skepticism, immediately stop talking and transition to next node.
- Never ask to set up an appointment.
- Never ask extra confirmation questions like "Make sense?" or echo user phrases."""

def update():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    
    updated = False
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        if label == QA_LABEL:
            print(f"🔧 Removing KB Step for {label}")
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
