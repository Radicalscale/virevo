from pymongo import MongoClient
from bson import ObjectId
import time

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

# IDs
INTRO_ID = "1763163400676"
QA_ID = "1763206946898"
N200_NEW_ID = "1763222222222"

# Content
QA_LABEL = "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive"
QA_GOAL = """Determine what has already been done in this node by being aware of the conversation context and then do the next step.

Steps:
- Handle user questions using KB, qualifier setter, company info, objection handler, or toolkit.
- Highlight site value: each site earns five hundred to two thousand monthly, aim for ten sites.
- Ask twenty thousand value question only as specified: "With that in mind, would you honestly be upset if you had an extra twenty thousand a month coming in?"
- If user skeptical of twenty thousand question, refocus on desire for extra money and re-ask once.
- If twenty thousand question asked at least one time and response shows compliance (e.g., "No, who would be?", "That would be great", "Of course not", "Who would?") without skepticism, immediately stop talking and transition to next node.
- Never ask to set up an appointment.
- Never ask extra confirmation questions like "Make sense?" or echo user phrases.

## Strategic Toolkit
- **Tactic for: Premature Booking / Asking to Schedule / Offering Time (Call Control)** → Agent must say verbatim: `<speak>Sure, but first we need to cover a few things before that to make sure this is the right fit. Then we can swing back to that.</speak>`
  - Then immediately return to the previous goal/question or the next question in the sequence."""

QA_TRANSITION_CONDITION = """...would you honestly be upset if you had an extra twenty thousand a month coming in?</speak>
- If user skeptical of twenty thousand question, refocus on desire for extra money and re-ask once.
- If twenty thousand question asked at least one time and response shows compliance (e.g., "No, who would be?", "That would be great", "Of course not", "Who would?") without skepticism, immediately stop talking and transition to next node.
- Never ask to set up an appointment.
- Never ask extra confirmation questions like "Make sense?" or echo user phrases."""

def restore():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    updated_nodes = []
    
    qa_found = False
    
    for n in nodes:
        label = n.get('data', {}).get('label') or n.get('label')
        
        # 1. Fix Intro ID
        if label == 'N_IntroduceModel_And_AskQuestions_V3_Adaptive':
            print(f"🔧 Fixing Intro ID: {INTRO_ID}")
            n['id'] = INTRO_ID
            # Ensure transition points to QA
            n['data']['auto_transition_after_response'] = QA_ID
        
        # 2. Fix N200 ID
        if label == 'N200_Super_WorkAndIncomeBackground_V3_Adaptive':
            print(f"🔧 Fixing N200 ID: {N200_NEW_ID}")
            n['id'] = N200_NEW_ID
            
        # 3. Fix QA Node
        if label == QA_LABEL:
            print(f"🔧 Fixing Existing QA Node ID: {QA_ID}")
            n['id'] = QA_ID
            n['data']['goal'] = QA_GOAL
            # Update Transition 0
            if n['data']['transitions']:
                n['data']['transitions'][0]['nextNode'] = N200_NEW_ID
                n['data']['transitions'][0]['condition'] = QA_TRANSITION_CONDITION
            else:
                 n['data']['transitions'] = [{
                     "id": str(int(time.time()*1000)),
                     "condition": QA_TRANSITION_CONDITION,
                     "nextNode": N200_NEW_ID,
                     "check_variables": []
                 }]
            qa_found = True
            
        updated_nodes.append(n)
        
    # 4. Create QA Node if missing
    if not qa_found:
        print(f"✨ Creating Missing QA Node: {QA_ID}")
        new_node = {
            "id": QA_ID,
            "type": "conversation",
            "label": QA_LABEL,
            "data": {
                "label": QA_LABEL,
                "goal": QA_GOAL,
                "transitions": [{
                     "id": str(int(time.time()*1000)),
                     "condition": QA_TRANSITION_CONDITION,
                     "nextNode": N200_NEW_ID,
                     "check_variables": []
                 }],
                 "mode": "script" # usually script for these logic nodes? Or conversation?
                 # Need to check Intro mode logic. Assume conversation if prompt driven.
            }
        }
        # Insert after Intro? Or just append.
        # Order matters!
        # I'll append. Backend sorts by ID usually? No, flow order.
        # I should insert it after Intro.
        
        final_nodes = []
        for n in updated_nodes:
            final_nodes.append(n)
            label = n.get('data', {}).get('label') or n.get('label')
            if label == 'N_IntroduceModel_And_AskQuestions_V3_Adaptive':
                final_nodes.append(new_node)
        updated_nodes = final_nodes

    # Save
    if 'call_flow' in agent:
        DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"call_flow": updated_nodes}})
    else:
        DB['agents'].update_one({'_id': AGENT_ID}, {"$set": {"flow.nodes": updated_nodes}})
        
    print("✅ Restoration Complete.")

if __name__ == "__main__":
    restore()
