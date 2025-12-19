# Agent Builder Testing Workflow

## Purpose
This document provides instructions for iteratively testing and refining AI agent node behavior using direct MongoDB access. It enables rapid prototyping and debugging without needing to make actual phone calls.

## Context
During testing of the `JK First Caller-optimizer3` agent, we discovered that the LLM was hallucinating on certain nodes—ignoring node-specific prompts and following conversation history context instead. The `N_AskCapital_15k_V1_Adaptive` node was supposed to ask about $15-25k capital but instead talked about scheduling with "Kendrick".

**Root Cause:** The LLM (grok-4-fast-non-reasoning) was weighting conversation history more heavily than node instructions, causing drift from intended behavior.

**Solution:** This workflow allows us to:
1. Simulate conversations without actual calls
2. Identify which nodes deviate from expected behavior
3. Edit node prompts/transitions directly in MongoDB
4. Re-test immediately to verify fixes
5. Changes reflect in the UI call flow editor

---


## Test Agent Details
- **Name:** `JK First Caller-optimizer3-antigrav`
- **MongoDB ID:** `6944df147eadbccc46887cdf`
- **Nodes:** 65
- **Model:** `grok-4-fast-non-reasoning`

## MongoDB Connection
```python
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
DATABASE = 'test_database'
COLLECTION = 'agents'
```

---

## Quick Commands

### View a Node's Content
```bash
python3 -c "
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']
agent = db['agents'].find_one({'_id': ObjectId('6944df147eadbccc46887cdf')})

# Replace 'NODE_LABEL' with actual label
for node in agent.get('call_flow', []):
    if node.get('label') == 'NODE_LABEL':
        print(node.get('data', {}).get('content', 'No content'))
"
```

### Edit a Node's Content
```bash
python3 -c "
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']

# Update specific node content
db['agents'].update_one(
    {'_id': ObjectId('6944df147eadbccc46887cdf'), 'call_flow.label': 'NODE_LABEL'},
    {
        '\$set': {
            'call_flow.\$.data.content': '''YOUR NEW CONTENT HERE''',
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
    }
)
print('✅ Node updated!')
"
```

### Edit Global Prompt
```bash
python3 -c "
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']

db['agents'].update_one(
    {'_id': ObjectId('6944df147eadbccc46887cdf')},
    {'\$set': {'system_prompt': '''NEW GLOBAL PROMPT HERE'''}}
)
print('✅ Global prompt updated!')
"
```

### Edit Node Transitions
```bash
python3 -c "
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']

# New transitions array
new_transitions = [
    {'id': '1', 'condition': 'CONDITION TEXT', 'nextNode': 'TARGET_NODE_ID'}
]

db['agents'].update_one(
    {'_id': ObjectId('6944df147eadbccc46887cdf'), 'call_flow.label': 'NODE_LABEL'},
    {'\$set': {'call_flow.\$.data.transitions': new_transitions}}
)
print('✅ Transitions updated!')
"
```

### List All Node Labels
```bash
python3 -c "
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada')
db = client['test_database']
agent = db['agents'].find_one({'_id': ObjectId('6944df147eadbccc46887cdf')})

for node in agent.get('call_flow', []):
    print(f\"  - {node.get('label')}\")"
```

---

## Testing Workflow

### 1. Run Debug Script
```bash
cd /Users/kendrickbowman/Downloads/Andro-main
python3 debug_agent_nodes.py --agent-id "6944df147eadbccc46887cdf"
```

### 2. Interactive Commands
- Type message to simulate user input
- `/node NODE_LABEL` - Show node details
- `/history` - Show conversation history
- `/nodes` - Show node transition history
- `/quit` - Exit

### 3. Scripted Test
Create a script file with one user message per line:
```text
# script.txt
Hello
Um, I have my own business
We do about 15k a month
12k
Yeah
Sure
kendrickbomer9@gmail.com
```

Run:
```bash
python3 debug_agent_nodes.py --agent-id "6944df147eadbccc46887cdf" --script script.txt
```

---

## Iterative Testing Loop

1. **Test** - Run script or interactive session
2. **Identify Issue** - Note which node behaved incorrectly
3. **View Node** - Check current prompt/transitions
4. **Edit** - Update MongoDB with fix
5. **Verify in UI** - Refresh call flow editor to confirm change
6. **Re-test** - Run again to verify fix
7. **Repeat** until agent flows correctly

---

## Node Properties You Can Edit

| Property | Path | Description |
|----------|------|-------------|
| Content/Prompt | `call_flow.$.data.content` | Main node instructions |
| Goal | `call_flow.$.data.goal` | Node's objective |
| Mode | `call_flow.$.data.mode` | `prompt` or `script` |
| Transitions | `call_flow.$.data.transitions` | Array of next nodes |
| use_parallel_llm | `call_flow.$.data.use_parallel_llm` | Parallel processing |
| Global Prompt | `system_prompt` | Agent-wide instructions |

---

## Files Created

- `/Users/kendrickbowman/Downloads/Andro-main/debug_agent_nodes.py` - Testing tool
- `/Users/kendrickbowman/Downloads/Andro-main/AGENT_TESTING_WORKFLOW.md` - This document

---

## Test Transcript (From logs.1766107896816.log)

This is the actual conversation that revealed the node hallucination issue. Use this to reproduce the problem.

### Cleaned User Lines (for script.txt)
```text
Um, so you have, like, a system where you're teaching us how to, like, sell people things, like goods?
Yeah, that sounds about right.
Hmm, No, who would be?
I do my own thing.
Why do you need to know that?
Um, what do you mean move the needle for me in a meaningful way?
Um, we do about 15k a month.
12k.
Yeah.
Sure.
kendrickbomer9@gmail.com
```

### Full Transcript with Agent Responses
| Turn | Speaker | Text |
|------|---------|------|
| 1 | Agent | Okay, in a nutshell, we set up passive income websites, and we let them produce income for you. What... |
| 2 | User | Um, so you have, like, a system where you're teaching us how to, like, sell people things, like g... |
| 3 | Agent | [N] Not quite, that's a common mix-up. We teach you to build your own websites that generate leads a... |
| 4 | User | Yeah, that sounds about right. |
| 5 | Agent | [N] Great, glad that lands better. So, to put some numbers on it, each site can bring in five hundre... |
| 6 | User | Hmm, No, who would be? |
| 7 | Agent | [H] Exactly, right? Nobody would turn that down. So, are you working for someone right now, or do yo... |
| 8 | User | I do my own thing. |
| 9 | Agent | [N] Awesome, that's the perfect spot for this. As a business owner, where's your monthly revenue at ... |
| 10 | User | Why do you need to know that? |
| 11 | Agent | [N] That's a fair question. The only reason I ask is to get a sense of your current scale, so I can ... |
| 12 | User | Um, what do you mean move the needle for me in a meaningful way? |
| 13 | Agent | [N] I mean, if your business is already pulling in, say, a hundred thousand a month, adding another ... |
| 14 | User | Um, we do about 15k a month. |
| 15 | Agent | [N] Got it, fifteen K a month is a solid base. And in the last two years, what was the highest month... |
| 16 | User | 12k. |
| 17 | Agent | [N] So, with your business topping out around twelve K in a good month, do you see yourself being ab... |
| 18 | User | Yeah. |
| 19 | Agent | **⚠️ ISSUE NODE: `N_AskCapital_15k_V1_Adaptive`** - Agent said: "Great, that's the confidence we need. With that kind of potential in play, are you open to hoppi..." (HALLUCINATED - should have asked about $15-25k capital!) |
| 20 | User | Sure. |
| 21 | Agent | **⚠️ HALLUCINATION CONTINUES:** "Perfect, I'll get you set up with Kendrick right now—he's the one who'll walk you through the fu..." |
| 22 | User | kendrickbomer9@gmail.com |

### Issue Identified
- **Node:** `N_AskCapital_15k_V1_Adaptive`
- **Expected:** "Okay, got it. For this kind of business, it definitely helps to have about fifteen to twenty-five thousand dollars in liquid capital..."
- **Actual:** "Great, that's the confidence we need. With that kind of potential in play, are you open to hopping..."
- **Root Cause:** LLM followed conversation context instead of node's Opening Gambit
