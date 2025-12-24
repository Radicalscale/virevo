
import re

inputs = [
    "10 0to 20 0,1 50 to 20 0grand.",
    "10 0 to 20 0",
    "1 50 to 20 0 grand",
    "10 to 20 grand"
]

def clean_transcript(text: str) -> str:
    # Original (simplified for test)
    if not text: return text
    text = re.sub(r'\s+', ' ', text).strip()
    standalone = {'a', 'i', 'the', 'and', 'for', 'are', 'but', 'not', 'you', 'to', 'of'} # Simplified set
    
    words = text.split()
    merged_words = []
    i = 0
    while i < len(words):
        current = words[i]
        # Original logic:
        if (len(current) <= 2 and 
            current.lower() not in standalone and 
            i + 1 < len(words)):
            next_word = words[i + 1]
            if (not any(c in current.lower() for c in 'aeiou') or
                len(current) == 1 and current.lower() not in {'a', 'i'}):
                merged_words.append(current + next_word)
                i += 2
                continue
        merged_words.append(current)
        i += 1
    return ' '.join(merged_words)

def clean_transcript_v2(text: str) -> str:
    # Fix with has_digits check
    if not text: return text
    text = re.sub(r'\s+', ' ', text).strip()
    standalone = {'a', 'i', 'the', 'and', 'for', 'are', 'but', 'not', 'you', 'to', 'of'} # Simplified set

    words = text.split()
    merged_words = []
    i = 0
    while i < len(words):
        current = words[i]
        
        # FIX: Check for digits
        has_digits = any(c.isdigit() for c in current)
        
        if (len(current) <= 2 and 
            not has_digits and   # <--- FIX
            current.lower() not in standalone and 
            i + 1 < len(words)):
            next_word = words[i + 1]
            if (not any(c in current.lower() for c in 'aeiou') or
                len(current) == 1 and current.lower() not in {'a', 'i'}):
                merged_words.append(current + next_word)
                i += 2
                continue
        merged_words.append(current)
        i += 1
    return ' '.join(merged_words)

print("--- Testing clean_transcript (Original) ---")
for inp in inputs:
    print(f"Input:  '{inp}'")
    print(f"Output: '{clean_transcript(inp)}'")
print("\n--- Testing clean_transcript_v2 (Fix) ---")
for inp in inputs:
    print(f"Input:  '{inp}'")
    print(f"Output: '{clean_transcript_v2(inp)}'")
