import customtkinter as ctk
import tkinter as tk
import math
import threading
import time
import numpy as np
import os

# Import from the modularized backend
from backend.sound import play_sound_async
from backend.audio import start_audio_recording, stop_audio_recording_and_process
from backend.hotkeys import update_hotkey_from_config, start_keyboard_listener
from backend.ai import load_asr_model, initialize_mistral_client, initialize_gemini_client, transcribe_and_refine_audio_data

# Import from the modularized UI
from ui.drag_handler import on_drag_start, on_drag_motion
from ui.drawing import update_ui_elements
from ui.streaming_widget import StreamingWidget

# Import from the modularized settings
from settings.config_manager import load_config, save_config
from settings.settings_window import open_settings_dialog

# Image handling for icons
from PIL import Image

# --- Global Constants ---
ASSETS_DIR = "assets"

# Default model names (can be overridden by user selection including custom models)
DEFAULT_MISTRAL_MODEL_NAME = "mistral-medium-latest"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.0-flash"


class AxoApp:
    def __init__(self, app_window):
        self.master = app_window
        self.master.title("Axo")
        try:
            self.master.iconbitmap(os.path.join(ASSETS_DIR, "Axo Icon.ico"))
        except tk.TclError:
            print(f"Icon '{os.path.join(ASSETS_DIR, 'Axo Icon.ico')}' not found or not supported. Skipping icon.")

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
        self.num_audio_bars = 9
        self.bar_target_heights = np.zeros(self.num_audio_bars)
        self.bar_current_heights = np.zeros(self.num_audio_bars)

        self.config = load_config()
        self.mistral_api_key = self.config.get("api_keys", {}).get("mistral")
        self.gemini_api_key = self.config.get("api_keys", {}).get("gemini")

        self.mistral_client = None
        initialize_mistral_client(self)

        self.gemini_model_instance = None
        initialize_gemini_client(self)

        # Initialize Ollama manager
        from backend.ai import initialize_ollama_manager
        initialize_ollama_manager(self)

        try:
            current_theme = ctk.ThemeManager.get_theme()
            self.accent_color = current_theme["CTkButton"]["fg_color"][1] if isinstance(current_theme["CTkButton"]["fg_color"], (list, tuple)) else current_theme["CTkButton"]["fg_color"]
            self.content_bg_color = current_theme["CTkFrame"]["fg_color"][1] if isinstance(current_theme["CTkFrame"]["fg_color"], (list, tuple)) else current_theme["CTkFrame"]["fg_color"]
            self.indicator_line_color = current_theme["CTkFrame"]["top_fg_color"][1] if isinstance(current_theme["CTkFrame"]["top_fg_color"], (list, tuple)) else current_theme["CTkFrame"]["top_fg_color"]
            if self.indicator_line_color == self.content_bg_color:
                 self.indicator_line_color = "#3D3D3D" if ctk.get_appearance_mode().lower() == "dark" else "#B0B0B0"
            self.animation_visual_color = current_theme["CTkLabel"]["text_color"][1] if isinstance(current_theme["CTkLabel"]["text_color"], (list, tuple)) else current_theme["CTkLabel"]["text_color"]
        except (TypeError, KeyError, IndexError, AttributeError):
            self.accent_color = "#0078D4"
            self.content_bg_color = "#2B2B2B" if ctk.get_appearance_mode().lower() == "dark" else "#E0E0E0"
            self.indicator_line_color = "#4A4A4A" if ctk.get_appearance_mode().lower() == "dark" else "#B0B0B0"
            self.animation_visual_color = "#E0E0E0" if ctk.get_appearance_mode().lower() == "dark" else "#202020"

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
        self._update_hotkey_from_config()
        self.settings_hotkey_char = 'h'
        self.hotkey_active_for_release = False
        self.settings_window = None

        self.language_display_to_code = {
            "English": "en", "Arabic": "ar", "French": "fr", "Spanish": "es",
            "German": "de", "Italian": "it", "Portuguese": "pt", "Russian": "ru",
            "Chinese (Simplified)": "zh", "Japanese": "ja", "Korean": "ko", "Hindi": "hi",
            "Dutch": "nl", "Polish": "pl", "Turkish": "tr", "Swedish": "sv"
        }
        self.language_code_to_display = {v: k for k, v in self.language_display_to_code.items()}

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        # Initialize streaming widget
        self.streaming_widget = StreamingWidget(self)

        for widget_to_bind in [self.main_content_frame, self.drawing_canvas]:
            widget_to_bind.bind("<ButtonPress-1>", self._on_drag_start)
            widget_to_bind.bind("<B1-Motion>", self._on_drag_motion)

        print("Loading ASR model...")
        threading.Thread(target=self._load_asr_model, daemon=True).start()
        threading.Thread(target=self._start_keyboard_listener, daemon=True).start()

    def _on_drag_start(self, event):
        on_drag_start(self, event)

    def _on_drag_motion(self, event):
        on_drag_motion(self, event)

    def _save_config(self):
        save_config(self)

    def _play_sound_async(self, sound_file_name_only):
        play_sound_async(sound_file_name_only)

    def _update_hotkey_from_config(self):
        update_hotkey_from_config(self)

    def _start_keyboard_listener(self):
        start_keyboard_listener(self)

    def _update_ui_elements(self):
        update_ui_elements(self)

    def _load_asr_model(self):
        load_asr_model(self)

    def _start_audio_recording(self):
        start_audio_recording(self)

    def _stop_audio_recording_and_process(self):
        stop_audio_recording_and_process(self)

    def start_transcription_thread(self, frames_to_process):
        threading.Thread(target=transcribe_and_refine_audio_data, args=(self, frames_to_process), daemon=True).start()

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

    def _safe_ui_update_to_initial(self):
        self.current_state = "initial"
        if not self.master.winfo_viewable(): self.master.deiconify()
        self.is_window_visible = True; self._update_ui_elements()

    def _set_initial_state_after_processing(self):
        self.current_state = "initial"
        self.animation_step = 0
        if not self.master.winfo_viewable():
            self.master.deiconify()
        self.is_window_visible = True
        self._update_ui_elements()

    def _toggle_ui_visibility(self):
        """Toggles the main window's visibility on Ctrl+Shift+X."""
        # The winfo_viewable() method returns 1 if the window is mapped (visible), 0 otherwise.
        if self.master.winfo_viewable():
            self.master.withdraw() # Hides the window entirely.
            self.is_window_visible = False
            print("UI Hidden. Press Ctrl+Shift+X to show again.")
        else:
            self.master.deiconify() # Shows the window again.
            self.is_window_visible = True
            self.master.attributes('-topmost', True) # Ensure it's on top when it reappears.
            print("UI Shown.")

    def _open_settings_dialog(self):
        open_settings_dialog(self)

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    root_app_window = ctk.CTk()
    app_instance = AxoApp(root_app_window)
    root_app_window.mainloop()