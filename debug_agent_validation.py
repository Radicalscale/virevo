
import json
from pydantic import ValidationError
from backend.models import Agent

def check_agent_json(file_path):
    print(f"Checking {file_path}...")
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check call_flow length
        if 'call_flow' in data:
            print(f"call_flow has {len(data['call_flow'])} items.")
            if len(data['call_flow']) > 66:
                node = data['call_flow'][66]
                print(f"Node at index 66 keys: {list(node.keys())}")
                if 'data' not in node:
                    print("ERROR: 'data' field missing in node at index 66.")
                    print(json.dumps(node, indent=2))
                else:
                    print("Node at index 66 has 'data' field.")
            else:
                print("call_flow has fewer than 67 items.")
        
        # Try full validation
        try:
            agent = Agent(**data)
            print("Validation SUCCESS")
        except ValidationError as e:
            print("Validation FAILED")
            print(e)
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_agent_json("optimizer3_agent.json")
