# Fix Attempt History: Double Speak & Barge-In Regression
A chronological record of attempted fixes and their specific failures in this session.

## Attempt 1: The "False Positive" Guard
*   **The Fix:** Modified `calling_service.py` to prevent the barge-in interceptor from triggering if the input was exactly equal to the silence marker `"..."`.
*   **The Theory:** The system was "hearing" its own silence timeout as user speech, causing it to interrupt itself.
*   **User Experience (Failure):** The agent continued to double-speak: "Kendrick? ... [User: Hello?] ... Kendrick?".
*   **Nature of Failure:** The fix was incomplete. The system sometimes generates an empty string `""` for silence, which wasn't caught by the `"..."` check.

## Attempt 2: The "Empty String" Edge Case
*   **The Fix:** Updated the check to include empty strings: `if user_text.strip() in ["...", "…", ""]`.
*   **The Theory:** Catching the empty string using `.strip()` would stop the false barge-in detection.
*   **User Experience (Failure):** The agent *still* double-spoke: "Kendrick? ... [User: Hello?] ... Kendrick?".
*   **Nature of Failure:** Paradoxically, the barge-in was now working "correctly" (detecting the user's "Hello?"), but the **response logic** was flawed. The code explicitly forced the agent to repeat the greeting (`return greeting_script`) whenever a barge-in occurred, regardless of what the user said.

## Attempt 3: Removing the "Force Feed" Logic
*   **The Fix:** Deleted the code block in `calling_service.py` that forced the agent to re-speak the greeting script upon interruption.
*   **The Theory:** By removing the forced repetition, the system would "fall through" to the standard LLM processing, allowing it to hear "Hello?" and respond naturally.
*   **User Experience (Failure):** The agent stopped double-speaking the name, but drifted off-script: "Kendrick? ... [User: Hello?] ... **Hey Kendrick, good to hear from you. Is that you on the line?**"
*   **Nature of Failure:** The agent treated the user's "Hello?" as the *very first* interaction.
    *   *Why?* The barge-in logic included a "safety" cleanup step: `conversation_history.pop()`.
    *   *Result:* It deleted the memory of asking "Kendrick?", so the LLM thought it hadn't greeted the user yet and generated a new, verbose greeting instead of moving to the next script step.

## Attempt 4: Preserving History
*   **The Fix:** Modified `calling_service.py` to **preserve** the silence greeting in history (`conversation_history.pop()` commented out).
*   **The Theory:** Keeping "Agent: Kendrick?" in history would give the LLM context that the greeting was done.
*   **User Experience (Partial Success):**
    *   *Barge-in behavior:* IMPROVED. Agent didn't re-greet when interrupted.
    *   *Late Response behavior:* **FAILED**. User waited, then said "Hello?". Agent responded: "Hey Kendrick, yeah it's me. You there?"
*   **Nature of Failure:** **Transition Logic Failure**.
    *   The LLM knew it asked "Kendrick?".
    *   The User answered "Hello?".
    *   The System attempted to match "Hello?" against the transition: `Confirms name (Yes|Speaking...)`.
    *   The LLM decided "Hello?" **did not match** "Confirms name".
    *   Result: It stayed on the "Greeting" node. The Greeting node's goal is "Confirm identity", so the LLM generated a *new* confirmation attempt ("Yeah it's me...").

## Attempt 5: The "Hello = Yes" Heuristic (Implemented)
*   **The Fix:** Injected a conditional instruction into the LLM's transition evaluation prompt. When the node is "Greeting", the prompt states: "Treat neutral greetings like 'Hello' as a positive confirmation."
*   **The Theory:** The LLM will read this instruction and match "Hello?" to the "Confirms name" transition.
*   **User Experience (Failure):** User said "Hello?" right after answering the call. Agent responded: "**Hey Kendrick, it's Jake here from JK. You there?**". This is not the expected Introduction → it's still a Greeting-style confirmation loop.
*   **Nature of Failure:** **LLM Ignored Heuristic**.
    *   The log shows `AI transition decision: '-1'` (L388 in `logs.1766829556502.log`).
    *   The node *was* "Greeting" (L242), so the heuristic block code *should* have run.
    *   **Root Cause:** The heuristic instruction was embedded in the `eval_prompt` body but the LLM's "Critical Rules" section (defining strict standards for matching) likely took precedence. The heuristic was placed **after** the "CRITICAL RULES" section, making it less impactful.

## Attempt 6: Hard-Coded Transition Override (Implemented & Redeployed)
*   **The Fix:** Added a hard check in `_follow_transition` to bypass LLM if `node="Greeting"` and `input="Hello"`.
*   **User Experience (Initial Failure):** "Ghost Code" scenario. Fix was committed but deployment stalled/failed.
*   **Action Taken:** Forced a fresh deployment by pushing commit `2f2f4082` with updated trace logs (`[DEPLOYMENT VERIFIED]`).
*   **Verification:** **FAILED**. Log analysis (`logs.1766986230758.log`) confirms the **new code is still NOT running**.
    *   Missing: `[DEPLOYMENT VERIFIED]` tag.
    *   Missing: `Checking 'Hello=Yes' override` log.
    *   **CRITICAL INSIGHT:** The logs *do* contain "Preserving silence greeting" (Attempt 4 Code).
    *   **Conclusion:** The deployment pipeline is **STUCK on Attempt 4**. No changes since Attempt 4 have successfully propagated to the production server. We are debugging a cache/deployment ghost.

## Attempt 7: Forced Rebuild (Cache Busting)
*   **The Fix:** Modified `Dockerfile`, `server.py`, and `calling_service.py` with cache-busting comments and ENV vars.
*   **Action:** User manually committed and pushed.
*   **Verification:** **FAILED**. Log analysis (`logs.1766987388309.log`) shows:
    *   Still NO `[DEPLOYMENT VERIFIED]` tag.
    *   Still NO `Checking 'Hello=Yes' override` log.
    *   Server is definitely running stale code.
*   **Conclusion:** The "Ghost Code" issue is severe. The deployment platform is likely ignoring the docker build context changes or pulling from a detached state.

## Attempt 8: Scorched Earth (File Renaming)
*   **Strategy:** Rename `backend/calling_service.py` to `backend/core_calling_service.py`.
*   **Rationale:** If the build system is caching `calling_service.py` by filename/checksum, changing the filename forces it to read the new file. It cannot serve a cached version of a file that didn't exist before.
*   **Plan:**
    1.  Rename `calling_service.py` -> `core_calling_service.py`.
    2.  Update imports in `server.py`.
    3.  Commit and Push.
*   **Verification:** **PARTIAL SUCCESS / NEW FAILURE**.
    *   **Deployment Confirmed:** Log shows `core_calling_service` in log messages (L177, L197, etc.). The renamed file IS NOW RUNNING.
    *   **Override NOT Reached:** The `Checking 'Hello=Yes' override [DEPLOYMENT VERIFIED]` log is MISSING.
    *   **Root Cause:** The override logic was in `_follow_transition()`, but the code path for the hard-coded override was NOT reached before the LLM evaluated the transition.
    *   **LLM Verdict:** The LLM returned `-1` for "Hello?" against the "Confirms name" transition (L388, L393-394).
    *   **Simultaneous Speech:** The "Kendrick?" TTS was still playing (0.98s latency, L380) when the LLM generated "Hey Kendrick, yeah it's me..." (L513-514). This caused overlapping speech.
*   **New Issue:** The "Hello = Yes" hard-coded override is NOT firing before the LLM call. The LLM is still the one deciding transitions.

## Attempt 9: Dual Fix (Override + TTS Cancellation)
*   **Analysis Method:** Cracking Creativity methodology applied to both issues.
*   **Bug 1 Root Cause:** `core_calling_service.py` L2145 used `current_node.get("name")` but nodes use `label` attribute. Override condition always evaluated to False.
*   **Bug 2 Root Cause:** `telnyx_service.py` L961-976 called `self.client.calls.actions.playback_stop()` which doesn't exist in the Telnyx SDK. Audio cancellation always failed.
*   **Fix 1:** Changed `get("name")` to `get("label")`.
*   **Fix 2:** Rewrote `stop_audio_playback()` to use REST API instead of non-existent SDK method.
*   **Verification:** **PARTIAL SUCCESS / NEW FAILURE**
    *   ✅ **Deployment SUCCESS** - Both fixes are running.
    *   ✅ **TTS Cancellation:** `Successfully stopped audio playback` (L356).
    *   ✅ **Override Check FIRED:** `Checking 'Hello=Yes' override [DEPLOYMENT VERIFIED] for msg='hell o'` (L370).
    *   ❌ **Override NOT TRIGGERED:** The cleaned message `'hell o'` (with space) does NOT match any trigger in `override_triggers`.
*   **Root Cause:** STT (Soniox) tokenized "Hello" as `["Hell", "o."]` (L306), resulting in final transcript `"Hell o."`. The override compares against `"hello"` (no space), so it fails.
*   **LLM Result:** Returned `-1` (L389), agent stayed on Greeting, generated "Hey Kendrick, yeah it's me. You there?" (L471-523).

## Attempt 10: Fuzzy Matching for Override
*   **Strategy:** Modify the override logic to handle tokenization artifacts:
    1.  Remove ALL spaces from the cleaned message before comparison: `cleaned_msg.replace(" ", "")`
    2.  This will convert `"hell o"` → `"hello"`, which matches `override_triggers`.
*   **Status:** Implemented.

## Attempt 11: Removing Simple Greetings from Override Triggers
*   **The Fix:** Removed "hello", "hi", "hey" from the `override_triggers` list. Added more explicit confirmation phrases like "yep", "uh huh", "that's me".
*   **The Theory:** Simple greetings should NOT trigger a transition. They should fall through to normal processing where `_skip_sticky_prevention` handles them.
*   **Verification:** Prevented premature transitions on simple greetings. However, exposed the "double-speak" issue.

## Attempt 12: Timestamp-Based Race Condition Detection
*   **The Fix:** Added `greeting_playback_started_at` and `user_spoke_at` timestamps. In `_follow_transition`, if `user_spoke_at < greeting_playback_started_at`, set `_skip_sticky_prevention` flag.
*   **The Theory:** User speaking BEFORE the audio even started should result in re-delivering the script, not LLM generation.
*   **Verification:** Successfully detected the race condition scenario.

## Attempt 13: Audio Transmission Buffer Window
*   **The Fix:** Added 2.0-second buffer to the timestamp comparison: `if user_spoke_at < playback_started + 2.0`.
*   **The Theory:** Account for TTS generation time, network latency, and phone buffering. User speaking within 2s of playback start likely hasn't heard the greeting.
*   **User Experience (Failure):** Agent cut off its own audio mid-playback ("Ken-") then re-spoke ("Kendrick?"). Functionally correct but sounds unnatural.
*   **Nature of Failure:** The Barge-In logic still triggers `stop_audio_playback()` immediately when user speaks. The buffer only affects the response logic, not the audio cancellation.

## Attempt 14: Smart Barge-In (Conditional Audio Stop)
*   **The Fix:** Modified `core_calling_service.py` Barge-In Interceptor to check timestamp before stopping audio. If user spoke within 2.5s of greeting start, skip the `stop_audio_playback()` call.
*   **The Theory:** Let the greeting finish playing naturally if the user spoke very early.
*   **User Experience (CRITICAL FAILURE):** Agent said **"Hello?"** instead of **"Kendrick?"** (the correct script).
*   **Nature of Failure:** **Python Scoping Bug**.
    *   The fix added `import time` INSIDE the try block (line 602).
    *   Python's scoping rules: If a variable is assigned (imported) anywhere in a function, it's treated as local throughout.
    *   Line 573 (`latency_start = time.time()`) references `time` BEFORE the local import.
    *   Python raises `cannot access local variable 'time' where it is not associated with a value`.
    *   The exception caused the processing flow to fail, resulting in a fallback that spoke "Hello?" instead of the script.
*   **Log Evidence:** `logs.1767069222660.log` Line 228: `core_calling_service - ERROR - Error processing user input: cannot access local variable 'time' where it is not associated with a value`

## Attempt 15: Removing Redundant `import time`
*   **The Fix:** Removed the `import time` statement from line 602. The `time` module is already imported at line 4 of the file.
*   **The Theory:** Using the existing top-level import avoids the scoping conflict.
*   **Status:** IMPLEMENTED. ✅

## Attempt 16: Double "Kendrick?" Audio Issue
*   **Log:** `logs.1767074561269.log`
*   **User Experience (Failure):** User heard TWO "Kendrick?" greetings at the start.
*   **Timeline Analysis:**
    1.  `06:02:10.096` - Silence timeout fires, generates greeting "Kendrick?"
    2.  `06:02:10.210` - TTS starts generating "Kendrick?" (line 278)
    3.  `06:02:10.434` - User says "Hello?" (`user_spoke_at = 1767074530.4340703`)
    4.  `06:02:10.544` - BARGE-IN DETECTED (line 335)
    5.  `06:02:10.993` - FIRST playback starts (`greeting_playback_started_at = 1767074530.9941165`, line 358-364)
    6.  `06:02:10.999` - Barge-in calls `stop_audio_playback` (line 366-368) - **AUDIO ALREADY PLAYING**
    7.  `06:02:11.014` - `_skip_sticky_prevention` logic fires (line 380-383)
    8.  `06:02:11.014` - Queues **SECOND** "Kendrick?" response (line 400-401)
*   **Root Cause:** **Race condition between TTS and script re-delivery.**
    *   The FIRST "Kendrick?" was already sent to Telnyx playback API BEFORE the barge-in `process_user_input` code ran.
    *   The barge-in tried to stop it, but the audio was already playing.
    *   Then `_skip_sticky_prevention` logic correctly identified user spoke early and queued the SECOND "Kendrick?".
    *   The first audio played (or mostly played before stop), then the second played.
*   **Nature of Failure:** The system doesn't know that the greeting was already (partially) delivered, so it delivers it again.

*   **Proposed Solution:** Track a `greeting_delivered` flag. Set it when the first "Kendrick?" TTS is queued. In `_skip_sticky_prevention` logic, check this flag:
    *   If `greeting_delivered = True` AND user spoke early: **DO NOT** re-deliver the script. Just process the user input normally or wait.
    *   This prevents the double-delivery.

## Attempt 16 Fix: Implemented but Incomplete ⚠️
*   **Location:** `core_calling_service.py` lines 1528-1561
*   **The Logic:**
    ```python
    if skip_sticky:
        # Check if greeting was ALREADY delivered
        if call_id and call_id in call_states:
            playback_started = call_states[call_id].get("greeting_playback_started_at", 0)
            if playback_started > 0:
                # Greeting already playing - don't re-deliver
                return ""  # Empty = no double-speak
        # Only deliver if greeting wasn't already sent
        if stream_callback:
            await stream_callback(content)
        return content
    ```
*   **Status:** INCOMPLETE - This fix was placed in the wrong code branch.

## Attempt 17: "Let me say that again" Root Cause Found ✅
*   **Log:** `logs.1767077922925.log`
*   **User Experience (Failure):** Agent says "Let me say that again - Kendrick?"
*   **Timeline Analysis:**
    1.  `06:58:12.122` - `dynamic_rephrase` detected as enabled (line 389)
    2.  `06:58:12.131` - LLM call for rephrase FAILS: `'GrokClient' object has no attribute 'chat'` (line 399)
    3.  `06:58:12.131` - **FALLBACK** kicks in: returns `"Let me say that again - {original_script}"` (line 4035)
    4.  Agent speaks the hardcoded fallback message
*   **Root Cause:** Two issues:
    1.  **Attempt 16 fix was in the wrong branch** - it was inside `else:` of `if dynamic_rephrase:`, so it never ran when dynamic rephrase was enabled
    2.  **GrokClient SDK incompatibility** - `_generate_rephrased_script()` uses OpenAI-style `client.chat.completions.create()` which doesn't work with GrokClient

*   **The Fix (Attempt 17):**
    1.  Move the "greeting already delivered" check **BEFORE** the `dynamic_rephrase` branch
    2.  If `skip_sticky=True` AND `greeting_playback_started_at > 0`, return empty immediately
    3.  This prevents BOTH dynamic rephrase AND direct re-delivery when greeting audio is already playing

*   **Location:** `core_calling_service.py` lines 1509-1571
*   **New Code Structure:**
    ```python
    if stayed_on_same_node and prompt_type == "script":
        # 🔥 ATTEMPT 17: FIRST check if greeting already delivered
        skip_sticky = selected_node.get("_skip_sticky_prevention", False)
        if skip_sticky:
            if greeting_playback_started_at > 0:
                return ""  # ← PREVENTS double-speak AND "Let me say that again"
            # Otherwise deliver original script
            return content
        
        # Normal case: user stayed on node after hearing greeting
        if dynamic_rephrase:
            # Rephrase script (with fallback if LLM fails)
            ...
        else:
            # Dead air prevention
            ...
    ```
*   **Status:** IMPLEMENTED. ✅ Awaiting testing.
