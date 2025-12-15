
import sys
import wave
import struct

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.io import wavfile
    print("LIBRARIES_AVAILABLE")
except ImportError as e:
    print(f"MISSING_LIBRARY: {e}")
    sys.exit(1)

def create_spectrogram(wav_file, output_file):
    try:
        sample_rate, samples = wavfile.read(wav_file)
        
        # If stereo, take one channel
        if len(samples.shape) > 1:
            samples = samples[:, 0]
            
        plt.figure(figsize=(12, 6))
        
        # Create spectrogram
        # NFFT is the number of data points used in each block for the DFT.
        # Fs is the sampling frequency.
        plt.specgram(samples, NFFT=1024, Fs=sample_rate, noverlap=900, cmap='inferno')
        
        plt.title(f'Spectrogram of {wav_file}')
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.colorbar(label='Intensity [dB]')
        
        # Save
        plt.tight_layout()
        plt.savefig(output_file)
        print(f"Spectrogram saved to {output_file}")
        
    except Exception as e:
        print(f"Error creating spectrogram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_spectrogram('recording_analysis.wav', 'spectrogram.png')
