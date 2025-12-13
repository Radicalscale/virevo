# Remaining Tests Execution Plan

## Current Status
- **Completed**: 18 tests
- **In Progress**: Test 1.13 (Similarity Boost 1.0)
- **Remaining**: ~32 tests

## Priority Queue (Ordered by Category)

### 🎙️ ElevenLabs Settings (1 test remaining)
1. ✅ Test 1.9: Stability 0.5 (balanced) - **Ready to run**

### 🎧 Deepgram STT Settings (12 tests remaining)

**Endpointing Tests** (3 remaining):
2. Test 2.2: Endpointing 500ms (baseline)
3. Test 2.3: Endpointing 1000ms (needs retest - cache issue suspected)
4. Test 2.4: Endpointing 1500ms (very patient)

**Utterance End Tests** (4 tests):
5. Test 2.5: Utterance End 1ms (very quick)
6. Test 2.6: Utterance End 500ms (moderate)
7. Test 2.7: Utterance End 1000ms (baseline)
8. Test 2.8: Utterance End 2000ms (long)

**VAD Turnoff Tests** (3 tests):
9. Test 2.9: VAD Turnoff 100ms (quick)
10. Test 2.10: VAD Turnoff 250ms (baseline)
11. Test 2.11: VAD Turnoff 500ms (patient)

**Boolean Settings** (2 tests):
12. Test 2.12: Interim Results = false
13. Test 2.13: Smart Format = false

### 🎯 VAD Settings (10 tests remaining)

**Speech Sensitivity** (3 tests):
14. Test 3.1: Speech Sensitivity 10 (catches quiet sounds)
15. Test 3.2: Speech Sensitivity 20 (baseline)
16. Test 3.3: Speech Sensitivity 30 (only loud sounds)

**Silence Detection** (3 tests):
17. Test 3.4: Silence Detection 10 (sensitive)
18. Test 3.5: Silence Detection 16 (baseline)
19. Test 3.6: Silence Detection 25 (tolerant)

**Response Speed** (4 tests):
20. Test 3.7: Response Speed 100ms (very fast)
21. Test 3.8: Response Speed 200ms (baseline) - ✅ ALREADY TESTED
22. Test 3.9: Response Speed 500ms (moderate)
23. Test 3.10: Response Speed 800ms (patient) - ✅ ALREADY TESTED

### 🤖 LLM Provider & Model Testing (5 tests)

**OpenAI Models** (2 tests):
24. Test 4.1: GPT-4.1 (baseline) - Currently in use
25. Test 4.2: GPT-4 Turbo

**Grok Models** (3 tests):
26. Test 4.3: grok-4-fast-non-reasoning
27. Test 4.4: grok-4-fast-reasoning
28. Test 4.5: grok-2-1212

### ⚡ Combined Settings Stress Tests (3 tests)
29. Test 5.1: Ultra-fast setup - ✅ ALREADY TESTED
30. Test 5.2: Patient setup
31. Test 5.3: High quality voice

## Execution Strategy

### Batch 1: Complete ElevenLabs + Deepgram Endpointing (4 tests)
- Test 1.9: Stability 0.5
- Test 2.2: Endpointing 500ms
- Test 2.3: Endpointing 1000ms  
- Test 2.4: Endpointing 1500ms

### Batch 2: Deepgram Utterance End (4 tests)
- Tests 2.5-2.8

### Batch 3: Deepgram VAD Turnoff + Booleans (5 tests)
- Tests 2.9-2.13

### Batch 4: VAD Settings (6 tests, some already done)
- Tests 3.1-3.6 (skip 3.8 and 3.10 as done)

### Batch 5: LLM Models (5 tests)
- Tests 4.1-4.5

### Batch 6: Combined Stress Tests (2 remaining)
- Tests 5.2-5.3

## Notes
- Each test requires a phone call
- Agent config refresh now working, no need to delete/rebuild agents
- Tests can be run back-to-back with minimal delay
- User will confirm voice/behavior consistency during calls
