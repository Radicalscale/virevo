"""
Test Knowledge Base feature with Jake agent
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
JAKE_AGENT_ID = "474917c1-4888-47b8-b76b-f11a18f19d39"

# Sample PDFs provided by user
PDF_URLS = [
    "https://customer-assets.emergentagent.com/job_jake-tts-fix/artifacts/5g72d8fc_dan%20in%20ippei%20and%20company%20info.pdf",
    "https://customer-assets.emergentagent.com/job_jake-tts-fix/artifacts/h4b1aw6j_Di%20RE%20Customer%20Avatar.pdf"
]

async def test_kb_upload():
    """Test uploading PDFs to Jake agent's KB"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"\n📚 Testing Knowledge Base with Jake Agent")
        print(f"Agent ID: {JAKE_AGENT_ID}\n")
        
        # Download and upload each PDF
        for i, pdf_url in enumerate(PDF_URLS, 1):
            print(f"📄 [{i}/{len(PDF_URLS)}] Processing: {pdf_url.split('/')[-1]}")
            
            try:
                # Download PDF
                print("   ⬇️  Downloading PDF...")
                pdf_response = await client.get(pdf_url)
                pdf_response.raise_for_status()
                pdf_content = pdf_response.content
                print(f"   ✅ Downloaded ({len(pdf_content)} bytes)")
                
                # Upload to KB
                print("   ⬆️  Uploading to KB...")
                filename = pdf_url.split('/')[-1].replace('%20', ' ')
                files = {'file': (filename, pdf_content, 'application/pdf')}
                
                upload_response = await client.post(
                    f"{BACKEND_URL}/api/agents/{JAKE_AGENT_ID}/kb/upload",
                    files=files
                )
                upload_response.raise_for_status()
                result = upload_response.json()
                print(f"   ✅ Uploaded successfully")
                print(f"      - KB Item ID: {result['id']}")
                print(f"      - Content Length: {result['content_length']} chars")
                print(f"      - File Size: {result['file_size']} bytes\n")
                
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
        
        # List all KB items
        print("📋 Listing all KB items for Jake agent:")
        try:
            list_response = await client.get(f"{BACKEND_URL}/api/agents/{JAKE_AGENT_ID}/kb")
            list_response.raise_for_status()
            kb_items = list_response.json()
            print(f"   Total KB items: {len(kb_items)}")
            for item in kb_items:
                print(f"   - {item['source_name']} ({item['content_length']} chars)")
        except Exception as e:
            print(f"   ❌ Error listing KB items: {e}")
        
        # Test message with KB context
        print("\n💬 Testing AI message with KB context:")
        test_message = "Tell me about Dan Klein and Ippei Kanehara's business model"
        print(f"   Question: {test_message}")
        
        try:
            message_response = await client.post(
                f"{BACKEND_URL}/api/agents/{JAKE_AGENT_ID}/process",
                json={"message": test_message, "history": []}
            )
            message_response.raise_for_status()
            result = message_response.json()
            print(f"   AI Response: {result['response'][:300]}...")
            print(f"   Latency: {result['latency']:.2f}s")
        except Exception as e:
            print(f"   ❌ Error processing message: {e}")

if __name__ == "__main__":
    asyncio.run(test_kb_upload())
