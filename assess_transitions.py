import json
import re

def assess_agent(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
            data = json.loads(content)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    nodes = data.get("call_flow", [])
    print(f"Analyzing {len(nodes)} nodes for strict transitions...\n")

    high_risk_nodes = []

    for node in nodes:
        node_id = node.get("id")
        label = node.get("label", "Unknown")
        node_type = node.get("type")
        data = node.get("data", {})
        
        transitions = data.get("transitions", [])
        extract_vars = data.get("extract_variables", [])
        
        # Skip ending nodes or logic nodes usually
        if node_type not in ["conversation", "collect_input"]:
            continue

        risk_factors = []
        
        # Factor 1: Mandatory Variables with Strict Transition Checks
        mandatory_vars = [v["name"] for v in extract_vars if v.get("mandatory")]
        
        for t in transitions:
            condition = t.get("condition", "").lower()
            check_vars = t.get("check_variables", [])
            
            # Check for strict keywords in condition
            strict_keywords = ["specific", "explicitly", "exact", "number", "date", "amount", "must say"]
            found_keywords = [k for k in strict_keywords if k in condition]
            
            if found_keywords:
                risk_factors.append(f"Strict condition phrasing in Trans '{t.get('id')}': '{condition[:50]}...' (Keywords: {found_keywords})")
            
            # Check if transition requires variables
            if check_vars:
                risk_factors.append(f"Transition '{t.get('id')}' requires variables: {check_vars}")
                
            # Check if condition implies data but variables aren't checked (Soft Strictness)
            if ("date" in condition or "time" in condition or "amount" in condition) and not check_vars:
                # This is actually risky because the LLM might enforce it in reasoning even if not explicit variable check
                risk_factors.append(f"Condition necessitates data but no explicit variable check (LLM Enforcement Risk): '{condition[:50]}...'")

        # Factor 2: Single Strict Transition (No Fallback)
        if len(transitions) == 1:
            t = transitions[0]
            if "specific" in t.get("condition", "").lower() or t.get("check_variables"):
                 risk_factors.append("Single transition point with strict requirements (Bottleneck Risk)")

        if risk_factors:
            high_risk_nodes.append({
                "label": label,
                "id": node_id,
                "risks": risk_factors
            })

    print(f"Found {len(high_risk_nodes)} High Risk Nodes:\n")
    for n in high_risk_nodes:
        print(f"🔴 Node: {n['label']} ({n['id']})")
        for r in n['risks']:
            print(f"   - {r}")
        print("-" * 40)

if __name__ == "__main__":
    assess_agent("agent_bbeda2.json")
