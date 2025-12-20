from pymongo import MongoClient
from bson import ObjectId

CLIENT = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
DB = CLIENT['test_database']
AGENT_ID = ObjectId('6944df147eadbccc46887cdf')

def dump():
    agent = DB['agents'].find_one({'_id': AGENT_ID})
    print(agent.get("system_prompt", "NO SYSTEM PROMPT"))

if __name__ == "__main__":
    dump()
