
import sys
import os

# Add current directory to path so we can import backend
sys.path.append(os.getcwd())

from backend.soniox_service import clean_transcript

print("--- Testing Real clean_transcript from backend.soniox_service ---")

inputs = [
    ("10 0to 20 0,1 50 to 20 0grand.", "10 0to 20 0,1 50 to 20 0grand."), # Should not merge 10+to (remains split if not mergeable)
    ("10 0 to 20 0", "100 to 200"),   # 10 + 0 -> 100
    ("1 50 to 20 0 grand", "150 to 200 grand"), # 1+50 -> 150
    ("10 to 20 grand", "10 to 20 grand"), # 10 (digits) + to (no digits) -> NO MERGE
    ("I will be there at 10 to 5", "I will be there at 10 to 5"), # NO MERGE "10to"
    ("about 1 0 0 0 dol lar s", "about 1000 dollars"), # 1+0+0+0 -> 1000
    ("one", "one")
]

failures = 0
for inp, expected in inputs:
    cleaned = clean_transcript(inp)
    print(f"Input:    '{inp}'")
    print(f"Output:   '{cleaned}'")
    
    # Simple heuristic checks
    if inp == "about 1 0 0 0 dol lar s":
        if "1000" in cleaned:
             print("✅ Numeric merge PASSED (1000)")
        else:
             print("❌ Numeric merge FAILED (Expected 1000)")
             failures += 1
             
    if inp == "I will be there at 10 to 5":
        if "10 to" in cleaned:
            print("✅ Numeric separation PASSED (10 to)")
        else:
            print(f"❌ Numeric separation FAILED (Got '{cleaned}')")
            failures += 1
            
print(f"\nTotal Failures: {failures}")
