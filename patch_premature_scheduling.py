
from pymongo import MongoClient
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
MONGO_URL = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
AGENT_ID = "6944df147eadbccc46887cdf"

# Target Nodes (Pre-Booking Chain)
TARGET_NODES = [
    "N001B_IntroAndHelpRequest_Only",
    "N_Opener_StackingIncomeHook_V3_CreativeTactic",
    "N_IntroduceModel_And_AskQuestions_V3_Adaptive",
    "N_KB_Q&A_With_StrategicNarrative_V3_Adaptive",
    "N200_Super_WorkAndIncomeBackground_V3_Adaptive",
    "N_Intro_Triage_V3", # Just in case
    # Greeting is usually script/simple, but if it has a goal, we can add it. 
    # Usually handled by transitions in Greeting. But User said "Any node".
    # I'll stick to the Conversational ones.
]

# The Toolkit Tactic
TACTIC_TEXT = """
- **Tactic for: Premature Booking / Asking to Schedule / Offering Time (Call Control)** → Agent must say verbatim: `<speak>Sure, but first we need to cover a few things before that to make sure this is the right fit. Then we can swing back to that.</speak>`
  - Then immediately return to the previous goal/question or the next question in the sequence.
"""

def patch_agent():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    agents_coll = db['agents']

    agent = agents_coll.find_one({"_id": ObjectId(AGENT_ID)})
    if not agent:
        logger.error("Agent not found")
        return

    logger.info(f"Patching Agent: {agent.get('agentName', 'Unknown')}")

    # Handle both structure types
    if 'call_flow' in agent:
        nodes = agent['call_flow']
        flow_key = 'call_flow'
    elif 'flow' in agent and 'nodes' in agent['flow']:
        nodes = agent['flow']['nodes']
        flow_key = 'flow.nodes'
    else:
        logger.error("Could not find flow structure")
        return

    modified_count = 0
    updated_nodes = []
    
    # We need to reconstruct the list if we modify it
    # Actually, we modify the dicts in place then update the whole list
    
    for node in nodes:
        label = node.get('data', {}).get('label') or node.get('label')
        
        # Check by label or ID (if I had IDs)
        # Checking if label contains base match
        is_target = False
        for target in TARGET_NODES:
            if target in str(label): # Loose match for versioning
                is_target = True
                break
        
        if is_target:
            node_data = node.get('data', {})
            goal = node_data.get('goal', '')
            
            # Check if already patched with NEW text
            if TACTIC_TEXT.strip() in goal:
                 logger.info(f"Skipping {label} - Already has NEW tactic")
                 continue

            # Check for OLD text and replace
            OLD_SNIPPET = "That's great that you're ready to move forward"
            if OLD_SNIPPET in goal:
                # We need to find the block. It's risky to replace just snippet.
                # But since I know I appended it...
                # I'll just Replace the "Strategic Toolkit" block if I can, or use Regex?
                # Simplest: Replace the whole specific Tactic line if it matches my previous format
                # The previous format was: "- **Tactic for: ... (Call Control)** -> Agent says: <speak>That's great... Is that fair?</speak>"
                # I'll try to find the whole line and replace it.
                # Or simplistic:
                # goal = re.sub(r"- \*\*Tactic for: Premature Booking.*?</speak>", TACTIC_TEXT.strip(), goal, flags=re.DOTALL)
                pass 
            
            # Actually, simplest approach:
            # If "Premature Booking" is in goal, but NOT TACTIC_TEXT (New), then it's Old.
            # I will remove the old block manually via string manipulation or just append new and delete old?
            # I'll just use Replace.

            # Check for INTERMEDIATE state (Agent says: Sure...)
            INTERMEDIATE_SNIPPET = "Sure, but first we need to cover a few things"
            if INTERMEDIATE_SNIPPET in goal and "verbatim" not in goal:
                 import re
                 # Replace the whole Tactic line
                 # Pattern: - \*\*Tactic for: Premature Booking.*?swing back to that\.</speak>
                 goal = re.sub(r"- \*\*Tactic for: Premature Booking.*?swing back to that\.</speak>", TACTIC_TEXT.strip(), goal, flags=re.DOTALL | re.MULTILINE)
                 node['data']['goal'] = goal
                 logger.info(f"Updated {label} from Intermediate to Verbatim")
                 modified_count += 1
                 continue

            if "Premature Booking" in goal:
                logger.info(f"Updating {label} with NEW Tactic")
                # Remove the old section roughly
                # It was appended at end of Strategic Toolkit.
                # I'll simply Read the goal, remove the old Tactic lines, then Repatch.
                # Or simpler:
                import re
                # Regex to match the tactic from "- **Tactic" to "</speak>"
                # My previous text ended with </speak> and newline.
                # Pattern: - \*\*Tactic for: Premature Booking.*?Is that fair\?</speak>
                goal = re.sub(r"- \*\*Tactic for: Premature Booking.*?Is that fair\?</speak>", TACTIC_TEXT.strip(), goal, flags=re.DOTALL | re.MULTILINE)
                node['data']['goal'] = goal
                modified_count += 1
            else:
                # Inject Toolkit (Fresh)
                if "## Strategic Toolkit" in goal:
                    new_goal = goal.replace("## Strategic Toolkit", "## Strategic Toolkit" + TACTIC_TEXT)
                    node['data']['goal'] = new_goal
                    logger.info(f"✅ Patched {label}")
                    modified_count += 1
                elif "Steps:" in goal:
                     node['data']['goal'] = goal + "\n\n## Strategic Toolkit" + TACTIC_TEXT
                     logger.info(f"✅ Patched {label} (Appended Toolkit)")
                     modified_count += 1

        updated_nodes.append(node)

    if modified_count > 0:
        if flow_key == 'call_flow':
            result = agents_coll.update_one(
                {"_id": ObjectId(AGENT_ID)},
                {"$set": {"call_flow": updated_nodes}}
            )
        else:
            result = agents_coll.update_one(
                {"_id": ObjectId(AGENT_ID)},
                {"$set": {"flow.nodes": updated_nodes}}
            )
            
        logger.info(f"Update Result: {result.modified_count} documents modified. ({modified_count} nodes updated)")
    else:
        logger.info("No nodes needed patching.")

if __name__ == "__main__":
    patch_agent()
