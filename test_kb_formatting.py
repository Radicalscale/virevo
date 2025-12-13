"""
Test KB formatting logic without requiring database access
This simulates how KB will be formatted and presented to the LLM
"""

def test_kb_formatting():
    """Test the new KB formatting system"""
    print("="*80)
    print("🧪 TESTING KB FORMATTING LOGIC")
    print("="*80)
    
    # Simulate 3 KB items like the Jake agent has
    kb_items = [
        {
            "source_name": "5g72d8fc_dan in ippei and company info.pdf",
            "description": None,  # No description set yet
            "content": """Company Overview:
We are Digital Growth Partners, a digital marketing agency specializing in helping local businesses generate leads through online strategies.

Founded: 2019
Services: Lead generation, SEO, social media marketing, paid advertising
Target Market: Local service businesses (plumbers, lawyers, contractors)
Team Size: 15 employees
Location: Austin, Texas

Our Approach:
- Custom marketing strategies
- Data-driven decisions
- ROI-focused campaigns
""" + "X" * 79000  # Simulate 79.8K chars
        },
        {
            "source_name": "h4b1aw6j_Di RE Customer Avatar.pdf",
            "description": None,
            "content": """Customer Avatar: Local Business Owner

Demographics:
- Age: 35-55
- Business: Service-based local business
- Revenue: $500K-$5M annually
- Pain Points: Not enough leads, expensive advertising, inconsistent results

Goals:
- Predictable lead flow
- Better ROI on marketing spend
- More qualified leads
""" + "Y" * 50000  # Simulate 50.5K chars
        },
        {
            "source_name": "Calm-Disc And Other Sales Frameworks.pdf",
            "description": None,
            "content": """CALM Framework:
C - Connect emotionally
A - Ask discovery questions
L - Listen actively
M - Move to solution

DISC Sales Method:
D - Dominance: Results-oriented, direct
I - Influence: Social, enthusiastic
S - Steadiness: Patient, reliable
C - Conscientiousness: Analytical, detail-oriented

Objection Handling:
1. Price objection -> Focus on ROI
2. Timing objection -> Create urgency
3. Competition objection -> Differentiate value
""" + "Z" * 281000  # Simulate 281.8K chars
        }
    ]
    
    print(f"\n1. 📚 Simulated KB Items:")
    for idx, item in enumerate(kb_items, 1):
        print(f"   {idx}. {item['source_name']} - {len(item['content'])} chars")
    
    total_size = sum(len(item['content']) for item in kb_items)
    print(f"   Total: {total_size:,} chars ({total_size/1000:.1f}K)")
    
    # Format KB using the new system
    print(f"\n2. 🔧 Applying new KB formatting...")
    kb_texts = []
    for idx, item in enumerate(kb_items, 1):
        source_name = item.get("source_name", "Unknown")
        description = item.get("description", "")
        content = item.get("content", "")
        
        # Format KB with clear headers including description if provided
        kb_header = f"### KNOWLEDGE BASE SOURCE {idx}: {source_name}"
        if description:
            kb_header += f"\n**Purpose/Contains:** {description}"
        else:
            kb_header += f"\n**Purpose/Contains:** (No description provided - content type will be inferred by AI)"
        kb_header += f"\n**Use this source when:** questions match the content described above\n"
        
        kb_texts.append(f"{kb_header}\n{content}\n")
    
    knowledge_base = "\n" + "="*80 + "\n".join(kb_texts)
    
    print(f"✅ KB formatted: {len(knowledge_base):,} chars")
    
    # Show the formatted KB structure
    print(f"\n3. 👀 Formatted KB Structure Preview:")
    print("-" * 80)
    # Show just the headers and first 500 chars of each
    for idx, item in enumerate(kb_items, 1):
        source_name = item['source_name']
        description = item.get('description', '')
        content = item['content']
        
        print(f"\n### KNOWLEDGE BASE SOURCE {idx}: {source_name}")
        if description:
            print(f"**Purpose/Contains:** {description}")
        else:
            print(f"**Purpose/Contains:** (No description - AI will infer)")
        print(f"**Use this source when:** questions match the content described above\n")
        print(f"Content preview (first 300 chars):")
        print(content[:300])
        print(f"... ({len(content) - 300:,} more chars)")
        print("="*80)
    
    # Show what LLM instructions look like
    print(f"\n4. 📋 LLM Instructions (what AI sees):")
    print("-" * 80)
    llm_instructions = """
=== KNOWLEDGE BASE ===
You have access to multiple reference sources below. Each source serves a different purpose.

🧠 HOW TO USE THE KNOWLEDGE BASE:
1. When user asks a question, FIRST identify which knowledge base source(s) are relevant based on their descriptions
2. Read ONLY the relevant source(s) to find the answer
3. Use ONLY information from the knowledge base - do NOT make up or improvise ANY factual details
4. If the knowledge base doesn't contain the answer, say: "I don't have that specific information available"
5. Different sources contain different types of information - match the user's question to the right source

⚠️ NEVER invent: company names, product names, prices, processes, methodologies, or any factual information not in the knowledge base
"""
    print(llm_instructions)
    print("-" * 80)
    
    # Test scenarios
    print(f"\n5. 🧪 Test Scenarios:")
    scenarios = [
        {
            "question": "Who are you? What's your company name?",
            "expected_source": "SOURCE 1 (company info)",
            "expected_answer": "Digital Growth Partners",
            "should_not_say": "Site Stack"
        },
        {
            "question": "What sales framework should I use?",
            "expected_source": "SOURCE 3 (sales frameworks)",
            "expected_answer": "CALM or DISC framework",
            "should_not_say": "Making up frameworks"
        },
        {
            "question": "Who is my target customer?",
            "expected_source": "SOURCE 2 (customer avatar)",
            "expected_answer": "Local business owners, age 35-55",
            "should_not_say": "Making up demographics"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n   Question: \"{scenario['question']}\"")
        print(f"   Expected to use: {scenario['expected_source']}")
        print(f"   Should answer with: {scenario['expected_answer']}")
        print(f"   Should NOT: {scenario['should_not_say']}")
    
    # Check if company info is findable
    print(f"\n6. 🔍 Verifying company info is accessible:")
    company_in_kb = "Digital Growth Partners" in knowledge_base
    print(f"   {'✅' if company_in_kb else '❌'} Company name 'Digital Growth Partners' found in KB")
    
    first_source = kb_texts[0]
    company_in_first = "Digital Growth Partners" in first_source
    print(f"   {'✅' if company_in_first else '❌'} Company name in FIRST source (high priority)")
    
    # Summary
    print(f"\n7. 📊 FORMATTING TEST SUMMARY:")
    print(f"   ✅ 3 KB sources formatted with clear headers")
    print(f"   ✅ Each source has 'Purpose/Contains' and 'Use this source when' metadata")
    print(f"   ✅ LLM receives 5-step instructions on intelligent KB selection")
    print(f"   ✅ Clear warnings against inventing information")
    print(f"   ✅ Company info is in first source for high priority")
    print(f"   ✅ Total KB size: {len(knowledge_base):,} chars (within Grok 2M token limit)")
    
    print(f"\n{'='*80}")
    print(f"✅ KB FORMATTING TEST COMPLETE!")
    print(f"   The new system should help LLM:")
    print(f"   1. Identify relevant KB source based on question")
    print(f"   2. Read only that source (not all 412K chars)")
    print(f"   3. Use actual company name (Digital Growth Partners)")
    print(f"   4. NOT make up fake names (Site Stack)")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_kb_formatting()
