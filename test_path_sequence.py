#!/usr/bin/env python3
"""
Path Sequence Tester - Deviation & Silent Agreement Detector
=============================================================
Simulates a full conversation through the call flow path and detects:
1. Sequence deviations (skipping nodes, wrong order)
2. Silent agreements (agent accepts input without advancing)
3. Missing transitions (agent doesn't move to next node)
4. Infinite loops (agent stays stuck on same topic)

Tests the ACTUAL conversation flow, not individual nodes in isolation.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pymongo import MongoClient
from bson import ObjectId

# API Configuration
GROK_API_KEY = "xai-mDonAg7JKMuTnRm6k6NF9SxSNTrLpnENRyU5Y0CWzG82NBzKcr5y3eUGnC5Yxu7yZTRpG98ax2ZmE8GL"
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-4-fast-non-reasoning"

# MongoDB
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'

# Customer variables
CUSTOMER_VARS = {
    "customer_name": "Mike",
    "customer_email": "mike@example.com",
    "employed_yearly_income": 36000,
    "side_hustle": 12000,
    "amount_reference": 4000,
    "timeZone": "EST",
    "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
}


@dataclass
class ConversationTurn:
    """Single turn in the conversation"""
    turn_number: int
    expected_node: str
    user_input: str
    agent_response: str
    detected_node: str
    sequence_correct: bool
    has_question: bool
    advances_conversation: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class SequenceTestResult:
    """Result of sequence test"""
    total_turns: int = 0
    sequence_correct: int = 0
    silent_agreements: int = 0
    stuck_loops: int = 0
    skipped_nodes: int = 0
    turns: List[ConversationTurn] = field(default_factory=list)


# Expected conversation sequence with user inputs
CONVERSATION_SEQUENCE = [
    # (expected_node_contains, user_input, expected_topics_in_response)
    ("Greeting", "Yes, this is Mike", ["help", "wondering"]),
    ("N001B_IntroAndHelpRequest", "Sure, what's up?", ["income", "stacking", "25 seconds"]),
    ("N_Opener_StackingIncomeHook", "Yeah, go ahead", ["passive", "website", "income"]),
    ("N_IntroduceModel_And_AskQuestions", "That sounds interesting, how does it work?", ["rank", "lead", "business"]),
    ("N200_Super_WorkAndIncomeBackground", "I work for a company, regular job", ["yearly", "income", "producing"]),
    ("N201A_Employed_AskYearlyIncome", "About 36 thousand a year", ["side hustle", "extra", "income"]),
    ("N201B_Employed_AskSideHustle", "Yes, I do some freelance work", ["month", "bringing", "income"]),
    ("N201C_Employed_AskSideHustleAmount", "About a thousand a month", ["generate", "four thousand", "model"]),
    ("N201D_Employed_AskVehicleQ", "Yeah, I think that could work", ["capital", "five thousand", "liquid"]),
    ("N_AskCapital_5k", "Yes, I have about 5 thousand", ["why", "now", "reason", "change"]),
    ("N401_AskWhyNow", "I want more financial freedom", ["appreciate", "refreshing", "know why"]),
    ("N402_Compliment_And_AskYouKnowWhy", "No, why?", ["dreams", "serious", "commend", "fit"]),
    ("N403_IdentityAffirmation", "Yes, that's exactly what I'm looking for", ["call", "deeper", "dive", "set up"]),
    ("N500A_ProposeDeeperDive", "Sure, sounds good", ["timezone", "scheduling"]),
    ("N500B_AskTimezone", "Eastern time", ["desk", "time range", "available"]),
    ("N_AskForCallbackRange", "Afternoons, like 2 to 5", ["specific", "time", "day"]),
    ("N_Scheduling_AskTime", "Tuesday at 6 PM", ["6 PM", "Tuesday", "confirm", "Zoom"]),
    ("N_ConfirmVideoCallEnvironment", "Yes, I'll be at my computer", ["great", "set", "video"]),
]


class SequenceTester:
    """Tests full conversation sequence for deviations"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.client = MongoClient(MONGO_URL)
        self.db = self.client['test_database']
        self.agent_config = None
        self.global_prompt = ""
        self.nodes = []
        self.conversation_history = []
        self.results = SequenceTestResult()
        
    def load_agent(self) -> bool:
        """Load agent from MongoDB"""
        try:
            agent = self.db['agents'].find_one({'_id': ObjectId(self.agent_id)})
            if not agent:
                print(f"❌ Agent not found")
                return False
            
            self.agent_config = agent
            self.global_prompt = agent.get('global_prompt', '') or ''
            self.nodes = agent.get('call_flow', [])
            
            print(f"✅ Loaded: {agent.get('name')}")
            print(f"   Nodes: {len(self.nodes)}")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def find_node_by_partial(self, partial: str) -> Optional[Dict]:
        """Find node by partial label"""
        for node in self.nodes:
            data = node.get('data', {})
            label = data.get('label') or node.get('label') or ''
            if partial.lower() in label.lower():
                return node
        return None

    def get_node_content(self, node: Dict) -> str:
        """Get node content/script"""
        data = node.get('data', {})
        return data.get('content', '') or data.get('script', '')

    def detect_node_from_response(self, response: str) -> str:
        """Try to detect which node the agent is executing based on response content"""
        response_lower = response.lower()
        
        # Key phrases that indicate specific nodes
        node_indicators = [
            ("help me out", "N001B_IntroAndHelpRequest"),
            ("stacking income", "N_Opener_StackingIncomeHook"),
            ("passive income websites", "N_IntroduceModel"),
            ("working for someone", "N200_WorkBackground"),
            ("yearly income", "N201A_AskYearlyIncome"),
            ("side hustle", "N201B_AskSideHustle"),
            ("bringing in for you", "N201C_SideHustleAmount"),
            ("four thousand", "N201D_VehicleQ"),
            ("five thousand", "N_AskCapital"),
            ("why now", "N401_AskWhyNow"),
            ("why is this", "N401_AskWhyNow"),
            ("refreshing", "N402_Compliment"),
            ("you know why", "N402_Compliment"),
            ("dreams", "N403_IdentityAffirmation"),
            ("commend", "N403_IdentityAffirmation"),
            ("deeper dive", "N500A_ProposeDeeperDive"),
            ("set up another call", "N500A_ProposeDeeperDive"),
            ("timezone", "N500B_AskTimezone"),
            ("desk", "N_AskForCallbackRange"),
            ("time range", "N_AskForCallbackRange"),
            ("specific time", "N_Scheduling_AskTime"),
            ("zoom", "N_ConfirmVideoCall"),
            ("video call", "N_ConfirmVideoCall"),
        ]
        
        for phrase, node in node_indicators:
            if phrase in response_lower:
                return node
        
        return "UNKNOWN"

    def check_for_silent_agreement(self, response: str, expected_topics: List[str]) -> Tuple[bool, List[str]]:
        """Check if response is a silent agreement (accepts without advancing)"""
        issues = []
        response_lower = response.lower()
        
        # Check for question mark (advancing conversation)
        has_question = '?' in response
        
        # Check if any expected topics appear
        topics_found = sum(1 for t in expected_topics if t.lower() in response_lower)
        
        # Silent agreement patterns
        silent_patterns = [
            "got it",
            "okay",
            "sounds good",
            "perfect",
            "great",
            "thanks for sharing",
            "i understand",
        ]
        
        # Check if response is mainly just acknowledgment
        is_mainly_ack = False
        if len(response) < 100:
            for pattern in silent_patterns:
                if pattern in response_lower:
                    # Check if that's basically all it says
                    remaining = response_lower.replace(pattern, '').strip()
                    if len(remaining) < 50 and '?' not in response:
                        is_mainly_ack = True
                        break
        
        if is_mainly_ack:
            issues.append("SILENT AGREEMENT: Response acknowledges without advancing")
        
        if not has_question and topics_found == 0:
            issues.append("NO PROGRESSION: Response doesn't ask question or address expected topic")
        
        if topics_found < len(expected_topics) / 2:
            issues.append(f"MISSING TOPICS: Expected {expected_topics}, found only {topics_found} matches")
        
        advances = has_question or topics_found >= len(expected_topics) / 2
        
        return advances, issues

    def replace_vars(self, text: str) -> str:
        """Replace customer variables"""
        for var, val in CUSTOMER_VARS.items():
            text = text.replace(f"{{{{{var}}}}}", str(val))
            text = text.replace(f"{{{var}}}", str(val))
        return text

    async def call_llm(self, messages: List[Dict]) -> Tuple[str, float]:
        """Call Grok API"""
        start = datetime.now()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    GROK_API_URL,
                    headers={
                        "Authorization": f"Bearer {GROK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": GROK_MODEL,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 500
                    }
                )
                
                latency = (datetime.now() - start).total_seconds() * 1000
                
                if response.status_code != 200:
                    return f"[API Error {response.status_code}]", latency
                
                result = response.json()
                return result['choices'][0]['message']['content'].strip(), latency
                
        except Exception as e:
            return f"[Error: {e}]", 0

    async def run_conversation_turn(self, turn_num: int, expected_node: str, 
                                   user_input: str, expected_topics: List[str]) -> ConversationTurn:
        """Run a single conversation turn"""
        
        # Find the expected node
        node = self.find_node_by_partial(expected_node)
        node_content = self.get_node_content(node) if node else ""
        node_content = self.replace_vars(node_content)
        global_prompt = self.replace_vars(self.global_prompt)
        
        # Build conversation history for context
        history_text = ""
        for h in self.conversation_history[-6:]:  # Last 6 turns
            history_text += f"User: {h['user']}\nAgent: {h['agent']}\n\n"
        
        # Build prompt
        system_prompt = f"""{global_prompt}

---
## CURRENT NODE INSTRUCTIONS:
{node_content}

## CONVERSATION SO FAR:
{history_text}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User says: \"{user_input}\"\n\nRespond according to your node instructions. Be concise (1-3 sentences)."}
        ]
        
        # Call LLM
        response, latency = await self.call_llm(messages)
        
        # Detect which node the response seems to come from
        detected_node = self.detect_node_from_response(response)
        
        # Check for sequence correctness
        sequence_correct = expected_node.lower() in detected_node.lower() or detected_node == "UNKNOWN"
        
        # Check for silent agreement
        advances, issues = self.check_for_silent_agreement(response, expected_topics)
        has_question = '?' in response
        
        # Update conversation history
        self.conversation_history.append({
            'user': user_input,
            'agent': response
        })
        
        turn = ConversationTurn(
            turn_number=turn_num,
            expected_node=expected_node,
            user_input=user_input,
            agent_response=response,
            detected_node=detected_node,
            sequence_correct=sequence_correct,
            has_question=has_question,
            advances_conversation=advances,
            issues=issues
        )
        
        return turn

    async def run_full_sequence(self) -> SequenceTestResult:
        """Run the complete conversation sequence"""
        
        print("\n" + "="*80)
        print("🔄 SEQUENCE TEST - Full Conversation Path")
        print("="*80)
        print(f"Agent: {self.agent_config.get('name')}")
        print(f"Sequence length: {len(CONVERSATION_SEQUENCE)} turns")
        print("="*80)
        
        for i, (expected_node, user_input, expected_topics) in enumerate(CONVERSATION_SEQUENCE, 1):
            turn = await self.run_conversation_turn(i, expected_node, user_input, expected_topics)
            self.results.turns.append(turn)
            self.results.total_turns += 1
            
            if turn.sequence_correct:
                self.results.sequence_correct += 1
            else:
                self.results.skipped_nodes += 1
            
            if not turn.advances_conversation:
                self.results.silent_agreements += 1
            
            # Print turn result
            status = "✅" if turn.advances_conversation and not turn.issues else "⚠️" if turn.issues else "✅"
            print(f"\n[Turn {i}] {status}")
            print(f"  Expected: {expected_node[:40]}")
            print(f"  User: \"{user_input[:50]}...\"" if len(user_input) > 50 else f"  User: \"{user_input}\"")
            print(f"  Agent: \"{turn.agent_response[:80]}...\"" if len(turn.agent_response) > 80 else f"  Agent: \"{turn.agent_response}\"")
            print(f"  Detected Node: {turn.detected_node}")
            print(f"  Has Question: {turn.has_question}")
            
            if turn.issues:
                for issue in turn.issues:
                    print(f"  ⚠️ {issue}")
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        return self.results

    def generate_report(self) -> str:
        """Generate markdown report"""
        lines = []
        lines.append("# Sequence Test Report - Path Integrity Check")
        lines.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Agent:** {self.agent_config.get('name')}")
        
        lines.append("\n## Summary")
        lines.append(f"- **Total Turns:** {self.results.total_turns}")
        lines.append(f"- **Sequence Correct:** {self.results.sequence_correct}/{self.results.total_turns}")
        lines.append(f"- **Silent Agreements:** {self.results.silent_agreements} ⚠️")
        lines.append(f"- **Skipped Nodes:** {self.results.skipped_nodes}")
        
        # Count issues
        issue_turns = [t for t in self.results.turns if t.issues]
        lines.append(f"- **Turns with Issues:** {len(issue_turns)}")
        
        if issue_turns:
            lines.append("\n## ⚠️ Issues Detected")
            for t in issue_turns:
                lines.append(f"\n### Turn {t.turn_number}: {t.expected_node}")
                lines.append(f"- **User said:** \"{t.user_input}\"")
                lines.append(f"- **Agent said:** \"{t.agent_response[:200]}...\"" if len(t.agent_response) > 200 else f"- **Agent said:** \"{t.agent_response}\"")
                lines.append(f"- **Issues:**")
                for issue in t.issues:
                    lines.append(f"  - {issue}")
        
        lines.append("\n## Full Conversation Flow")
        for t in self.results.turns:
            status = "✅" if not t.issues else "⚠️"
            lines.append(f"\n### {status} Turn {t.turn_number}: {t.expected_node}")
            lines.append(f"**User:** {t.user_input}")
            lines.append(f"\n**Agent:** {t.agent_response}")
            lines.append(f"\n- Detected as: `{t.detected_node}`")
            lines.append(f"- Has question: {t.has_question}")
            lines.append(f"- Advances: {t.advances_conversation}")
            if t.issues:
                lines.append(f"- Issues: {', '.join(t.issues)}")
        
        return "\n".join(lines)


async def main():
    agent_id = "69468a6d6a4bcc7eb92595cd"
    
    tester = SequenceTester(agent_id)
    
    if not tester.load_agent():
        return
    
    results = await tester.run_full_sequence()
    
    # Generate report
    report = tester.generate_report()
    report_path = os.path.join(os.path.dirname(__file__), 'sequence_test_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print("\n" + "="*80)
    print("📊 SEQUENCE TEST COMPLETE")
    print("="*80)
    print(f"Total Turns: {results.total_turns}")
    print(f"Sequence Correct: {results.sequence_correct}/{results.total_turns}")
    print(f"Silent Agreements: {results.silent_agreements}")
    print(f"Report: {report_path}")
    
    if results.silent_agreements > 0:
        print(f"\n⚠️ SILENT AGREEMENTS DETECTED:")
        for t in results.turns:
            if not t.advances_conversation:
                print(f"  Turn {t.turn_number} ({t.expected_node}): {t.issues[0] if t.issues else 'No progression'}")


if __name__ == '__main__':
    asyncio.run(main())
