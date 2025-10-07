import sounddevice
import numpy as np
import wave
import time
import os
import threading
from typing import List, Optional

SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_BLOCK_DURATION_MS = 100
ASSETS_DIR = "assets"
TEMP_AUDIO_FILENAME = os.path.join(ASSETS_DIR, "temp_axo_audio.wav")


class AudioManager:
    """
    Manages audio resources and prevents leaks.
    Handles audio stream lifecycle and cleanup.
    """

    def __init__(self):
        self.active_streams: List[sounddevice.InputStream] = []
        self._lock = threading.Lock()

    def create_stream(self, **kwargs) -> sounddevice.InputStream:
        """Create and track a new audio stream."""
        stream = sounddevice.InputStream(**kwargs)
        with self._lock:
            self.active_streams.append(stream)
        return stream

    def remove_stream(self, stream: sounddevice.InputStream):
        """Remove a stream from tracking."""
        with self._lock:
            if stream in self.active_streams:
                self.active_streams.remove(stream)

    def cleanup_all_streams(self):
        """Clean up all active streams."""
        with self._lock:
            streams_to_cleanup = self.active_streams.copy()
            self.active_streams.clear()

        for stream in streams_to_cleanup:
            try:
                if stream.active:
                    stream.stop()
                stream.close()
            except Exception as e:
                print(f"Error cleaning up audio stream: {e}")

    def get_active_stream_count(self) -> int:
        """Get count of currently active streams."""
        with self._lock:
            return len(self.active_streams)


# Global audio manager instance
audio_manager = AudioManager()

def get_audio_devices():
    """Returns a list of available audio input device names."""
    devices = sounddevice.query_devices()
    input_devices = ["Default"]
    for device in devices:
        if device['max_input_channels'] > 0:
            input_devices.append(device['name'])
    return input_devices

def audio_callback(app, indata, frames, time, status):
    if status: print(f"Audio callback status: {status}")
    if app.is_recording:
        app.audio_frames.append(indata.copy())
        MAX_EXPECTED_AMPLITUDE = 2000
        mean_abs_val = np.abs(indata).mean()
        app.current_normalized_amplitude = min(mean_abs_val / MAX_EXPECTED_AMPLITUDE, 1.0) if MAX_EXPECTED_AMPLITUDE > 0 else 0.0

        # Update modern UI audio bars if active
        if hasattr(app, 'modern_ui') and app.modern_ui is not None:
            app.modern_ui.update_audio_bars(app.current_normalized_amplitude)
    else:
        app.current_normalized_amplitude = 0.0
        # Reset modern UI audio bars if active
        if hasattr(app, 'modern_ui') and app.modern_ui is not None:
            app.modern_ui.update_audio_bars(0.0)

def start_audio_recording(app):
    if not app.model_loaded_event.is_set():
        print("ASR Model not ready."); app.current_state = "initial"; app._update_ui_elements(); return
    if app.is_recording: return
    print("Starting recording..."); app._play_sound_async("open.wav")
    app.audio_frames = []; app.current_normalized_amplitude = 0.0
    app.bar_current_heights = np.zeros(app.num_audio_bars)
    app.is_recording = True
    try:
        blocksize = int(SAMPLE_RATE * AUDIO_BLOCK_DURATION_MS / 1000)
        selected_device = app.config.get("audio_config", {}).get("device", "Default")

        device_to_use = None if selected_device == "Default" else selected_device
        print(f"Using audio device: {selected_device}")

        # Use audio manager to create and track stream
        app.audio_stream = audio_manager.create_stream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            callback=lambda indata, frames, time, status: audio_callback(app, indata, frames, time, status),
            blocksize=blocksize,
            device=device_to_use
        )
        app.audio_stream.start()
    except Exception as e:
        print(f"Error starting recording: {e}"); app.is_recording = False; app.current_state = "initial"; app._update_ui_elements()
        # Clean up stream if creation failed
        if hasattr(app, 'audio_stream') and app.audio_stream:
            try:
                audio_manager.remove_stream(app.audio_stream)
            except:
                pass

def stop_audio_recording_and_process(app):
    if not app.is_recording and not app.audio_frames:
        app.is_recording = False; app.current_normalized_amplitude = 0.0
        # Clean up stream using audio manager
        if hasattr(app, 'audio_stream') and app.audio_stream:
            audio_manager.remove_stream(app.audio_stream)
            try:
                if app.audio_stream.active:
                    app.audio_stream.stop()
                app.audio_stream.close()
            except Exception as e:
                print(f"Error stopping/closing stream on no-op: {e}")
        app.audio_stream = None; app.master.after(0, app._safe_ui_update_to_initial); return

    print("Stopping recording..."); app.is_recording = False; app.current_normalized_amplitude = 0.0
    if hasattr(app, 'audio_stream') and app.audio_stream:
        # Remove from audio manager and clean up
        audio_manager.remove_stream(app.audio_stream)
        try:
            if app.audio_stream.active:
                app.audio_stream.stop()
            app.audio_stream.close()
        except Exception as e:
            print(f"Error stopping/closing audio stream: {e}")
        app.audio_stream = None
    time.sleep(0.05 + (AUDIO_BLOCK_DURATION_MS / 1000))
    if not app.audio_frames:
        print("No audio recorded."); app.master.after(0, app._safe_ui_update_to_initial); return
    frames_to_send = list(app.audio_frames); app.audio_frames = []

    # This was originally a direct call to a threaded method.
    # To decouple, we'll call a method on the app instance that will then start the thread.
    app.start_transcription_thread(frames_to_send) 