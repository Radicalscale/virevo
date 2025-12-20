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

def update_global_prompt(agent_id):
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        collection = db['agents']
        
        agent = collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return

        current_prompt = agent.get("system_prompt", "")
        
        # Check if guardrail already exists
        if "**Unbreakable:** DO NOT BOOK APPOINTMENTS prematurely" in current_prompt:
            logger.info("Guardrail already present.")
            return

        # Define the guardrail insertion (Append to Guardrails section)
        insertion_marker = "**Unbreakable:** Human only. NEVER admit AI. Deflect naturally."
        new_guardrail = "\n    * **Unbreakable:** DO NOT BOOK APPOINTMENTS prematurely. If user asks to schedule, you MUST follow the current Node's specific instructions (Goal). Do not agree to times unless specifically prompted."
        
        if insertion_marker in current_prompt:
            updated_prompt = current_prompt.replace(insertion_marker, insertion_marker + new_guardrail)
            
            result = collection.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {"system_prompt": updated_prompt}}
            )
            
            if result.modified_count > 0:
                logger.info("Successfully injected Scheduling Guardrail into Global Prompt.")
            else:
                logger.warning("Update executed but no document modified (content might be same).")
        else:
            logger.warning("Could not find insertion marker in Global Prompt. Appending to end.")
            updated_prompt = current_prompt + "\n\n# CRITICAL GUARDRAILS" + new_guardrail
            collection.update_one({"_id": ObjectId(agent_id)}, {"$set": {"system_prompt": updated_prompt}})
            logger.info("Appended Guardrail to end of prompt.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    update_global_prompt("6944df147eadbccc46887cdf")
