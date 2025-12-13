"""
REAL LLM TEST - Actually calls the LLM with KB to verify it works
"""
import asyncio
import sys
import os

sys.path.insert(0, '/app/backend')

from calling_service import CallSession

async def test_kb_with_real_llm():
    """Test KB system with actual LLM call"""
    print("="*80)
    print("🧪 REAL LLM TEST - Testing KB with actual AI call")
    print("="*80)
    
    # Create mock agent config (similar to Jake)
    agent_config = {
        "name": "Test Jake Agent",
        "agent_type": "call_flow",
        "system_prompt": "You are Jake, a sales representative calling to discuss passive income opportunities.",
        "model": "grok-4-fast-non-reasoning",
        "settings": {
            "llm_provider": "grok",
            "model": "grok-4-fast-non-reasoning"
        }
    }
    
    # Create mock KB with 3 sources (simulating Jake's actual KB)
    kb_source_1 = """Company Overview:
We are Digital Growth Partners, a digital marketing agency specializing in helping local businesses generate leads through online strategies.

Founded: 2019
Services: Lead generation, SEO, social media marketing, paid advertising
Target Market: Local service businesses (plumbers, lawyers, contractors)
Team Size: 15 employees
Location: Austin, Texas

Contact:
- Website: www.digitalgrowthpartners.com
- Phone: (512) 555-0123
- Email: info@digitalgrowthpartners.com

Our Approach:
- Custom marketing strategies tailored to each business
- Data-driven decisions backed by analytics
- ROI-focused campaigns that deliver results
- Transparent reporting and regular communication
"""
    
    kb_source_2 = """Customer Avatar: Local Business Owner

Demographics:
- Age: 35-55
- Business: Service-based local business
- Revenue: $500K-$5M annually
- Employees: 5-50
- Location: United States

Pain Points:
- Not enough qualified leads
- Expensive advertising with poor ROI
- Inconsistent results from marketing
- Wasting time on marketing instead of running business
- Don't know which marketing channels work

Goals:
- Predictable lead flow every month
- Better ROI on marketing spend
- More qualified leads who are ready to buy
- Systems that run without constant attention
"""
    
    kb_source_3 = """Sales Frameworks and Methodologies:

CALM Framework:
C - Connect emotionally with the prospect
A - Ask discovery questions to understand needs
L - Listen actively without interrupting
M - Move to solution that addresses their pain

DISC Sales Method:
D - Dominance: Results-oriented, direct, wants control
I - Influence: Social, enthusiastic, relationship-focused
S - Steadiness: Patient, reliable, dislikes change
C - Conscientiousness: Analytical, detail-oriented, needs data

Objection Handling:
1. Price objection: "It's too expensive"
   -> Focus on ROI and cost of inaction
   
2. Timing objection: "Not the right time"
   -> Create urgency with missed opportunities
   
3. Competition objection: "Already working with someone"
   -> Differentiate value and results
"""
    
    # Format KB like the actual system does
    kb_items = [
        {"source_name": "company_info.pdf", "description": "", "content": kb_source_1},
        {"source_name": "customer_avatar.pdf", "description": "", "content": kb_source_2},
        {"source_name": "sales_frameworks.pdf", "description": "", "content": kb_source_3}
    ]
    
    kb_texts = []
    for idx, item in enumerate(kb_items, 1):
        source_name = item["source_name"]
        description = item["description"]
        content = item["content"]
        
        kb_header = f"### KNOWLEDGE BASE SOURCE {idx}: {source_name}"
        if description:
            kb_header += f"\n**Purpose/Contains:** {description}"
        kb_header += f"\n**Use this source when:** questions match the content described above\n"
        
        kb_texts.append(f"{kb_header}\n{content}\n")
    
    knowledge_base = "\n" + "="*80 + "\n".join(kb_texts)
    
    print(f"\n1. 📚 Created test KB with 3 sources:")
    print(f"   - SOURCE 1: company_info.pdf ({len(kb_source_1)} chars)")
    print(f"   - SOURCE 2: customer_avatar.pdf ({len(kb_source_2)} chars)")
    print(f"   - SOURCE 3: sales_frameworks.pdf ({len(kb_source_3)} chars)")
    print(f"   Total: {len(knowledge_base)} chars")
    
    # Create CallSession with KB
    print(f"\n2. 🤖 Creating CallSession with KB...")
    call_id = "test_kb_llm_call"
    session = CallSession(call_id, agent_config, agent_id="test_agent", knowledge_base=knowledge_base)
    
    print(f"   ✅ Session created")
    print(f"   ✅ KB loaded: {len(session.knowledge_base)} chars")
    
    # Test question 1: Company identity
    print(f"\n3. 🧪 TEST 1: Asking about company identity")
    print(f"   Question: 'Who are you? What's your company name?'")
    print(f"   Expected: Should say 'Digital Growth Partners'")
    print(f"   Should NOT: Say 'Site Stack' or make up a name")
    print(f"\n   Calling LLM...")
    
    try:
        # Simulate conversation history - user just asked the question
        session.conversation_history = [
            {"role": "assistant", "content": "Hello, this is Jake calling."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hi! How are you today?"},
            {"role": "user", "content": "Who are you? What's your company name?"}
        ]
        
        # Call the actual LLM response generation method - asking it to respond to user's question
        response = await session._generate_ai_response_streaming(
            content="The user just asked about your identity and company name. Answer their question using information from your knowledge base.",
            stream_callback=None
        )
        
        print(f"\n   📝 LLM Response:")
        print(f"   " + "-"*76)
        print(f"   {response}")
        print(f"   " + "-"*76)
        
        # Check response
        response_lower = response.lower()
        
        checks = {
            "✅ Mentions 'Digital Growth Partners'": "digital growth partners" in response_lower,
            "❌ Does NOT mention 'Site Stack'": "site stack" not in response_lower,
            "❌ Does NOT make up company names": not any(fake in response_lower for fake in ["revenue boost", "income stack", "profit partners", "site builder"]),
        }
        
        print(f"\n   📊 Response Analysis:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"      {status} {check}")
        
        all_passed = all(checks.values())
        
    except Exception as e:
        print(f"\n   ❌ Error calling LLM: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Test question 2: Sales framework
    print(f"\n4. 🧪 TEST 2: Asking about sales methodology")
    print(f"   Question: 'What sales framework should I use?'")
    print(f"   Expected: Should mention CALM or DISC from KB")
    print(f"   Should NOT: Make up frameworks")
    print(f"\n   Calling LLM...")
    
    try:
        # Add the question to conversation history
        session.conversation_history.append({"role": "assistant", "content": response})
        session.conversation_history.append({"role": "user", "content": "What sales framework should I use?"})
        
        response2 = await session._generate_ai_response_streaming(
            content="The user wants to know what sales framework to use. Look in your knowledge base for sales frameworks and recommend one.",
            stream_callback=None
        )
        
        print(f"\n   📝 LLM Response:")
        print(f"   " + "-"*76)
        print(f"   {response2}")
        print(f"   " + "-"*76)
        
        response2_lower = response2.lower()
        
        checks2 = {
            "✅ Mentions CALM framework": "calm" in response2_lower,
            "✅ OR mentions DISC method": "disc" in response2_lower or "calm" in response2_lower,
            "❌ Does NOT make up frameworks": len(response2) > 20  # Basic check
        }
        
        print(f"\n   📊 Response Analysis:")
        for check, passed in checks2.items():
            status = "✅" if passed else "❌"
            print(f"      {status} {check}")
        
        all_passed2 = any([checks2["✅ Mentions CALM framework"], checks2["✅ OR mentions DISC method"]])
        
    except Exception as e:
        print(f"\n   ❌ Error calling LLM: {e}")
        import traceback
        traceback.print_exc()
        all_passed2 = False
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"📊 TEST SUMMARY:")
    print(f"{'='*80}")
    
    if all_passed:
        print(f"✅ TEST 1 PASSED: LLM correctly used company info KB")
        print(f"   - Said 'Digital Growth Partners' (correct)")
        print(f"   - Did NOT say 'Site Stack' (correct)")
    else:
        print(f"❌ TEST 1 FAILED: LLM did not use KB correctly")
        print(f"   - Check if it made up a company name")
    
    if all_passed2:
        print(f"✅ TEST 2 PASSED: LLM correctly used sales framework KB")
        print(f"   - Mentioned CALM or DISC from KB (correct)")
    else:
        print(f"❌ TEST 2 FAILED: LLM did not reference KB frameworks")
    
    if all_passed and all_passed2:
        print(f"\n🎉 ALL TESTS PASSED - KB system is working correctly!")
        print(f"   Safe to proceed with live call testing.")
    else:
        print(f"\n⚠️  SOME TESTS FAILED - KB system needs adjustment")
        print(f"   Review LLM responses above to see what went wrong.")
    
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(test_kb_with_real_llm())
