from pymongo import MongoClient
from bson import ObjectId
import certifi

MONGO_URI = "mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada"
DB_NAME = "test_database"
COLLECTION_NAME = "agents"
AGENT_ID = "6944df147eadbccc46887cdf"
GREETING_NODE_ID = "2"
CONFIRM_NAME_NODE_ID = "1766180529241"
INTRO_NODE_ID = "1763159750250"

def repair_node():
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    agent = collection.find_one({"_id": ObjectId(AGENT_ID)})
    if not agent:
        print("❌ Agent not found")
        return

    # 1. Find Greeting Node to get Wrong Number Target
    greeting_node = next((n for n in agent['call_flow'] if n['id'] == GREETING_NODE_ID), None)
    if not greeting_node:
        print("❌ Greeting node not found")
        return

    wrong_number_target_id = None
    for t in greeting_node.get('transitions', []):
        condition = t.get('condition', '').lower()
        if "wrong number" in condition:
            wrong_number_target_id = t.get('nextNode')
            print(f"✅ Found Wrong Number Target from Greeting: {wrong_number_target_id}")
            break
            
    if not wrong_number_target_id:
        print("⚠️ Could not find Wrong Number target in Greeting. Using default guess (Ending: 1763197918747).")
        wrong_number_target_id = "1763197918747"


    # 2. Construct New Transitions
    new_transitions = [
        # 0. High Prio: Explicit Confirmation
        {
            "id": "confirm_yes",
            "condition": "Confirms name (Yes|Speaking|This is he/she|etc). Proceed to Intro.",
            "nextNode": INTRO_NODE_ID
        },
        # 1. High Prio: Wrong Number
        {
            "id": "confirm_wrong",
            "condition": "Wrong number (No John here|Wrong number|etc) - dont assume. Proceed to Wrong Number handling.",
            "nextNode": wrong_number_target_id
        },
        # 2. Rescue: Catch-All
        {
            "id": "confirm_rescue",
            "condition": "Does not conform (Any other response / Resistance / Question). User asks 'Who is this?', 'Is this a scam?', or ignores name request. Proceed to Intro.",
            "nextNode": INTRO_NODE_ID
        }
    ]

    # 3. Update Node
    node_index = next((i for i, n in enumerate(agent['call_flow']) if n['id'] == CONFIRM_NAME_NODE_ID), -1)
    if node_index == -1:
        print("❌ Confirm Name Node not found")
        return

    node = agent['call_flow'][node_index]
    print(f"DEBUG: Node Top Level Transitions: {len(node.get('transitions', []))}")
    if 'data' in node:
        print(f"DEBUG: Node Data Level Transitions: {len(node['data'].get('transitions', []))}")
        # Update DATA level too
        node['data']['transitions'] = new_transitions
        print("✅ Updated transitions inside 'data' field.")
    else:
        print("⚠️ Node has no 'data' field. Creating it.")
        node['data'] = {'transitions': new_transitions}

    # Also keep top level just in case?
    node['transitions'] = new_transitions
    agent['call_flow'][node_index] = node


    # 4. Clear Cache (system_prompt)
    unset_op = {}
    if 'system_prompt' in agent:
        unset_op["system_prompt"] = ""
        print("✅ Will clear 'system_prompt' field.")

    # 5. Write to DB
    update_op = {"$set": {"call_flow": agent['call_flow']}}
    if unset_op:
        update_op["$unset"] = unset_op
    
    result = collection.update_one(
        {"_id": ObjectId(AGENT_ID)},
        update_op
    )
    
    if result.modified_count > 0:
        print("✅ Successfully updated agent in DB.")
    else:
        print("⚠️ No changes made (maybe already up to date).")

if __name__ == "__main__":
    repair_node()
