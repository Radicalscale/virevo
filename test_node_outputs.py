#!/usr/bin/env python3
"""
Node Output Tester - Expected vs Actual
=========================================
Tests each node in the call flow path by:
1. Sending the node's prompt + user input to the actual LLM
2. Comparing the actual output to expected behavior
3. Identifying deviations from the node's stated goal

Usage: python test_node_outputs.py
"""

import asyncio
import httpx
import json
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from pymongo import MongoClient
from bson import ObjectId

# Grok API Configuration
GROK_API_KEY = "xai-mDonAg7JKMuTnRm6k6NF9SxSNTrLpnENRyU5Y0CWzG82NBzKcr5y3eUGnC5Yxu7yZTRpG98ax2ZmE8GL"
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-4-fast-non-reasoning"

# MongoDB
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'

# Customer Profile
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
class TestCase:
    """A single test case for a node"""
    node_partial_label: str
    user_input: str
    expected_behavior: str  # What the node SHOULD do
    expected_keywords: List[str]  # Keywords that should appear
    forbidden_keywords: List[str] = field(default_factory=list)  # Keywords that should NOT appear


@dataclass 
class TestResult:
    """Result of testing a single node"""
    node_label: str
    node_id: str
    node_goal: str
    test_input: str
    expected: str
    actual_output: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    latency_ms: float = 0


# Test cases for the path from Deframe to Booking
TEST_CASES = [
    TestCase(
        node_partial_label="N003B_DeframeInitialObjection",
        user_input="Okay, tell me more about it",
        expected_behavior="Should acknowledge interest and introduce the lead gen model briefly, then ask a question to gauge curiosity",
        expected_keywords=["passive", "income", "?"],
        forbidden_keywords=["goodbye", "transfer", "supervisor"]
    ),
    TestCase(
        node_partial_label="N_IntroduceModel_And_AskQuestions",
        user_input="How does that work exactly?",
        expected_behavior="Should explain the passive income website model and ask what questions come to mind",
        expected_keywords=["website", "income", "questions"],
        forbidden_keywords=["price", "cost", "$"]
    ),
    TestCase(
        node_partial_label="N200_Super_WorkAndIncomeBackground",
        user_input="I work for a company",
        expected_behavior="Should acknowledge employment and ask about income",
        expected_keywords=["job", "yearly", "?"],
        forbidden_keywords=["sorry", "can't help"]
    ),
    TestCase(
        node_partial_label="N201A_Employed_AskYearlyIncome",
        user_input="About 36 thousand a year",
        expected_behavior="Should acknowledge income and transition to side hustle question",
        expected_keywords=["side hustle", "income", "?"],
        forbidden_keywords=["not enough", "too low"]
    ),
    TestCase(
        node_partial_label="N201B_Employed_AskSideHustle",
        user_input="Yes, I do some freelance work on the side",
        expected_behavior="Should acknowledge side hustle and ask about the amount",
        expected_keywords=["great", "month", "?"],
        forbidden_keywords=["no", "don't"]
    ),
    TestCase(
        node_partial_label="N201C_Employed_AskSideHustleAmount",
        user_input="About a thousand a month",
        expected_behavior="Should acknowledge and ask the vehicle question about generating similar income",
        expected_keywords=["1000", "income", "model"],
    ),
    TestCase(
        node_partial_label="N201D_Employed_AskVehicleQ",
        user_input="Yeah, I think that could work for me",
        expected_behavior="Should acknowledge positively and transition to capital question",
        expected_keywords=["generate", "income", "capital", "?"],
    ),
    TestCase(
        node_partial_label="N_AskCapital_5k",
        user_input="Yes, I have about 5 thousand available",
        expected_behavior="Should acknowledge capital availability and ask 'why now' question",
        expected_keywords=["great", "why", "now", "?"],
    ),
    TestCase(
        node_partial_label="N401_AskWhyNow",
        user_input="I'm looking for more financial freedom and passive income",
        expected_behavior="Should acknowledge motivation and compliment their clarity",
        expected_keywords=["appreciate", "refreshing", "why"],
    ),
    TestCase(
        node_partial_label="N402_Compliment_And_AskYouKnowWhy",
        user_input="No, why?",
        expected_behavior="Should deliver the identity affirmation about being serious",
        expected_keywords=["serious", "dreams", "commend"],
    ),
    TestCase(
        node_partial_label="N403_IdentityAffirmation",
        user_input="Yes, that sounds exactly like what I'm looking for",
        expected_behavior="Should propose setting up a deeper dive call",
        expected_keywords=["call", "deeper", "dive", "?"],
    ),
    TestCase(
        node_partial_label="N500A_ProposeDeeperDive",
        user_input="Sure, sounds good",
        expected_behavior="Should ask for timezone",
        expected_keywords=["timezone", "scheduling", "?"],
    ),
    TestCase(
        node_partial_label="N500B_AskTimezone",
        user_input="Eastern time",
        expected_behavior="Should acknowledge timezone and ask about availability/desk time",
        expected_keywords=["got it", "desk", "time", "?"],
    ),
    TestCase(
        node_partial_label="N_AskForCallbackRange",
        user_input="Afternoons work best, like 2 to 5",
        expected_behavior="Should ask for a specific time",
        expected_keywords=["specific", "time", "schedule", "?"],
    ),
    TestCase(
        node_partial_label="N_Scheduling_AskTime",
        user_input="Tuesday at 6 PM",
        expected_behavior="Should confirm the time and ask about Zoom capability",
        expected_keywords=["6", "PM", "confirm", "Zoom"],
    ),
    TestCase(
        node_partial_label="N_ConfirmVideoCallEnvironment",
        user_input="Yes, I'll be at my computer",
        expected_behavior="Should confirm and proceed with booking",
        expected_keywords=["great", "confirm", "Zoom"],
    ),
]


class NodeOutputTester:
    """Tests nodes by calling actual LLM and comparing outputs"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.client = MongoClient(MONGO_URL)
        self.db = self.client['test_database']
        self.agent_config = None
        self.nodes_by_label = {}
        self.results: List[TestResult] = []
        self.global_prompt = ""
        
    def load_agent(self) -> bool:
        """Load agent from MongoDB"""
        try:
            agent = self.db['agents'].find_one({'_id': ObjectId(self.agent_id)})
            if not agent:
                print(f"❌ Agent not found: {self.agent_id}")
                return False
            
            self.agent_config = agent
            self.global_prompt = agent.get('global_prompt', '') or agent.get('system_prompt', '')
            
            nodes = agent.get('call_flow', [])
            for node in nodes:
                data = node.get('data', {})
                label = data.get('label') or node.get('label') or ''
                if label:
                    self.nodes_by_label[label] = node
            
            print(f"✅ Loaded agent: {agent.get('name')}")
            print(f"   Nodes: {len(nodes)}")
            print(f"   Global prompt: {len(self.global_prompt)} chars")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def find_node(self, partial_label: str) -> Optional[Dict]:
        """Find node by partial label match"""
        for label, node in self.nodes_by_label.items():
            if partial_label.lower() in label.lower():
                return node
        return None
    
    def get_node_goal(self, node: Dict) -> str:
        """Extract node's goal"""
        data = node.get('data', {})
        goal = data.get('goal', '')
        if goal:
            return goal
        
        content = data.get('content', '') or data.get('script', '')
        if '## Primary Goal' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '## Primary Goal' in line and i + 1 < len(lines):
                    return lines[i + 1].strip()
        
        return "(No explicit goal)"

    def build_prompt(self, node: Dict, user_input: str) -> Tuple[str, str]:
        """Build system and user prompts for LLM call"""
        data = node.get('data', {})
        content = data.get('content', '') or data.get('script', '')
        mode = data.get('mode', 'prompt')
        
        # Replace variables
        for var, val in CUSTOMER_VARS.items():
            content = content.replace(f"{{{{{var}}}}}", str(val))
            content = content.replace(f"{{{var}}}", str(val))
            self.global_prompt = self.global_prompt.replace(f"{{{{{var}}}}}", str(val))
            self.global_prompt = self.global_prompt.replace(f"{{{var}}}", str(val))
        
        if mode == 'script':
            # Script mode - just return the script
            system_prompt = self.global_prompt
            user_prompt = f"Deliver this script naturally: {content}\n\nUser just said: {user_input}"
        else:
            # Prompt mode - use the node content as instructions
            system_prompt = f"{self.global_prompt}\n\n---\n\n## CURRENT NODE INSTRUCTIONS:\n{content}"
            user_prompt = f"User says: \"{user_input}\"\n\nRespond according to the node instructions above. Keep response natural and concise (1-3 sentences max)."
        
        return system_prompt, user_prompt

    async def call_llm(self, system_prompt: str, user_prompt: str) -> Tuple[str, float]:
        """Call Grok API and return response + latency"""
        start_time = datetime.now()
        
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
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 500
                    }
                )
                
                latency = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status_code != 200:
                    return f"[API Error: {response.status_code}]", latency
                
                result = response.json()
                output = result['choices'][0]['message']['content'].strip()
                return output, latency
                
        except Exception as e:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return f"[Error: {e}]", latency

    def analyze_output(self, test: TestCase, actual_output: str, goal: str) -> Tuple[bool, List[str]]:
        """Analyze if output matches expected behavior"""
        issues = []
        
        # Check expected keywords
        actual_lower = actual_output.lower()
        missing_keywords = []
        for kw in test.expected_keywords:
            if kw.lower() not in actual_lower:
                missing_keywords.append(kw)
        
        if missing_keywords:
            issues.append(f"Missing expected keywords: {missing_keywords}")
        
        # Check forbidden keywords
        found_forbidden = []
        for kw in test.forbidden_keywords:
            if kw.lower() in actual_lower:
                found_forbidden.append(kw)
        
        if found_forbidden:
            issues.append(f"Contains forbidden keywords: {found_forbidden}")
        
        # Check response quality
        if len(actual_output) < 15:
            issues.append("Response too short")
        
        if len(actual_output) > 800:
            issues.append("Response too long (verbose)")
        
        if actual_output.startswith("["):
            issues.append("Response appears to be an error")
        
        # Check if it ends with a question when expected
        if "?" in test.expected_keywords and "?" not in actual_output:
            issues.append("Expected a question but response doesn't ask one")
        
        passed = len(issues) == 0 or (len(issues) == 1 and "missing" in issues[0].lower() and len(missing_keywords) <= 1)
        
        return passed, issues

    async def test_node(self, test: TestCase) -> TestResult:
        """Test a single node"""
        node = self.find_node(test.node_partial_label)
        
        if not node:
            return TestResult(
                node_label=test.node_partial_label,
                node_id="NOT_FOUND",
                node_goal="N/A",
                test_input=test.user_input,
                expected=test.expected_behavior,
                actual_output="[Node not found]",
                passed=False,
                issues=["Node not found in agent"]
            )
        
        data = node.get('data', {})
        label = data.get('label') or test.node_partial_label
        node_id = str(node.get('id', ''))
        goal = self.get_node_goal(node)
        
        print(f"\n{'='*70}")
        print(f"📍 Testing: {label[:60]}")
        print(f"   Input: \"{test.user_input}\"")
        print(f"   Expected: {test.expected_behavior[:60]}...")
        
        # Build prompts and call LLM
        system_prompt, user_prompt = self.build_prompt(node, test.user_input)
        actual_output, latency = await self.call_llm(system_prompt, user_prompt)
        
        print(f"   Actual: \"{actual_output[:80]}...\"" if len(actual_output) > 80 else f"   Actual: \"{actual_output}\"")
        print(f"   Latency: {latency:.0f}ms")
        
        # Analyze
        passed, issues = self.analyze_output(test, actual_output, goal)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   Status: {status}")
        if issues:
            for issue in issues:
                print(f"   ⚠️ {issue}")
        
        return TestResult(
            node_label=label,
            node_id=node_id,
            node_goal=goal[:200],
            test_input=test.user_input,
            expected=test.expected_behavior,
            actual_output=actual_output,
            passed=passed,
            issues=issues,
            latency_ms=latency
        )

    async def run_all_tests(self) -> List[TestResult]:
        """Run all test cases"""
        print("\n" + "="*70)
        print("🧪 NODE OUTPUT TESTER - Expected vs Actual")
        print("="*70)
        print(f"Agent: {self.agent_config.get('name')}")
        print(f"Test cases: {len(TEST_CASES)}")
        print(f"LLM Model: {GROK_MODEL}")
        print("="*70)
        
        for test in TEST_CASES:
            result = await self.test_node(test)
            self.results.append(result)
            await asyncio.sleep(0.5)  # Rate limiting
        
        return self.results

    def generate_report(self) -> str:
        """Generate markdown report"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        lines = []
        lines.append("# Node Output Test Report")
        lines.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Agent:** {self.agent_config.get('name')}")
        lines.append(f"**LLM Model:** {GROK_MODEL}")
        
        lines.append("\n## Summary")
        lines.append(f"- **Total Tests:** {len(self.results)}")
        lines.append(f"- **Passed:** {passed} ✅")
        lines.append(f"- **Failed:** {failed} ❌")
        lines.append(f"- **Pass Rate:** {(passed/len(self.results)*100):.1f}%")
        
        avg_latency = sum(r.latency_ms for r in self.results) / len(self.results)
        lines.append(f"- **Avg Latency:** {avg_latency:.0f}ms")
        
        if failed > 0:
            lines.append("\n## ❌ Failed Tests")
            lines.append("\n| Node | Issue | Expected | Actual |")
            lines.append("|------|-------|----------|--------|")
            for r in self.results:
                if not r.passed:
                    issues_str = "; ".join(r.issues[:2])
                    lines.append(f"| {r.node_label[:25]} | {issues_str[:40]} | {r.expected[:30]}... | {r.actual_output[:30]}... |")
        
        lines.append("\n## Detailed Results")
        for i, r in enumerate(self.results, 1):
            status = "✅ PASS" if r.passed else "❌ FAIL"
            lines.append(f"\n### {i}. {status} {r.node_label}")
            lines.append(f"- **Goal:** {r.node_goal[:150]}...")
            lines.append(f"- **Input:** \"{r.test_input}\"")
            lines.append(f"- **Expected:** {r.expected}")
            lines.append(f"- **Actual Output:**")
            lines.append(f"```")
            lines.append(r.actual_output)
            lines.append(f"```")
            lines.append(f"- **Latency:** {r.latency_ms:.0f}ms")
            if r.issues:
                lines.append(f"- **Issues:**")
                for issue in r.issues:
                    lines.append(f"  - {issue}")
        
        return "\n".join(lines)


async def main():
    agent_id = "69468a6d6a4bcc7eb92595cd"
    
    tester = NodeOutputTester(agent_id)
    
    if not tester.load_agent():
        return
    
    results = await tester.run_all_tests()
    
    # Generate and save report
    report = tester.generate_report()
    report_path = os.path.join(os.path.dirname(__file__), 'node_output_test_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    print("\n" + "="*70)
    print("📊 TEST COMPLETE")
    print("="*70)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print(f"Pass Rate: {(passed/len(results)*100):.1f}%")
    print(f"Report: {report_path}")
    
    if failed > 0:
        print("\n⚠️ FAILED TESTS:")
        for r in results:
            if not r.passed:
                print(f"  - {r.node_label[:40]}: {r.issues[0] if r.issues else 'Unknown issue'}")


if __name__ == '__main__':
    asyncio.run(main())
