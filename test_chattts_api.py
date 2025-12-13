"""
Quick test to verify ChatTTS API works correctly
Run this first before starting the server
"""

import torch

try:
    print("=" * 60)
    print("Testing ChatTTS API")
    print("=" * 60)
    
    print("\n1. Importing ChatTTS...")
    import ChatTTS
    print("✅ Import successful")
    
    print("\n2. Initializing Chat...")
    chat = ChatTTS.Chat()
    print("✅ Chat object created")
    
    print("\n3. Loading models...")
    chat.load_models(compile=False)  # Use False for testing
    print("✅ Models loaded")
    
    print("\n4. Checking available methods...")
    methods = [method for method in dir(chat) if not method.startswith('_')]
    print(f"Available methods: {', '.join(methods[:10])}...")
    
    print("\n5. Testing sample_random_speaker...")
    rand_spk = chat.sample_random_speaker()
    print(f"✅ Speaker embedding generated: shape={rand_spk.shape if hasattr(rand_spk, 'shape') else 'N/A'}")
    
    print("\n6. Testing inference...")
    params_infer_code = ChatTTS.Chat.InferCodeParams(
        spk_emb=rand_spk,
        temperature=0.3,
    )
    
    wavs = chat.infer(
        ["Hello, this is a test."],
        params_infer_code=params_infer_code,
    )
    print(f"✅ Inference successful: generated {len(wavs)} audio(s)")
    
    if wavs and len(wavs) > 0:
        print(f"   Audio shape: {wavs[0].shape if hasattr(wavs[0], 'shape') else len(wavs[0])}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! ChatTTS is working correctly.")
    print("=" * 60)
    
except AttributeError as e:
    print(f"\n❌ API Error: {str(e)}")
    print("\nTrying alternative methods...")
    
    try:
        # Try load() instead of load_models()
        chat = ChatTTS.Chat()
        chat.load(compile=False)
        print("✅ Alternative: chat.load() works")
        
        # Check for alternative speaker methods
        if hasattr(chat, 'sample_random_speaker'):
            print("✅ sample_random_speaker() exists")
        elif hasattr(chat, 'get_random_speaker'):
            print("✅ Alternative: get_random_speaker() exists")
        else:
            print("❌ No speaker sampling method found")
            print(f"Available methods: {[m for m in dir(chat) if 'sample' in m.lower() or 'speaker' in m.lower()]}")
            
    except Exception as e2:
        print(f"❌ Alternative also failed: {str(e2)}")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
