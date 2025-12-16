import pytest
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from natural_delivery_middleware import NaturalDeliveryMiddleware

class TestNaturalDeliveryMiddleware:
    def setup_method(self):
        self.middleware = NaturalDeliveryMiddleware()

    def test_strip_tags(self):
        text = "[H] Hello there!"
        clean_text, payload = self.middleware.process(text, model_id="eleven_flash_v2_5")
        assert clean_text == "Hello there!"

    def test_flash_strategy_happy(self):
        text = "[H] I am excited!"
        clean_text, payload = self.middleware.process(text, model_id="eleven_flash_v2_5")
        
        # Check settings for Happy (Lower stability)
        settings = payload["voice_settings"]
        assert settings["stability"] == 0.30
        assert settings["style"] == 0.75
        
        # Check clean text
        assert clean_text == "I am excited!"

    def test_flash_strategy_serious(self):
        text = "[S] This is serious."
        clean_text, payload = self.middleware.process(text, model_id="eleven_flash_v2_5")
        
        # Check settings for Serious (Higher stability)
        settings = payload["voice_settings"]
        assert settings["stability"] == 0.50
        
        # Check clean text
        assert clean_text == "This is serious."

    def test_turbo_strategy_ssml(self):
        text = "[H] Fast mode."
        clean_text, payload = self.middleware.process(text, model_id="eleven_turbo_v2_5")
        
        # Check SSML injection
        tts_text = payload["text"]
        assert '<prosody pitch="+10%" rate="105%">' in tts_text
        assert 'Fast mode.' in tts_text
        
        # Check settings (should be default/neutral for turbo usually, or specific if mapped)
        settings = payload["voice_settings"]
        assert settings["stability"] == 0.5 # Default for turbo in middleware

    def test_default_neutral(self):
        text = "Just normal text."
        clean_text, payload = self.middleware.process(text, model_id="eleven_flash_v2_5")
        
        # Should detect N (neutral) implicitly if no tag? 
        # Logic: if no tag, defaults to current_emotion (initially N) or stays N
        # Let's check implementation behavior
        settings = payload["voice_settings"]
        assert settings["stability"] == 0.40 # Neutral settings

    def test_pause_insertion_flash(self):
        text = "[N] One, two, three."
        clean_text, payload = self.middleware.process(text, model_id="eleven_flash_v2_5")
        
        # Check pause insertion for Flash
        tts_text = payload["text"]
        # Note: Implementation updated to 0.2s
        assert '<break time="0.2s"/>' in tts_text
