#!/usr/bin/env python3
"""
Comprehensive Latency Tester for Voice Agents
Tests multiple scenarios and tracks detailed metrics
"""

import asyncio
import httpx
import time
import json
import csv
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict
import statistics

# Configuration
MONGO_URL = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada'
DB_NAME = 'test_database'
BACKEND_URL = 'https://api.li-ai.org'

class LatencyTester:
    def __init__(self, agent_id: str, agent_name: str, user_id: str = None):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.user_id = user_id
        self.results = []
        self.session_id = None
        self.cookies = {}
        
    async def get_auth(self, db):
        """Get authentication from database"""
        # Get a recent session for auth
        sessions = await db.sessions.find().sort('_id', -1).limit(1).to_list(length=1)
        if sessions:
            session_id = sessions[0].get('session_id', '')
            self.cookies = {"session": session_id}
            print(f"✅ Using authentication")
            return True
        print("⚠️  No authentication found - tests may fail")
        return False
        
    async def start_session(self, http_client):
        """Start a new test session"""
        response = await http_client.post(
            f"{BACKEND_URL}/api/agents/{self.agent_id}/test/start",
            json={},
            cookies=self.cookies,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            self.session_id = data.get('session_id')
            print(f"✅ Session started: {self.session_id}")
            return True
        else:
            print(f"❌ Failed to start session: {response.status_code}")
            return False
    
    async def reset_session(self, http_client):
        """Reset session to start fresh"""
        if not self.session_id:
            return await self.start_session(http_client)
        
        response = await http_client.post(
            f"{BACKEND_URL}/api/agents/{self.agent_id}/test/reset",
            json={"session_id": self.session_id},
            cookies=self.cookies,
            timeout=30.0
        )
        
        if response.status_code == 200:
            print("✅ Session reset")
            return True
        else:
            print(f"⚠️  Reset failed, starting new session")
            return await self.start_session(http_client)
    
    async def send_message(self, http_client, message: str, scenario: str, measure_real_tts: bool = False) -> Dict:
        """Send a message and measure latency"""
        
        start_time = time.time()
        
        try:
            response = await http_client.post(
                f"{BACKEND_URL}/api/agents/{self.agent_id}/test/message",
                json={
                    "message": message,
                    "session_id": self.session_id,
                    "measure_real_tts": measure_real_tts
                },
                cookies=self.cookies,
                timeout=60.0
            )
            
            total_time = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    'scenario': scenario,
                    'message': message,
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'total_latency': total_time
                }
            
            data = response.json()
            detailed_timing = data.get('detailed_timing', {})
            
            result = {
                'scenario': scenario,
                'message': message,
                'success': True,
                'total_latency': total_time,
                'reported_latency': data.get('latency', 0),
                'llm_time': detailed_timing.get('llm_time', 0),
                'tts_time': detailed_timing.get('tts_time', 0),
                'tts_method': detailed_timing.get('tts_method', 'formula'),
                'ttfb': detailed_timing.get('ttfb'),
                'system_overhead': detailed_timing.get('system_overhead', 0),
                'calculated_total': detailed_timing.get('total_latency', 0),
                'current_node': data.get('current_node_label', 'Unknown'),
                'response_preview': data.get('agent_response', '')[:100],
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            return {
                'scenario': scenario,
                'message': message,
                'success': False,
                'error': str(e),
                'total_latency': time.time() - start_time
            }
    
    async def run_test_suite(self, http_client, measure_real_tts: bool = False):
        """Run comprehensive test suite"""
        
        print("=" * 80)
        print("COMPREHENSIVE LATENCY TEST SUITE")
        print("=" * 80)
        print(f"Agent: {self.agent_name}")
        print(f"Agent ID: {self.agent_id}")
        print(f"Real TTS Measurement: {'Enabled' if measure_real_tts else 'Disabled (using formula)'}")
        print("=" * 80)
        print()
        
        # Test Scenarios
        test_scenarios = [
            # Simple Transitions (5 tests)
            {
                'category': 'Simple Transitions',
                'tests': [
                    {'message': 'Yes', 'scenario': 'Name confirmation'},
                    {'message': 'Sure', 'scenario': 'Agreement'},
                    {'message': 'Okay', 'scenario': 'Basic acknowledgment'},
                    {'message': 'No', 'scenario': 'Rejection'},
                    {'message': 'Speaking', 'scenario': 'Identity confirmation'},
                ]
            },
            
            # KB Lookups (if applicable)
            {
                'category': 'KB Queries',
                'tests': [
                    {'message': 'What is this about?', 'scenario': 'General inquiry'},
                    {'message': 'How much does it cost?', 'scenario': 'Price question'},
                    {'message': 'Tell me more', 'scenario': 'Information request'},
                    {'message': 'Is this legit?', 'scenario': 'Legitimacy question'},
                    {'message': 'Who are you?', 'scenario': 'Identity question'},
                ]
            },
            
            # Complex Conditionals
            {
                'category': 'Complex Logic',
                'tests': [
                    {'message': 'Yes, but I have questions', 'scenario': 'Conditional agreement'},
                    {'message': 'I don\'t know', 'scenario': 'Uncertainty'},
                    {'message': 'Maybe later', 'scenario': 'Deferral'},
                    {'message': 'It depends', 'scenario': 'Conditional response'},
                    {'message': 'Not right now', 'scenario': 'Timing objection'},
                ]
            },
            
            # Dynamic Responses
            {
                'category': 'Dynamic Adaptation',
                'tests': [
                    {'message': 'Go ahead', 'scenario': 'Invitation to continue'},
                    {'message': 'I\'m busy', 'scenario': 'Time constraint'},
                    {'message': 'Call me back', 'scenario': 'Callback request'},
                    {'message': 'Not interested', 'scenario': 'Direct rejection'},
                    {'message': 'What\'s in it for me?', 'scenario': 'Value inquiry'},
                ]
            },
        ]
        
        # Run all tests
        for category_data in test_scenarios:
            category = category_data['category']
            tests = category_data['tests']
            
            print(f"\n{'='*80}")
            print(f"CATEGORY: {category}")
            print(f"{'='*80}\n")
            
            for i, test in enumerate(tests, 1):
                message = test['message']
                scenario = test['scenario']
                
                # Reset session for each test
                await self.reset_session(http_client)
                await asyncio.sleep(1)  # Brief pause
                
                print(f"Test {i}/{len(tests)}: {scenario}")
                print(f"  Message: \"{message}\"")
                
                result = await self.send_message(http_client, message, f"{category} - {scenario}", measure_real_tts)
                
                if result['success']:
                    print(f"  ✅ Success")
                    print(f"  Total Latency: {result['total_latency']:.3f}s")
                    print(f"  LLM Time: {result['llm_time']:.3f}s")
                    print(f"  TTS Time: {result['tts_time']:.3f}s ({result['tts_method']})")
                    if result['ttfb']:
                        print(f"  TTFB: {result['ttfb']:.3f}s")
                    print(f"  Current Node: {result['current_node']}")
                else:
                    print(f"  ❌ Failed: {result.get('error')}")
                
                print()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive report"""
        
        if not self.results:
            return {'error': 'No test results available'}
        
        # Filter successful results
        successful = [r for r in self.results if r['success']]
        
        if not successful:
            return {'error': 'No successful tests'}
        
        # Calculate statistics
        total_latencies = [r['total_latency'] for r in successful]
        llm_times = [r['llm_time'] for r in successful]
        tts_times = [r['tts_time'] for r in successful]
        
        # Group by category
        categories = {}
        for result in successful:
            category = result['scenario'].split(' - ')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result['total_latency'])
        
        report = {
            'agent_name': self.agent_name,
            'agent_id': self.agent_id,
            'test_date': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'successful_tests': len(successful),
            'failed_tests': len(self.results) - len(successful),
            
            'overall_metrics': {
                'average_latency': statistics.mean(total_latencies),
                'median_latency': statistics.median(total_latencies),
                'min_latency': min(total_latencies),
                'max_latency': max(total_latencies),
                'stdev_latency': statistics.stdev(total_latencies) if len(total_latencies) > 1 else 0,
            },
            
            'component_breakdown': {
                'average_llm_time': statistics.mean(llm_times),
                'average_tts_time': statistics.mean(tts_times),
                'llm_percentage': (statistics.mean(llm_times) / statistics.mean(total_latencies)) * 100,
                'tts_percentage': (statistics.mean(tts_times) / statistics.mean(total_latencies)) * 100,
            },
            
            'category_breakdown': {
                category: {
                    'average': statistics.mean(latencies),
                    'min': min(latencies),
                    'max': max(latencies),
                    'count': len(latencies)
                }
                for category, latencies in categories.items()
            },
            
            'target_comparison': {
                'target_latency': 1.5,
                'current_average': statistics.mean(total_latencies),
                'difference': statistics.mean(total_latencies) - 1.5,
                'percentage_over_target': ((statistics.mean(total_latencies) - 1.5) / 1.5) * 100,
                'meets_target': statistics.mean(total_latencies) <= 1.5
            }
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted report"""
        
        print("\n" + "=" * 80)
        print("LATENCY TEST REPORT")
        print("=" * 80)
        print(f"Agent: {report['agent_name']}")
        print(f"Date: {report['test_date']}")
        print(f"Tests: {report['successful_tests']}/{report['total_tests']} successful")
        print()
        
        print("OVERALL METRICS:")
        print("-" * 80)
        om = report['overall_metrics']
        print(f"  Average Latency: {om['average_latency']:.3f}s")
        print(f"  Median Latency:  {om['median_latency']:.3f}s")
        print(f"  Min Latency:     {om['min_latency']:.3f}s")
        print(f"  Max Latency:     {om['max_latency']:.3f}s")
        print(f"  Std Deviation:   {om['stdev_latency']:.3f}s")
        print()
        
        print("COMPONENT BREAKDOWN:")
        print("-" * 80)
        cb = report['component_breakdown']
        print(f"  Average LLM Time: {cb['average_llm_time']:.3f}s ({cb['llm_percentage']:.1f}%)")
        print(f"  Average TTS Time: {cb['average_tts_time']:.3f}s ({cb['tts_percentage']:.1f}%)")
        print()
        
        print("CATEGORY BREAKDOWN:")
        print("-" * 80)
        for category, metrics in report['category_breakdown'].items():
            print(f"  {category}:")
            print(f"    Average: {metrics['average']:.3f}s")
            print(f"    Range:   {metrics['min']:.3f}s - {metrics['max']:.3f}s")
            print(f"    Tests:   {metrics['count']}")
        print()
        
        print("TARGET COMPARISON:")
        print("-" * 80)
        tc = report['target_comparison']
        print(f"  Target:          {tc['target_latency']:.1f}s")
        print(f"  Current Average: {tc['current_average']:.3f}s")
        print(f"  Difference:      {tc['difference']:+.3f}s ({tc['percentage_over_target']:+.1f}%)")
        
        if tc['meets_target']:
            print(f"  Status:          ✅ TARGET MET!")
        else:
            print(f"  Status:          ❌ {tc['difference']:.3f}s over target")
        
        print("=" * 80)
        print()
    
    def export_csv(self, filename: str):
        """Export results to CSV"""
        
        if not self.results:
            print("No results to export")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"✅ Results exported to {filename}")
    
    def export_json(self, filename: str, report: Dict):
        """Export report to JSON"""
        
        export_data = {
            'report': report,
            'detailed_results': self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Report exported to {filename}")


async def main():
    """Main test execution"""
    
    # Agent to test
    AGENT_NAME = "JK First Caller-copy-copy"
    AGENT_ID = "f251b2d9-aa56-4872-ac66-9a28accd42bb"
    
    # Test configuration
    MEASURE_REAL_TTS = False  # Set to True for accurate TTS measurements
    
    # Connect to database for auth
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Create tester
    tester = LatencyTester(AGENT_ID, AGENT_NAME)
    
    # Get authentication
    await tester.get_auth(db)
    
    # Run tests
    async with httpx.AsyncClient() as http_client:
        # Start session
        await tester.start_session(http_client)
        
        # Run comprehensive test suite
        await tester.run_test_suite(http_client, measure_real_tts=MEASURE_REAL_TTS)
    
    client.close()
    
    # Generate and print report
    report = tester.generate_report()
    tester.print_report(report)
    
    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tester.export_csv(f"/app/latency_results_{timestamp}.csv")
    tester.export_json(f"/app/latency_report_{timestamp}.json", report)
    
    print("✅ Testing complete!")
    
    # Return report for iteration tracking
    return report


if __name__ == "__main__":
    report = asyncio.run(main())
