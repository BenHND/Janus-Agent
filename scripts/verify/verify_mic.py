import pyaudio
import numpy as np
import time

def test_mic():
    p = pyaudio.PyAudio()
    
    print("🎤 Testing Microphone...")
    print(f"Default Input Device Info:")
    try:
        info = p.get_default_input_device_info()
        print(f"  Name: {info['name']}")
        print(f"  Sample Rate: {info['defaultSampleRate']}")
        print(f"  Max Input Channels: {info['maxInputChannels']}")
    except Exception as e:
        print(f"  ❌ Error getting device info: {e}")
        return

    target_rate = int(info['defaultSampleRate']) # Use native rate
    chunk = 1024
    
    print(f"\n🎧 Attempting to open stream at {target_rate}Hz (Native)...")
    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=target_rate,
                        input=True,
                        frames_per_buffer=chunk)
        
        print("✅ Stream opened successfully.")
        print("🗣️  Please speak into the microphone for 3 seconds...")
        
        rms_values = []
        for i in range(0, int(target_rate / chunk * 3)):
            data = stream.read(chunk, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
            rms_values.append(rms)
            # Print a simple bar
            bars = "#" * int(rms / 100)
            print(f"\rLevel: {rms:.1f} {bars}", end="")
            
        print("\n")
        avg_rms = np.mean(rms_values)
        max_rms = np.max(rms_values)
        print(f"📊 Stats: Avg RMS={avg_rms:.1f}, Max RMS={max_rms:.1f}")
        
        if max_rms < 100:
            print("⚠️  WARNING: Signal is very low (Silence?). Check mic permissions/mute.")
        else:
            print("✅ Audio signal detected!")
            
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"\n❌ Failed to open stream at {target_rate}Hz: {e}")
        print("Try changing sample_rate in config.ini to 44100 or 48000 (though openWakeWord prefers 16000)")

    p.terminate()

if __name__ == "__main__":
    test_mic()
