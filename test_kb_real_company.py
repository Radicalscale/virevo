"""
REAL KB TEST - Testing with ACTUAL company info from the PDF
Tests 10 specific facts from the document
"""
import asyncio
import sys
import os

sys.path.insert(0, '/app/backend')

from calling_service import CallSession

# REAL company info from the PDF
REAL_KB_CONTENT = """
The Klein-Kanehara Partnership - Company Information

Company Names: The Klein-Kanehara Partnership, Lead Generation Enterprise, JK program (formerly JobKilling), Snapps.ai

Founders: Dan Klein and Ippei Kanehara

Company History:
- Dan Klein: Coaching since 2014, over a decade of operation
- Ippei Kanehara: Discovered lead generation in 2014, partnered with Dan in 2018
- Operational for over a decade

What They Do:
- Local lead generation coaching
- Teaching students to build and rank websites for local businesses
- Creating "digital properties" that generate recurring income
- Developing Snapps.ai (AI-powered website builder)
- Operating Ippei.com blog (generates six-figure monthly revenue)

Founders Details:

Dan Klein ("The OG Lead Gen Coach"):
- Net worth: $30 million
- Made $30 million from PPE sales during COVID-19
- 15+ years business experience
- Started coaching in 2014
- 8-figure serial entrepreneur
- Previous ventures: window tinting, coupon business, real estate, Dutch Bros Coffee franchise

Ippei Kanehara:
- Net worth: $5 million
- Former student of Dan Klein
- Michigan State University graduate (advertising degree)
- Worked at Japanese automotive car parts company
- Monthly income from lead gen properties: >$50,000
- Ippei.com blog revenue: $100,000+ monthly
- Relocated to Folsom, Sacramento, California in 2019

Business Details:
- Student base: 7,200 - 7,500+ students
- Coaching program cost: $5,000 - $9,000+
- High-ticket offering
- Estimated lifetime gross revenue: $36M - $67.5M+
- Profit margins: 90-95%
- Annual live events in Las Vegas
- 5 Done-For-You websites provided to new students

Location: Folsom, Sacramento, California

Products/Programs:
- Lead Generation Coaching Program
- JK program (formerly "JobKilling")
- Snapps.ai (AI-powered website builder)
- Ippei.com (blog and content platform)
- "Digital real estate" concept
- "Link circles" for backlinks

Contact:
- Ippei.com
- Snapps.ai
"""

async def test_real_kb():
    """Test with 10 specific facts from the REAL company KB"""
    print("="*80)
    print("🧪 TESTING WITH REAL COMPANY INFO FROM PDF")
    print("="*80)
    
    # Create agent config
    agent_config = {
        "name": "Test Jake Agent",
        "agent_type": "call_flow",
        "system_prompt": "You are Jake, a sales representative.",
        "model": "grok-4-fast-non-reasoning",
        "settings": {
            "llm_provider": "grok",
            "model": "grok-4-fast-non-reasoning"
        }
    }
    
    # Format KB like the actual system
    kb_header = f"""### KNOWLEDGE BASE SOURCE 1: dan in ippei and company info.pdf
**Purpose/Contains:** Company information about the Klein-Kanehara Partnership
**Use this source when:** questions match the content described above

"""
    knowledge_base = "\n" + "="*80 + "\n" + kb_header + REAL_KB_CONTENT + "\n"
    
    print(f"\n1. 📚 Created KB with REAL company info:")
    print(f"   - Size: {len(knowledge_base)} chars")
    print(f"   - Actual company: Klein-Kanehara Partnership (JK program)")
    
    # Create session
    call_id = "test_real_kb"
    session = CallSession(call_id, agent_config, agent_id="test_agent", knowledge_base=knowledge_base)
    
    print(f"\n2. 🧪 Testing 10 Specific Facts from PDF:\n")
    
    # 10 test questions with expected answers
    tests = [
        {
            "num": 1,
            "question": "What is your company name?",
            "expected": "Klein-Kanehara Partnership OR JK program OR Lead Generation Enterprise",
            "keywords": ["klein", "kanehara", "jk", "lead generation enterprise"],
            "should_not_contain": ["digital growth partners", "site stack"]
        },
        {
            "num": 2,
            "question": "Who are the founders?",
            "expected": "Dan Klein and Ippei Kanehara",
            "keywords": ["dan klein", "ippei kanehara"],
            "should_not_contain": []
        },
        {
            "num": 3,
            "question": "How long has the company been in business?",
            "expected": "Over a decade / Since 2014",
            "keywords": ["decade", "2014"],
            "should_not_contain": ["2019", "5 years"]
        },
        {
            "num": 4,
            "question": "What is Dan Klein's net worth?",
            "expected": "$30 million",
            "keywords": ["30 million", "$30"],
            "should_not_contain": ["5 million", "10 million"]
        },
        {
            "num": 5,
            "question": "What is Ippei Kanehara's net worth?",
            "expected": "$5 million",
            "keywords": ["5 million", "$5"],
            "should_not_contain": ["30 million"]
        },
        {
            "num": 6,
            "question": "Where is the company located?",
            "expected": "Folsom, Sacramento, California",
            "keywords": ["folsom", "sacramento", "california"],
            "should_not_contain": ["austin", "texas"]
        },
        {
            "num": 7,
            "question": "How much does your coaching program cost?",
            "expected": "$5,000 to $9,000+",
            "keywords": ["5000", "9000", "$5", "$9"],
            "should_not_contain": ["$500", "$99", "free"]
        },
        {
            "num": 8,
            "question": "How many students do you have?",
            "expected": "7,200 to 7,500+ students",
            "keywords": ["7200", "7500", "7,", "over 7"],
            "should_not_contain": ["100", "500", "1000"]
        },
        {
            "num": 9,
            "question": "What is Snapps.ai?",
            "expected": "AI-powered website builder",
            "keywords": ["snapps", "ai", "website builder", "platform"],
            "should_not_contain": []
        },
        {
            "num": 10,
            "question": "Where are your annual events held?",
            "expected": "Las Vegas",
            "keywords": ["las vegas", "vegas"],
            "should_not_contain": ["austin", "california", "online"]
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n{'='*80}")
        print(f"TEST #{test['num']}: {test['question']}")
        print(f"Expected: {test['expected']}")
        print("-" * 80)
        
        try:
            # Add question to conversation
            session.conversation_history = [
                {"role": "assistant", "content": "Hi, this is Jake calling."},
                {"role": "user", "content": test['question']}
            ]
            
            # Get response
            response = await session._generate_ai_response_streaming(
                content=f"The user asked: '{test['question']}'. Answer using information from your knowledge base.",
                stream_callback=None
            )
            
            print(f"Response: {response}")
            print("-" * 80)
            
            # Check if response contains expected keywords
            response_lower = response.lower()
            found_keywords = [kw for kw in test['keywords'] if kw in response_lower]
            bad_keywords = [kw for kw in test['should_not_contain'] if kw in response_lower]
            
            if found_keywords and not bad_keywords:
                print(f"✅ PASS - Found expected keywords: {found_keywords}")
                passed += 1
            elif bad_keywords:
                print(f"❌ FAIL - Found forbidden keywords: {bad_keywords}")
                failed += 1
            else:
                print(f"❌ FAIL - Did not find any expected keywords from: {test['keywords']}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
        
        # Brief pause between requests
        await asyncio.sleep(0.5)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"📊 FINAL TEST RESULTS:")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}/10")
    print(f"❌ Failed: {failed}/10")
    print(f"Success Rate: {(passed/10)*100:.0f}%")
    
    if passed >= 8:
        print(f"\n🎉 EXCELLENT - KB system is working well!")
        print(f"   The agent is correctly using company information from the KB.")
    elif passed >= 6:
        print(f"\n⚠️  GOOD BUT NEEDS IMPROVEMENT - Most tests passed")
        print(f"   Some information may not be retrieved accurately.")
    else:
        print(f"\n❌ POOR - KB system not working correctly")
        print(f"   The agent is not reliably using KB information.")
    
    print(f"{'='*80}")
    
    await session.close()

if __name__ == "__main__":
    asyncio.run(test_real_kb())
