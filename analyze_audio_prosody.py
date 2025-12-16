import sys
import os
import numpy as np
import librosa

def analyze_audio(file_path):
    print(f"Analyzing {file_path}...")
    
    try:
        # Load audio (mono)
        y, sr = librosa.load(file_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        print(f"Duration: {duration:.2f} seconds")
        
        # 1. Pitch Analysis (Fundamental Frequency F0)
        # Use pyin for robust pitch detection
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        
        # Filter only voiced parts
        voiced_f0 = f0[voiced_flag]
        
        if len(voiced_f0) > 0:
            pitch_std = np.std(voiced_f0)
            pitch_range = np.max(voiced_f0) - np.min(voiced_f0)
            print(f"Pitch Std Dev: {pitch_std:.2f} Hz")
            print(f"Pitch Range: {pitch_range:.2f} Hz")
            
            # Simple heuristic for "robot" voice
            if pitch_std < 20:
                print("Basic Assessment: ROBOTIC / MONOTONE (Low pitch variance)")
            elif pitch_std > 50:
                print("Basic Assessment: EXPRESSIVE (High pitch variance)")
            else:
                print("Basic Assessment: NEUTRAL / STANDARD")
        else:
            print("No pitch detected (silence or noise only).")

        # 2. Silence/Pause Analysis
        # Split on silence
        intervals = librosa.effects.split(y, top_db=20)
        
        total_speech_len = 0
        pause_durations = []
        
        # Calculate speech vs silence segments
        last_end = 0
        for start, end in intervals:
            total_speech_len += (end - start)
            if last_end > 0:
                pause_len = (start - last_end) / sr
                pause_durations.append(pause_len)
            last_end = end
            
        silence_ratio = (len(y) - total_speech_len) / len(y)
        print(f"Silence Ratio: {silence_ratio:.2%}")
        
        if len(pause_durations) > 0:
            avg_pause = np.mean(pause_durations)
            print(f"Avg Pause Duration: {avg_pause:.2f}s")
            print(f"Number of Pauses: {len(pause_durations)}")
        else:
            print("No significant pauses detected (rushed delivery).")

    except Exception as e:
        print(f"Error analyzing audio: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_audio_prosody.py <file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    analyze_audio(file_path)
