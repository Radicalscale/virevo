import os
import logging
from pymongo import MongoClient
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB_NAME = 'test_database'
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

# The "Strategic Toolkit" instructions for Premature Booking
TOOLKIT_TEXT = """
### PREMATURE BOOKING / SCHEDULING REQUESTS:
If the user asks to book an appointment, schedule a time, or meet BEFORE you have confirmed they are qualified (completed this node's goal):
1.  **ACKNOWLEDGE**: "I appreciate you wanting to jump ahead..."
2.  **REFUSE**: "...but booking a time right now wouldn't be the best move without us first nailing down if this fits your goals."
3.  **PIVOT:** Return immediately to the current topic/question.
**DO NOT AGREE TO BOOK A TIME.**
"""

def apply_toolkit():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['agents']

    # Load target nodes from file
    try:
        with open("candidate_nodes.txt", "r") as f:
            targets = [line.strip().split(',')[0] for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("candidate_nodes.txt not found. Run scan first.")
        return

    logger.info(f"Loaded {len(targets)} target nodes.")

    agent = collection.find_one({"_id": AGENT_ID})
    if not agent:
        logger.error("Agent not found")
        return

    nodes = agent.get('call_flow', []) or agent['flow']['nodes']
    updated_count = 0

    for n in nodes:
        if n.get('id') in targets:
            # Check where to add instructions (goal or content)
            # data.content is usually the "Goal" for prompts
            data = n.get('data', {})
            current_content = data.get('content', '')
            
            # Check if already present to avoid duplication
            if "PREMATURE BOOKING" in current_content:
                logger.info(f"Skipping {n.get('id')} - Toolkit already present.")
                continue

            # Append Toolkit
            new_content = current_content + "\n\n" + TOOLKIT_TEXT
            
            # Update Node in Memory
            n['data']['content'] = new_content
            updated_count += 1
            logger.info(f"Updated {n.get('id')}: {data.get('label')}")

    # Bulk Write back to DB
    if updated_count > 0:
        result = collection.update_one(
            {"_id": AGENT_ID},
            {"$set": {"call_flow": nodes}}
        )
        logger.info(f"Successfully updated {updated_count} nodes in Database.")
    else:
        logger.info("No nodes needed updating.")

    client.close()

if __name__ == "__main__":
    apply_toolkit()
