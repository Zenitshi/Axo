import os
import threading

try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYDUB_AVAILABLE = True
except ImportError:
    print("pydub library not found. Audio cues will be disabled. Install with: pip install pydub simpleaudio Pillow")
    PYDUB_AVAILABLE = False
    def pydub_play(audio_segment):
        print(f"Audio cue: Would play an audio segment (pydub/backend not fully available)")

ASSETS_DIR = "assets"

def play_sound_async(sound_file_name_only):
    if not PYDUB_AVAILABLE: return
    sound_path = os.path.join(ASSETS_DIR, sound_file_name_only)
    if os.path.exists(sound_path):
        def play_it():
            try:
                sound = AudioSegment.from_file(sound_path, format="wav")
                louder_sound = sound + 15
                pydub_play(louder_sound)
            except Exception as e:
                print(f"Error playing sound {sound_path} with pydub: {e}")
        threading.Thread(target=play_it, daemon=True).start()
    else:
        print(f"Sound file not found: {sound_path}") 