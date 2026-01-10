"""
Dead Air Prevention Monitor
Handles background monitoring of silence and triggers check-ins when needed.
"""
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


async def monitor_dead_air(session, websocket, call_control_id, stream_sentence_callback, telnyx_service, redis_service):
    """
    SIMPLE dead air monitoring:
    1. Start silence timer when AI finishes speaking
    2. Reset timer when user starts speaking
    3. Send check-in if silence exceeds threshold AND nobody is speaking
    
    Args:
        session: CallSession instance
        websocket: WebSocket connection to send messages
        call_control_id: Telnyx call control ID  
        stream_sentence_callback: Callback to stream check-in message to TTS
        telnyx_service: TelnyxService instance to hangup call
        redis_service: RedisService instance for multi-worker coordination
    """
    logger.info(f"🔇 Dead air monitoring started for call {call_control_id}")
    
    try:
        # NOTE: In single-worker mode, silence tracking is started by the webhook handler
        # when it detects all playbacks have finished. This monitor just checks if
        # check-ins should be sent based on the silence duration.
        
        while session.is_active:
            
            # Check max call duration
            if session.should_end_call_max_duration():
                logger.warning(f"⏱️ Max call duration reached - hanging up call {call_control_id}")
                session.should_end_call = True
                try:
                    await asyncio.sleep(1)
                    result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"📞 Call hung up - result: {result}")
                except Exception as e:
                    logger.error(f"❌ Error hanging up call: {e}")
                break
            
            # Check if we've waited long enough after max check-ins
            if session.should_end_call_max_checkins():
                logger.warning(f"🚫 Max check-ins + timeout reached - hanging up call {call_control_id}")
                session.should_end_call = True
                try:
                    await asyncio.sleep(1)
                    result = await telnyx_service.hangup_call(call_control_id)
                    logger.info(f"📞 Call hung up - result: {result}")
                except Exception as e:
                    logger.error(f"❌ Error hanging up call: {e}")
                break
            
            # Check for Redis flag from webhook handler (multi-worker fix)
            # If playback ended on a different worker, it sets this flag
            agent_done_flag = redis_service.get_flag(call_control_id, "agent_done_speaking")
            if agent_done_flag and session.agent_speaking:
                logger.info(f"🚩 Detected 'agent_done_speaking' flag from webhook - marking agent as done")
                session.mark_agent_speaking_end()
                redis_service.delete_flag(call_control_id, "agent_done_speaking")
            
            # 🔥 FIX: Skip monitoring if agent is processing/thinking
            # This prevents race conditions where agent logic is working but audio hasn't started
            if getattr(session, 'is_processing', False):
                if int(time.time()) % 5 == 0:
                    logger.info(f"🔇 MONITOR: Paused - agent is processing/thinking")
                await asyncio.sleep(0.5)
                continue
            
            # 🔥 FIX FOR WEBSOCKET STREAMING: Check playback_expected_end_time
            # With WebSocket audio streaming, we don't get media.playback.ended webhooks
            # So we need to check if the expected playback time has passed
            if session.agent_speaking:
                try:
                    from server import call_states, persistent_tts_manager
                    playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                    current_time = time.time()
                    
                    # Also check Redis playback count for multi-worker setup
                    playback_count = redis_service.get_playback_count(call_control_id)
                    
                    # 🔥 FIX: Also check if TTS is still generating a multi-sentence response
                    tts_session = persistent_tts_manager.get_session(call_control_id) if call_control_id else None
                    generation_in_progress = tts_session and not tts_session.generation_complete
                    
                    # 🔥 FIX: Also check if webhook is executing (e.g., waiting for booking confirmation)
                    # This prevents false "are you still there" triggers during webhook wait periods
                    executing_webhook = getattr(session, 'executing_webhook', False)
                    
                    # If playback time has passed AND no pending playbacks in Redis AND generation is complete AND not executing webhook
                    if playback_expected_end > 0 and current_time > playback_expected_end and playback_count == 0 and not generation_in_progress and not executing_webhook:
                        time_since_end = current_time - playback_expected_end
                        logger.info(f"⏱️ Playback expected end time passed ({time_since_end:.1f}s ago), marking agent as done speaking")
                        session.mark_agent_speaking_end()
                        # Clear the expected end time to prevent repeated triggers
                        call_states[call_control_id]["playback_expected_end_time"] = 0
                except Exception as e:
                    logger.debug(f"Could not check playback_expected_end_time: {e}")
            
            # 🔥 FIX: Don't count silence if audio is expected to still be playing
            # This prevents false "are you still there" triggers during playback
            try:
                from server import call_states, persistent_tts_manager
                
                # 🔥 FIX: Also check if TTS is still generating (multi-sentence response)
                # The generation_complete flag is False while sentences are still being generated
                tts_session = persistent_tts_manager.get_session(call_control_id) if call_control_id else None
                if tts_session:
                    # 🔥 FIX: Check if we are waiting for audio (precise state)
                    # This covers the "gap" between LLM done and audio start
                    if getattr(tts_session, 'is_waiting_for_first_audio_of_response', False):
                        if int(time.time()) % 5 == 0:
                            logger.info(f"🔇 MONITOR: Skipping silence check - waiting for first audio (precise state)")
                        await asyncio.sleep(0.5)
                        continue
                        
                    # Also check if generation is still in progress (multi-sentence)
                    if not tts_session.generation_complete:
                        # Agent is still generating/streaming a multi-sentence response
                        if int(time.time()) % 5 == 0:
                            logger.info(f"🔇 MONITOR: Skipping silence check - response generation still in progress")
                        await asyncio.sleep(0.5)
                        continue
                
                playback_expected_end = call_states.get(call_control_id, {}).get("playback_expected_end_time", 0)
                current_time = time.time()
                time_until_audio_done = playback_expected_end - current_time if playback_expected_end > 0 else 0
                
                if time_until_audio_done > 0.5:
                    # Audio is still expected to be playing - skip silence check
                    if int(time.time()) % 5 == 0:
                        logger.info(f"🔇 MONITOR: Skipping silence check - audio playing ({time_until_audio_done:.1f}s left)")
                    await asyncio.sleep(0.5)
                    continue
            except Exception as e:
                logger.debug(f"Could not check playback_expected_end_time for silence: {e}")
            
            # SIMPLE CHECK-IN LOGIC: 
            # Only send if BOTH agent and user are NOT speaking
            # AND not executing a webhook (webhooks may take time)
            silence_duration = session.get_silence_duration()
            
            # Skip dead air check if webhook is executing
            if getattr(session, 'executing_webhook', False):
                if int(time.time()) % 10 == 0:
                    logger.info(f"🔇 MONITOR: Paused - webhook executing for call {call_control_id}")
                await asyncio.sleep(0.5)
                continue
            
            # Diagnostic logging every 10 seconds to track state
            if int(time.time()) % 10 == 0:
                settings = session.agent_config.get("settings", {}).get("dead_air_settings", {})
                max_checkins = settings.get("max_checkins_before_disconnect", 2)
                logger.info(f"🔍 MONITOR: agent_speaking={session.agent_speaking}, user_speaking={session.user_speaking}, silence={silence_duration:.1f}s, checkin_count={session.checkin_count}/{max_checkins}")
            
            if not session.agent_speaking and not session.user_speaking:
                if session.should_checkin():
                    # Double-check playbacks are done before sending check-in
                    playback_count = redis_service.get_playback_count(call_control_id)
                    if playback_count == 0:
                        checkin_msg = session.get_checkin_message()
                        logger.info(f"💬 Sending check-in after {silence_duration:.1f}s silence: {checkin_msg}")
                        
                        # Mark agent as speaking
                        session.mark_agent_speaking_start()
                        
                        # Stream the check-in message
                        if stream_sentence_callback:
                            try:
                                await stream_sentence_callback(checkin_msg)
                                logger.info(f"✅ Check-in message sent")
                            except Exception as e:
                                logger.error(f"❌ Error sending check-in: {e}")
            
            # Check every 500ms
            await asyncio.sleep(0.5)
            
    except asyncio.CancelledError:
        logger.info(f"🔇 Dead air monitoring cancelled for call {call_control_id}")
    except Exception as e:
        logger.error(f"❌ Error in dead air monitoring: {e}")
    finally:
        logger.info(f"🔇 Dead air monitoring stopped for call {call_control_id}")
