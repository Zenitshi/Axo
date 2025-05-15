import customtkinter as ctk
import tkinter as tk
import math
import threading
import time
import json
import os

import nemo.collections.asr as nemo_asr
import sounddevice
import numpy as np
import wave
import pyperclip
import pyautogui
from pynput import keyboard
from mistralai import Mistral

try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYDUB_AVAILABLE = True
except ImportError:
    print("pydub library not found. Audio cues will be disabled. Install with: pip install pydub simpleaudio")
    PYDUB_AVAILABLE = False
    def pydub_play(audio_segment):
        print(f"Audio cue: Would play an audio segment (pydub/backend not fully available)")

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"
TEMP_AUDIO_FILENAME = os.path.join("assets", "temp_axo_audio.wav")
SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_BLOCK_DURATION_MS = 100
CONFIG_FILE = "config.json"
class AxoApp:
    def __init__(self, app_window):
        self.master = app_window
        self.master.title("Axo")
        try:
            # Ensure 'Axo Icon.ico' is in the same directory as your script
            self.master.iconbitmap(os.path.join("assets", "Axo Icon.ico"))
        except tk.TclError:
            print("Icon 'Axo Icon.ico' not found or not supported. Skipping icon.")

        self.master.overrideredirect(True)
        self.master.attributes('-topmost', True)

        self.window_width = 220
        self.window_height = 60
        self.master.update_idletasks()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        offset_from_bottom = 30
        self.initial_pos_x = (screen_width // 2) - (self.window_width // 2)
        self.initial_pos_y = screen_height - self.window_height - offset_from_bottom
        self.master.geometry(f"{self.window_width}x{self.window_height}+{self.initial_pos_x}+{self.initial_pos_y}")

        self.transparent_color = "#1A1B1C"
        self.master.configure(fg_color=self.transparent_color)
        self.master.wm_attributes("-transparentcolor", self.transparent_color)

        self.current_state = "loading_model"
        self.animation_step = 0
        self.is_window_visible = True
        self.current_normalized_amplitude = 0.0
        self.num_audio_bars = 5
        self.bar_target_heights = np.zeros(self.num_audio_bars)
        self.bar_current_heights = np.zeros(self.num_audio_bars)

        self.config = self._load_config()
        self.mistral_api_key = self.config.get("api_keys", {}).get("mistral")
        self.gemini_api_key = self.config.get("api_keys", {}).get("gemini")
        self.mistral_client = None
        self._initialize_mistral_client()

        try:
            current_theme = ctk.ThemeManager.get_theme()
            self.accent_color = current_theme["CTkButton"]["fg_color"][1] if isinstance(current_theme["CTkButton"]["fg_color"], (list, tuple)) else current_theme["CTkButton"]["fg_color"]
            self.content_bg_color = current_theme["CTkFrame"]["fg_color"][1] if isinstance(current_theme["CTkFrame"]["fg_color"], (list, tuple)) else current_theme["CTkFrame"]["fg_color"]
            self.indicator_line_color = current_theme["CTkFrame"]["top_fg_color"][1] if isinstance(current_theme["CTkFrame"]["top_fg_color"], (list, tuple)) else current_theme["CTkFrame"]["top_fg_color"]
            if self.indicator_line_color == self.content_bg_color:
                 self.indicator_line_color = "#3D3D3D" if ctk.get_appearance_mode().lower() == "dark" else "#B0B0B0"
            self.animation_visual_color = current_theme["CTkLabel"]["text_color"][1] if isinstance(current_theme["CTkLabel"]["text_color"], (list, tuple)) else current_theme["CTkLabel"]["text_color"]
        except:
            self.accent_color = "#0078D4"
            self.content_bg_color = "#2B2B2B"
            self.indicator_line_color = "#4A4A4A"
            self.animation_visual_color = "#E0E0E0"

        self.main_content_frame = ctk.CTkFrame(self.master, fg_color=self.content_bg_color, corner_radius=12)
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        resolved_frame_bg = self.main_content_frame.cget("fg_color")
        self.drawing_canvas = tk.Canvas(self.main_content_frame, bg=resolved_frame_bg, highlightthickness=0)
        self.drawing_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._update_ui_elements()

        self.asr_model = None
        self.is_recording = False
        self.audio_frames = []
        self.audio_stream = None
        self.model_loaded_event = threading.Event()
        self.currently_pressed_keys = set()
        self.hotkey_trigger_key = keyboard.Key.space
        self.settings_hotkey_char = 'h'
        self.hotkey_active_for_release = False
        self.settings_window = None

        self.language_display_to_code = {"English": "en", "Arabic": "ar", "French": "fr", "Spanish": "es"}
        self.language_code_to_display = {v: k for k, v in self.language_display_to_code.items()}

        # --- Dragging Logic Variables ---
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        # --- Bind Dragging Events ---
        # Bind to both frame and canvas to ensure click is captured
        for widget_to_bind in [self.main_content_frame, self.drawing_canvas]:
            widget_to_bind.bind("<ButtonPress-1>", self._on_drag_start)
            widget_to_bind.bind("<B1-Motion>", self._on_drag_motion)

        print("Loading ASR model...")
        threading.Thread(target=self._load_asr_model, daemon=True).start()
        threading.Thread(target=self._start_keyboard_listener, daemon=True).start()

    # --- Dragging Methods ---
    def _on_drag_start(self, event):
        """Records the initial mouse offset relative to the widget clicked."""
        self._drag_offset_x = event.x
        self._drag_offset_y = event.y

    def _on_drag_motion(self, event):
        """Updates the window position while dragging."""
        # event.x_root and event.y_root are the mouse's absolute screen coordinates
        # Or use winfo_pointerx/y which are also screen coordinates
        x = self.master.winfo_pointerx() - self._drag_offset_x
        y = self.master.winfo_pointery() - self._drag_offset_y
        self.master.geometry(f"+{x}+{y}")

    def _initialize_mistral_client(self):
        text_processing_service = self.config.get("models_config", {}).get("text_processing_service")
        current_mistral_key = self.config.get("api_keys", {}).get("mistral")

        if text_processing_service == "Mistral" and current_mistral_key:
            if not self.mistral_client or self.mistral_client.api_key != current_mistral_key:
                try:
                    self.mistral_client = Mistral(api_key=current_mistral_key)
                    print("Mistral client initialized/re-initialized.")
                except Exception as e:
                    print(f"Error initializing Mistral client: {e}")
                    self.mistral_client = None
        else:
            if self.mistral_client:
                 print("Mistral service not selected or API key removed. De-initializing client.")
            self.mistral_client = None

    def _load_config(self):
        default_config = {
            "api_keys": {"mistral": "", "gemini": ""},
            "models_config": {
                "text_processing_service": "Mistral",
                "mistral_model_name": "mistral-medium-latest",
                "gemini_model_name": "gemini-2.0-flash"
            },
            "language_config": {"target_language": "en"},
            "mode_config": {"operation_mode": "typer"}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    for key, default_value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = default_value
                        elif isinstance(default_value, dict):
                            if key not in loaded_config or not isinstance(loaded_config[key], dict):
                                loaded_config[key] = {}
                            for sub_key, default_sub_value in default_value.items():
                                if sub_key not in loaded_config[key]:
                                    loaded_config[key][sub_key] = default_sub_value
                    return loaded_config
            except Exception as e:
                print(f"Error loading {CONFIG_FILE}: {e}. Using defaults and attempting to save.")
        else:
            print(f"Warning: {CONFIG_FILE} not found. Creating with default settings.")

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Default configuration saved to {CONFIG_FILE}.")
        except Exception as e:
            print(f"Error creating default {CONFIG_FILE}: {e}")
        return default_config

    def _save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            print("Configuration saved.")
            self.mistral_api_key = self.config.get("api_keys", {}).get("mistral")
            self.gemini_api_key = self.config.get("api_keys", {}).get("gemini")
            self._initialize_mistral_client()
        except Exception as e:
            print(f"Error saving {CONFIG_FILE}: {e}")

    def _play_sound_async(self, sound_file_name): # sound_file_name is "open.wav" or "close.wav"
        if not PYDUB_AVAILABLE: return

        # Construct the full path to the sound file within the assets folder
        sound_file_path_in_assets = os.path.join("assets", sound_file_name)

        # Check if the file exists AT THE CORRECT PATH
        if os.path.exists(sound_file_path_in_assets):
            def play_it():
                try:
                    # Load the sound from the correct path
                    sound = AudioSegment.from_file(sound_file_path_in_assets, format="wav")
                    louder_sound = sound + 12 # Increase volume
                    pydub_play(louder_sound)
                except Exception as e:
                    # Use the correct path in the error message
                    print(f"Error playing sound {sound_file_path_in_assets} with pydub: {e}")
            threading.Thread(target=play_it, daemon=True).start()
        else:
            # Use the correct path in the "not found" message
            print(f"Sound file not found: {sound_file_path_in_assets}")

    def _start_keyboard_listener(self):
        print("Starting global keyboard listener for Axo...")
        with keyboard.Listener(on_press=self._on_global_key_press, on_release=self._on_global_key_release) as listener:
            listener.join()
        print("Axo global keyboard listener stopped.")

    def _check_hotkey_modifiers_active(self):
        has_ctrl = any(k in self.currently_pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
        has_shift = any(k in self.currently_pressed_keys for k in (keyboard.Key.shift_l, keyboard.Key.shift_r))
        return has_ctrl and has_shift

    def _on_global_key_press(self, key):
        self.currently_pressed_keys.add(key)
        key_char_val = getattr(key, 'char', None)
        vk_val = getattr(key, 'vk', None)
        modifiers_are_active = self._check_hotkey_modifiers_active()

        settings_hotkey_triggered = False
        if modifiers_are_active:
            if key_char_val and key_char_val.lower() == self.settings_hotkey_char:
                settings_hotkey_triggered = True
            elif vk_val and vk_val == 0x48: # VK for 'H'
                settings_hotkey_triggered = True

        if settings_hotkey_triggered:
            self.master.after(0, self._open_settings_dialog)
            return

        if key == self.hotkey_trigger_key and modifiers_are_active:
            if not self.hotkey_active_for_release and (self.current_state == "initial" or self.current_state == "loading_model"):
                if self.current_state == "loading_model" and not self.model_loaded_event.is_set():
                    return
                self.hotkey_active_for_release = True
                self.master.after(0, self._trigger_recording_start)

    def _on_global_key_release(self, key):
        original_hotkey_active_for_release = self.hotkey_active_for_release
        if key == self.hotkey_trigger_key and original_hotkey_active_for_release:
            if self.current_state == "listening":
                self.master.after(0, self._trigger_recording_stop_and_process)
            self.hotkey_active_for_release = False

        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.shift_l, keyboard.Key.shift_r):
            temp_removed = False
            if key in self.currently_pressed_keys:
                self.currently_pressed_keys.remove(key)
                temp_removed = True

            if original_hotkey_active_for_release and not self._check_hotkey_modifiers_active():
                if self.current_state == "listening":
                    self.master.after(0, self._trigger_recording_stop_and_process)
                self.hotkey_active_for_release = False

            if temp_removed:
                self.currently_pressed_keys.add(key)

        try:
            self.currently_pressed_keys.remove(key)
        except KeyError:
            pass

    def _trigger_recording_start(self):
        if not self.master.winfo_viewable(): self.master.deiconify()
        self.is_window_visible = True
        if not self.model_loaded_event.is_set():
            print("Model is still loading, please wait."); self.hotkey_active_for_release = False; return
        if self.current_state == "initial":
            self.current_state = "listening"; self.animation_step = 0
            self.bar_current_heights = np.zeros(self.num_audio_bars)
            self._update_ui_elements(); self._start_audio_recording()

    def _trigger_recording_stop_and_process(self):
        if self.current_state == "listening":
            self.current_state = "processing"; self.animation_step = 0
            self._update_ui_elements(); self._stop_audio_recording_and_process()    

    def _load_asr_model(self):
        try:
            self.asr_model = nemo_asr.models.ASRModel.from_pretrained(MODEL_NAME)
            self.model_loaded_event.set(); print("ASR model loaded successfully.")
            self.current_state = "initial"
            self.master.after(0, self._update_ui_elements)
        except Exception as e:
            print(f"Error loading ASR model: {e}"); self.current_state = "error_loading"
            self.master.after(0, self._update_ui_elements)

    def _update_ui_elements(self):
        if not self.master.winfo_exists() or not self.drawing_canvas.winfo_exists(): return
        self.drawing_canvas.delete("all"); self.master.update_idletasks()
        if not self.is_window_visible: return

        if self.current_state == "loading_model": self._draw_loading_model_state_ui()
        elif self.current_state == "initial": self._draw_initial_state_ui()
        elif self.current_state == "listening": self._draw_listening_state_ui()
        elif self.current_state == "processing": self._draw_processing_state_ui()
        elif self.current_state == "error_loading": self._draw_error_loading_state_ui()

    def _draw_loading_model_state_ui(self):
        canvas_width = self.drawing_canvas.winfo_width(); canvas_height = self.drawing_canvas.winfo_height()
        if canvas_width <=1 or canvas_height <=1: return
        self.drawing_canvas.create_text(
            canvas_width / 2, canvas_height / 2,
            text="Loading Model...", fill=self.animation_visual_color,
            font=("Arial", 10)
        )
        if self.current_state == "loading_model":
             self.master.after(100, self._update_ui_elements)

    def _draw_initial_state_ui(self):
        canvas_width = self.drawing_canvas.winfo_width(); canvas_height = self.drawing_canvas.winfo_height()
        if canvas_width <=1 or canvas_height <=1: return
        line_width, line_thickness = 40, 5; line_y_pos = canvas_height * 0.5
        self.drawing_canvas.create_line(
            (canvas_width-line_width)/2, line_y_pos,
            (canvas_width+line_width)/2, line_y_pos,
            fill=self.indicator_line_color, width=line_thickness, capstyle=tk.ROUND
        )

    def _draw_listening_state_ui(self):
        canvas_width = self.drawing_canvas.winfo_width(); canvas_height = self.drawing_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1: return
        anim_center_y = canvas_height / 2
        circle_max_radius = 7
        circle_x_offset = 20
        pulsing_radius = circle_max_radius * (0.65 + 0.35 * abs(math.sin(self.animation_step * 0.38)))
        self.drawing_canvas.create_oval(
            circle_x_offset - pulsing_radius, anim_center_y - pulsing_radius,
            circle_x_offset + pulsing_radius, anim_center_y + pulsing_radius,
            fill=self.accent_color, outline=""
        )
        bar_max_h = 24
        bar_w = 4
        bar_sep = 3
        total_bars_width = (self.num_audio_bars * (bar_w + bar_sep)) - bar_sep
        bars_start_x_centered = (canvas_width - total_bars_width) / 2
        smoothing_factor = 0.4
        for i in range(self.num_audio_bars):
            phase_shift = i * 0.65
            amplitude_modulation_factor = 0.6 + 0.4 * abs(math.sin(self.animation_step * 0.15 + phase_shift))
            effective_normalized_amplitude = self.current_normalized_amplitude * amplitude_modulation_factor
            target_h_factor = 0.15 + 0.85 * min(effective_normalized_amplitude, 1.0)
            self.bar_target_heights[i] = bar_max_h * target_h_factor
            self.bar_current_heights[i] += (self.bar_target_heights[i] - self.bar_current_heights[i]) * smoothing_factor
            bar_dynamic_height = max(2, self.bar_current_heights[i])
            current_bar_x_center = bars_start_x_centered + i * (bar_w + bar_sep) + (bar_w / 2)
            self.drawing_canvas.create_line(
                current_bar_x_center, anim_center_y - bar_dynamic_height / 2,
                current_bar_x_center, anim_center_y + bar_dynamic_height / 2,
                fill=self.animation_visual_color, width=bar_w, capstyle=tk.ROUND
            )
        self.animation_step += 1
        if self.current_state == "listening": self.master.after(35, self._update_ui_elements)

    def _draw_processing_state_ui(self):
        canvas_width = self.drawing_canvas.winfo_width(); canvas_height = self.drawing_canvas.winfo_height()
        if canvas_width <=1 or canvas_height <=1: return
        anim_center_x, anim_center_y = canvas_width/2, canvas_height/2
        dot_max_radius = 3.5
        orbit_dist = 12 * 1.3
        num_processing_dots = 4
        for i in range(num_processing_dots):
            angle = (self.animation_step*0.075 + (2*math.pi/num_processing_dots)*i)
            dot_center_x = anim_center_x + orbit_dist*math.cos(angle)
            dot_center_y = anim_center_y + orbit_dist*math.sin(angle)
            current_dot_size = dot_max_radius * (0.65 + 0.35 * abs(math.sin(self.animation_step*0.12 + i*2)))
            self.drawing_canvas.create_oval(dot_center_x-current_dot_size, dot_center_y-current_dot_size, dot_center_x+current_dot_size, dot_center_y+current_dot_size, fill=self.accent_color, outline="")
        self.animation_step += 1
        if self.current_state == "processing": self.master.after(65, self._update_ui_elements)

    def _draw_error_loading_state_ui(self):
        canvas_width = self.drawing_canvas.winfo_width(); canvas_height = self.drawing_canvas.winfo_height()
        if canvas_width <=1 or canvas_height <=1: return
        self.drawing_canvas.create_line(canvas_width/2 - 10, canvas_height/2, canvas_width/2 + 10, canvas_height/2, fill="red", width=5, capstyle=tk.ROUND)
        self.drawing_canvas.create_text(
            canvas_width / 2, canvas_height / 2 + 10,
            text="Error Loading", fill="red", font=("Arial", 8)
        )

    def _audio_callback(self, indata, frames, time, status):
        if status: print(f"Audio callback status: {status}")
        if self.is_recording:
            self.audio_frames.append(indata.copy())
            MAX_EXPECTED_AMPLITUDE = 2000
            mean_abs_val = np.abs(indata).mean()
            self.current_normalized_amplitude = min(mean_abs_val / MAX_EXPECTED_AMPLITUDE, 1.0) if MAX_EXPECTED_AMPLITUDE > 0 else 0.0
        else:
            self.current_normalized_amplitude = 0.0

    def _start_audio_recording(self):
        if not self.model_loaded_event.is_set():
            print("ASR Model not ready."); self.current_state = "initial"; self._update_ui_elements(); return
        if self.is_recording: return
        print("Starting recording..."); self._play_sound_async("Open.wav")
        self.audio_frames = []; self.current_normalized_amplitude = 0.0
        self.bar_current_heights = np.zeros(self.num_audio_bars)
        self.is_recording = True
        try:
            blocksize = int(SAMPLE_RATE * AUDIO_BLOCK_DURATION_MS / 1000)
            self.audio_stream = sounddevice.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16', callback=self._audio_callback, blocksize=blocksize)
            self.audio_stream.start()
        except Exception as e:
            print(f"Error starting recording: {e}"); self.is_recording = False; self.current_state = "initial"; self._update_ui_elements()

    def _stop_audio_recording_and_process(self):
        if not self.is_recording and not self.audio_frames:
            self.is_recording = False; self.current_normalized_amplitude = 0.0
            if self.audio_stream and self.audio_stream.active:
                try:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                except Exception as e:
                    print(f"Error stopping/closing stream on no-op: {e}")
            self.audio_stream = None; self.master.after(0, self._safe_ui_update_to_initial); return

        print("Stopping recording..."); self.is_recording = False; self.current_normalized_amplitude = 0.0
        if self.audio_stream:
            try:
                if self.audio_stream.active: self.audio_stream.stop()
                self.audio_stream.close()
            except Exception as e:
                print(f"Error stopping/closing audio stream: {e}")
            self.audio_stream = None

        time.sleep(0.05 + (AUDIO_BLOCK_DURATION_MS / 1000))

        if not self.audio_frames:
            print("No audio recorded."); self.master.after(0, self._safe_ui_update_to_initial); return

        frames_to_send = list(self.audio_frames); self.audio_frames = []
        threading.Thread(target=self._transcribe_and_refine_audio_data, args=(frames_to_send,), daemon=True).start()

    def _safe_ui_update_to_initial(self):
        self.current_state = "initial"
        if not self.master.winfo_viewable(): self.master.deiconify()
        self.is_window_visible = True; self._update_ui_elements()

    def _process_text_with_mistral(self, text):
        language_code = self.config.get("language_config", {}).get("target_language", "en")
        mode = self.config.get("mode_config", {}).get("operation_mode", "typer")
        model_name = self.config.get("models_config", {}).get("mistral_model_name", "mistral-medium-latest")

        system_prompt_core = f"""
You are an advanced AI assistant. Your primary task is to process raw speech-to-text transcription.
Modern LLMs like you excel at understanding direct instructions. Be clear, concise, and accurate.
First, meticulously correct any ASR errors (misspellings, stutters, phonetic mistakes, duplications).
Then, ensure your entire output is in the target language: **{language_code}** (ISO 639-1 code).
Preserve the original meaning and intent absolutely.
Output ONLY the processed text in the target language, with no additional comments, conversational phrases, apologies, or self-references, unless the mode specifically dictates a structured output.
"""

        typer_mode_instructions = f"""
CRITICAL INSTRUCTION: You are in 'Typer' mode. Your goal is to refine the provided ASR (Automatic Speech Recognition) transcript.
Follow these principles strictly:

1.  **ASR Correction:** Identify and correct common ASR errors. This includes:
    *   Misspellings due to phonetic similarity (e.g., "too" vs. "to" vs. "two", "there" vs. "their" vs. "they're").
    *   Stutters or repeated words (e.g., "I I I want" should become "I want"; "the the car" should become "the car").
    *   Incorrect word segmentation if evident.
    *   Punctuation: Add appropriate punctuation (periods, commas, question marks) to make the text readable and grammatically sound. Capitalize the beginning of sentences.

2.  **Translation:** Ensure the final output is entirely in the target language: **{language_code}**. If the ASR transcript contains phrases from other languages, translate them.

3.  **Meaning Preservation:** The corrected and translated text must retain the exact original meaning and intent of the speaker. Do NOT add new information or change the core message.

4.  **Style Preservation (High Priority):**
    *   If the original speech (once ASR errors are fixed) is already grammatically correct, natural-sounding, and clear in its phrasing and vocabulary for the target language **{language_code}**, **DO NOT ALTER IT.** Your role is to be a meticulous corrector and translator, not a stylistic rewriter.
    *   Maintain the user's original style of speaking, sentence structure, and vocabulary if it's already good and appropriate for the target language. For example, if the user speaks informally, keep it informal (unless it's an ASR error).

5.  **List Formatting:**
    *   If the user's speech implies a list (e.g., using "firstly", "secondly", "then this, then that", or a sequence of related short statements), format these items as bullet points (using '+ ') or a numbered list (e.g., '1. ') if the order is explicitly stated or clearly sequential.
    *   Example (if target language is English): User says, "For the project, we need to define scope, then gather resources, and finally set a timeline."
      Expected output:
      + Define scope.
      + Gather resources.
      + Set a timeline.
    *   Do not impose list formatting if it's not clearly implied.

6.  **Conciseness:** Output only the refined text. No explanations, no apologies, no "Here's the refined text:". Just the text itself.
"""

        prompt_engineer_mode_instructions = f"""
CRITICAL INSTRUCTION: You are in 'Prompt Engineer' mode. Your objective is to transform the user's spoken input into a highly effective, structured prompt for another advanced AI system (like GPT-4.1, Gemini 1.5 Pro, Claude 3).
The generated prompt MUST be in **{language_code}** and enclosed in a main `<Prompt>` XML tag, following the detailed structure below.

**Core Principles to Apply (Think step-by-step for each section):**

1.  **Deconstruct User Input:** Carefully analyze the user's raw ASR transcript to understand their core intent, the task they want the target AI to perform, key entities, desired output, and any implicit or explicit instructions.
2.  **Adhere to Modern Prompting Best Practices:** Construct the prompt using the following XML-delimited sections. These sections are based on proven strategies for guiding LLMs effectively.
3.  **Clarity and Directness:** Instructions within the generated prompt should be clear, direct, and unambiguous. Modern LLMs follow direct instructions well.
4.  **Negative Instructions:** Use negative instructions (e.g., "Do not include...") sparingly but appropriately if they clarify the task significantly.
5.  **Sandwich Method for Critical Instructions:** If there are overriding critical instructions for the target AI, ensure they are mentioned early (e.g., in `<RoleAndObjective>` or `<Instructions>`) and reiterated in `<FinalInstructions>`.
6.  **Chain-of-Thought (CoT) Encouragement:** Where appropriate, include a "Think step-by-step" instruction within the generated prompt's `<FinalInstructions>` or relevant instruction sections to guide the target AI's reasoning process.

**Output Structure (Generate the prompt in this XML format):**

```xml
<Prompt>
    <RoleAndObjective>
        <!-- Define the persona the target AI should adopt and its primary goal/task. -->
        <!-- Example: You are an expert Python programmer. Your objective is to write a function that... -->
        <!-- Based on user input: [Analyze user's speech for role and objective] -->
    </RoleAndObjective>

    <Instructions>
        <!-- Provide clear, step-by-step instructions for the target AI. -->
        <!-- Use numbered lists if the order is important. -->
        <!-- Example:
        1. Read the provided <InputText>.
        2. Identify all named entities.
        3. Categorize each entity.
        -->
        <!-- Based on user input: [Extract and structure detailed instructions from user's speech] -->
    </Instructions>

    <InputData name="[A_descriptive_name_for_the_primary_input_if_applicable_e.g., MeetingTranscript, UserQuery, CodeSnippet]">
        <!-- This section is for the actual data the target AI will process. -->
        <!-- If the user's speech *is* the input data for the target AI, place the cleaned-up version of their speech here. -->
        <!-- If the user is *describing* data that will be provided later, you might leave this section with a placeholder like "[PASTE USER'S DOCUMENT HERE]" or describe the expected input format. -->
        <!-- For example, if user says "Summarize this document for me..." and then provides the document text, that text goes here. -->
        <!-- If user says "I want you to write an email to John about the meeting", this section might be empty or describe what information the email should contain. -->
        <!-- Based on user input: [Place or describe the primary input data here] -->
    </InputData>

    <OutputFormat>
        <!-- Specify precisely how the target AI's output should be structured. -->
        <!-- Be very specific. e.g., "JSON format with keys 'name' and 'email'.", "A three-paragraph summary.", "Markdown list." -->
        <!-- If the user specified an output format, reflect it here. If not, infer a suitable one or state "natural language". -->
        <!-- Example: Provide the output as a JSON object with the keys "summary" and "action_items_list". -->
        <!-- Based on user input: [Define the desired output structure] -->
    </OutputFormat>

    <Examples>
        <!-- Provide 1-2 concise examples (few-shot) if it significantly clarifies the task or desired output style for the target AI. -->
        <!-- This is especially useful for complex formatting or nuanced tasks. -->
        <!-- If the user's request is simple and direct, this section can be omitted or state "No examples provided." -->
        <!-- Example (if the task was to extract names and roles):
        <Example>
            <Input>Text: "Alice is the project manager and Bob is the lead developer."</Input>
            <Output>JSON: [ {{"name": "Alice", "role": "project manager"}}, {{"name": "Bob", "role": "lead developer"}} ]</Output>
        </Example>
        -->
        <!-- Based on user input and task complexity: [Construct a relevant, simple example if beneficial, otherwise omit or state "No examples needed for this task."] -->
    </Examples>

    <Constraints>
        <!-- List any constraints or things the target AI should avoid. -->
        <!-- Example: Do not use technical jargon. The summary should not exceed 200 words. -->
        <!-- Based on user input: [Identify and list any constraints] -->
    </Constraints>

    <FinalInstructions>
        <!-- Reiterate the most critical instructions, especially regarding the output format and core task. -->
        <!-- Include a "Think step-by-step to ensure accuracy." or similar CoT prompt. -->
        <!-- Example: Ensure the output strictly adheres to the specified <OutputFormat>. Double-check all extracted entities for accuracy. Think step-by-step. -->
        <!-- Based on user input: [Reiterate key instructions and add CoT encouragement] -->
    </FinalInstructions>
</Prompt>
Your task:
1. Correct ASR errors in the following raw transcript.
2. Translate the corrected transcript fully into {language_code}.
3. Based on the translated content, generate a complete, structured XML prompt according to the schema and principles outlined above.
"""

        if not self.mistral_client:
         print("Mistral client not initialized. Skipping text refinement.")
         return text
        if not text.strip():
         print("No text from ASR to refine.")
         return ""

        print("Refining text with Mistral...")
        # model_name, language_code, mode are already defined at the start of the method

        user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
        user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"

        messages = []

        if mode == "typer":
            messages = [
                {"role": "system", "content": system_prompt_core},
                {"role": "user", "content": f"{typer_mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
            ]
        elif mode == "prompt_engineer":
            messages = [
                {"role": "system", "content": system_prompt_core},
                {"role": "user", "content": f"{prompt_engineer_mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
            ]
        else:
            print(f"Unknown mode: {mode}. Defaulting to 'typer' mode behavior.")
            messages = [
                {"role": "system", "content": system_prompt_core},
                {"role": "user", "content": f"{typer_mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
            ]

        try:
            chat_response = self.mistral_client.chat.complete(
                model=model_name,
                messages=messages,
                temperature=0.05
            )
            refined_text = chat_response.choices[0].message.content.strip()

            if mode == "prompt_engineer":
                if refined_text.startswith("```xml") and refined_text.endswith("```"):
                    refined_text = refined_text.removeprefix("```xml").removesuffix("```").strip()
                elif refined_text.startswith("```") and refined_text.endswith("```"):
                    refined_text_lines = refined_text.splitlines()
                    if len(refined_text_lines) > 2:
                        refined_text = "\n".join(refined_text_lines[1:-1]).strip()
                    else: # Only fences or fences with one line, strip them
                        refined_text = refined_text.replace("```", "").strip()
            else: # Typer mode
                if not (refined_text.startswith("+ ") or refined_text.startswith("1.")): # Don't strip quotes from lists
                    if (refined_text.startswith('"') and refined_text.endswith('"')) or \
                       (refined_text.startswith("'") and refined_text.endswith("'")):
                        refined_text = refined_text[1:-1]

            print(f"Mistral refined text (Mode: {mode}, Lang: {language_code}):\n{refined_text}")
            return refined_text
        except Exception as e:
            print(f"Error during Mistral API call: {e}")
            return text
    
    def _transcribe_and_refine_audio_data(self, frames_to_process):
        final_text_to_output = ""
        try:
            if not frames_to_process:
                print("Transcription thread: No frames received.")
                self.master.after(0, self._set_initial_state_after_processing)
                return
            audio_data = np.concatenate(frames_to_process, axis=0)
            if audio_data.size == 0:
                print("Concatenated audio data is empty.")
                self.master.after(0, self._set_initial_state_after_processing)
                return

            sample_width_bytes = 2
            with wave.open(TEMP_AUDIO_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(sample_width_bytes)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())

            transcribed_text = ""
            if self.asr_model:
                print("Transcribing audio with NeMo...")
                # nemo_result_list is expected to be a list of transcriptions.
                # For a single file, it will be a list with one element.
                nemo_result_list = self.asr_model.transcribe([TEMP_AUDIO_FILENAME])

                if nemo_result_list and isinstance(nemo_result_list, list) and len(nemo_result_list) > 0:
                    # CORRECTED LINE: Access the first element of the list
                    actual_result_item = nemo_result_list[0]

                    if isinstance(actual_result_item, str):
                        transcribed_text = actual_result_item
                    # Check if it's an object with a 'text' attribute (like NeMo's TranscriptionResult)
                    elif hasattr(actual_result_item, 'text') and isinstance(getattr(actual_result_item, 'text'), str):
                        transcribed_text = actual_result_item.text
                    elif actual_result_item is None: # Explicitly check for None if NeMo might return that
                        print("ASR transcription for the file by NeMo resulted in: None.")
                    else:
                        # This is where your error was likely being caught before,
                        # because actual_result_item was the list itself.
                        print(f"ASR: Unexpected type for NeMo's transcription result item: {type(actual_result_item)}")
                elif nemo_result_list is None: # Handle if transcribe itself returns None
                     print("ASR model's transcribe method returned: None.")
                elif isinstance(nemo_result_list, list) and len(nemo_result_list) == 0: # Handle empty list
                     print("ASR model's transcribe method returned: an empty list (no transcription).")
                else: # Handle other unexpected return types from transcribe()
                    print(f"ASR model's transcribe method returned an unexpected structure: {type(nemo_result_list)}")


                if transcribed_text:
                    print(f"ASR Transcription: {transcribed_text}")
                else:
                    # This message will now appear if actual_result_item was None,
                    # or if the text attribute was empty, or if an unexpected type was encountered.
                    print("ASR Transcription by NeMo resulted in empty text (no speech detected or error).")
            else:
                print("ASR model not available. Transcription skipped.")

            text_processing_service = self.config.get("models_config", {}).get("text_processing_service")
            if text_processing_service == "Mistral" and self.mistral_client and transcribed_text: # Process only if text exists
                final_text_to_output = self._process_text_with_mistral(transcribed_text)
            else: # Use raw ASR if no refinement service OR if transcribed_text was empty
                final_text_to_output = transcribed_text

            if final_text_to_output:
                pyperclip.copy(final_text_to_output)
                print(f"Final text copied to clipboard: \"{final_text_to_output}\"")
                try:
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'v')
                    print("Paste command sent.")
                except Exception as e_paste:
                    print(f"Could not simulate paste: {e_paste}")
            else:
                print("No final text to output after ASR and refinement.")

        except ValueError as ve:
            print(f"ValueError during audio processing: {ve}")
        except Exception as e:
            print(f"Error during transcription/refinement: {e}")
        finally:
            self._play_sound_async("Close.wav")
            self.master.after(0, self._set_initial_state_after_processing)
    def _set_initial_state_after_processing(self):
        self.current_state = "initial"; self.animation_step = 0
        if not self.master.winfo_viewable(): self.master.deiconify()
        self.is_window_visible = True; self._update_ui_elements()

    def _open_settings_dialog(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus(); return

        self.settings_window = ctk.CTkToplevel(self.master)
        self.settings_window.title("Axo Settings")
        self.settings_window.geometry("450x420")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.grab_set()
        try:
            # Ensure 'Axo Icon.ico' is in the same directory as your script
            self.master.iconbitmap(os.path.join("assets", "Axo Icon.ico"))
        except tk.TclError:
            print("Icon 'Axo Icon.ico' not found or not supported. Skipping icon.")

        tabview = ctk.CTkTabview(self.settings_window, width=430)
        tabview.pack(padx=10, pady=10, fill="both", expand=True)
        tab_mode = tabview.add("Mode")
        tab_models = tabview.add("Models")
        tab_language = tabview.add("Language")

        mode_frame = ctk.CTkFrame(tab_mode, fg_color="transparent")
        mode_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(mode_frame, text="Operation Mode:").pack(anchor="w", pady=(0,5))
        self.mode_var = ctk.StringVar(value=self.config.get("mode_config", {}).get("operation_mode", "typer"))

        def set_mode(mode): # Helper function for radio buttons
            self.mode_var.set(mode)

        typer_check = ctk.CTkRadioButton(mode_frame, text="Typer (Direct Refinement)", variable=self.mode_var, value="typer", command=lambda: set_mode("typer"))
        typer_check.pack(anchor="w", pady=2)
        prompt_check = ctk.CTkRadioButton(mode_frame, text="Prompt Engineer (AI Prompt Generation)", variable=self.mode_var, value="prompt_engineer", command=lambda: set_mode("prompt_engineer"))
        prompt_check.pack(anchor="w", pady=2)
        current_mode = self.config.get("mode_config", {}).get("operation_mode", "typer")
        if current_mode == "typer": typer_check.select()
        elif current_mode == "prompt_engineer": prompt_check.select()
        else: typer_check.select() # Default


        models_frame = ctk.CTkFrame(tab_models, fg_color="transparent")
        models_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(models_frame, text="Mistral API Key:").pack(anchor="w", pady=(5,2))
        self.mistral_api_entry = ctk.CTkEntry(models_frame, width=380)
        self.mistral_api_entry.insert(0, self.config.get("api_keys", {}).get("mistral", ""))
        self.mistral_api_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(models_frame, text="Gemini API Key:").pack(anchor="w", pady=(5,2))
        self.gemini_api_entry = ctk.CTkEntry(models_frame, width=380)
        self.gemini_api_entry.insert(0, self.config.get("api_keys", {}).get("gemini", ""))
        self.gemini_api_entry.pack(fill="x", pady=(0,10))

        language_frame = ctk.CTkFrame(tab_language, fg_color="transparent")
        language_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(language_frame, text="Output Language:").pack(anchor="w", pady=(0,5))

        current_lang_code = self.config.get("language_config", {}).get("target_language", "en")
        current_lang_display = self.language_code_to_display.get(current_lang_code, "English")
        self.language_var = ctk.StringVar(value=current_lang_display)

        lang_menu = ctk.CTkOptionMenu(language_frame,
                                       variable=self.language_var,
                                       values=list(self.language_display_to_code.keys()))
        lang_menu.pack(fill="x", pady=(0,10))

        save_button = ctk.CTkButton(self.settings_window, text="Save & Close", command=self._save_settings_from_dialog)
        save_button.pack(pady=(15,10), side="bottom")
        self.settings_window.protocol("WM_DELETE_WINDOW", self._on_settings_close)

    def _save_settings_from_dialog(self):
        if self.settings_window is None or not self.settings_window.winfo_exists(): return
        self.config["api_keys"]["mistral"] = self.mistral_api_entry.get()
        self.config["api_keys"]["gemini"] = self.gemini_api_entry.get()
        self.config["mode_config"]["operation_mode"] = self.mode_var.get()

        selected_display_language = self.language_var.get()
        self.config["language_config"]["target_language"] = self.language_display_to_code.get(selected_display_language, "en")

        self._save_config()
        self._on_settings_close()

    def _on_settings_close(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.grab_release()
            self.settings_window.destroy()
        self.settings_window = None

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark") # or "Light"
    ctk.set_default_color_theme("blue") # or "green", "dark-blue"

    root_app_window = ctk.CTk()
    app_instance = AxoApp(root_app_window)
    root_app_window.mainloop()        