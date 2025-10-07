import customtkinter as ctk
import tkinter as tk
from pynput import keyboard
from PIL import Image
import os

from backend.audio import get_audio_devices

ASSETS_DIR = "assets"
DEFAULT_MISTRAL_MODEL_NAME = "mistral-medium-latest"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.5-flash"

def open_settings_dialog(app):
    if app.settings_window is not None and app.settings_window.winfo_exists():
        app.settings_window.focus(); return

    app.settings_window = ctk.CTkToplevel(app.master)
    app.settings_window.title("Axo Settings")
    app.settings_window.geometry("580x720")
    app.settings_window.attributes("-topmost", True)
    app.settings_window.grab_set()
    app.hotkey_capture_listener = None

    try:
        app.settings_window.iconbitmap(os.path.join(ASSETS_DIR, "Axo Icon.ico"))
    except tk.TclError:
        print(f"Could not set icon for settings window.")

    tabview = ctk.CTkTabview(app.settings_window, width=530)
    tabview.pack(padx=10, pady=10, fill="both", expand=True)
    tab_mode = tabview.add("Mode")
    tab_ai = tabview.add("AI")
    tab_system = tabview.add("System")
    tab_streaming = tabview.add("Streaming")

    # Mode Tab
    mode_frame = ctk.CTkFrame(tab_mode, fg_color="transparent")
    mode_frame.pack(pady=10, padx=10, fill="x")
    ctk.CTkLabel(mode_frame, text="Operation Mode:").pack(anchor="w", pady=(0,5))
    app.mode_var = ctk.StringVar(value=app.config.get("mode_config", {}).get("operation_mode", "typer"))
    ctk.CTkRadioButton(mode_frame, text="Typer (Direct Refinement)", variable=app.mode_var, value="typer").pack(anchor="w", pady=2)
    ctk.CTkRadioButton(mode_frame, text="Prompt Engineer (AI Prompt Generation)", variable=app.mode_var, value="prompt_engineer").pack(anchor="w", pady=2)
    ctk.CTkRadioButton(mode_frame, text="Email (Compose Email)", variable=app.mode_var, value="email").pack(anchor="w", pady=2)
    ctk.CTkRadioButton(mode_frame, text="Coder (Code Generation)", variable=app.mode_var, value="coder").pack(anchor="w", pady=2)

    # Programming Language Selection (Coder Mode)
    ctk.CTkLabel(mode_frame, text="Programming Language (for Coder mode):").pack(anchor="w", pady=(15,5))
    available_languages = ["Python", "JavaScript", "TypeScript", "Go", "Java", "C#", "Rust", "PHP", "C++", "Swift", "Kotlin", "Ruby", "R", "Scala"]
    current_language = app.config.get("coder_config", {}).get("target_language", "Python")
    if current_language not in available_languages:
        current_language = "Python"
    app.coder_language_var = ctk.StringVar(value=current_language)
    language_menu = ctk.CTkOptionMenu(mode_frame, variable=app.coder_language_var, values=available_languages)
    language_menu.pack(fill="x", pady=(0,5))
    coder_explanation = "Select the programming language for code generation in Coder mode."
    ctk.CTkLabel(mode_frame, text=coder_explanation, font=("Arial", 10), text_color="gray").pack(anchor="w", pady=(0,10))

    # AI Tab - Models and Language
    ai_frame = ctk.CTkFrame(tab_ai, fg_color="transparent")
    ai_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # AI Service Selection
    ctk.CTkLabel(ai_frame, text="Text Refinement Service:").pack(anchor="w")
    app.service_var = ctk.StringVar(value=app.config.get("models_config", {}).get("text_processing_service", "Gemini"))
    service_menu = ctk.CTkOptionMenu(ai_frame, variable=app.service_var, values=["Mistral", "Gemini", "Ollama", "None (Raw ASR)"])
    service_menu.pack(fill="x", pady=(0,10))

    # Model Configurations
    models_conf = app.config.get("models_config", {})

    # Mistral Configuration
    mistral_config_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
    mistral_config_frame.pack(fill="x", pady=(5,0))
    ctk.CTkLabel(mistral_config_frame, text="Mistral Model:").pack(side="left", padx=(0, 5), pady=(0,5))
    mistral_custom_models = models_conf.get("mistral_custom_models", [])
    all_mistral_models = sorted(list(set([DEFAULT_MISTRAL_MODEL_NAME] + mistral_custom_models)))
    selected_mistral_model = models_conf.get("mistral_model_name", DEFAULT_MISTRAL_MODEL_NAME)
    if selected_mistral_model not in all_mistral_models: selected_mistral_model = DEFAULT_MISTRAL_MODEL_NAME
    app.mistral_model_var = ctk.StringVar(value=selected_mistral_model)
    app.mistral_model_menu = ctk.CTkOptionMenu(mistral_config_frame, variable=app.mistral_model_var, values=all_mistral_models, width=180)
    app.mistral_model_menu.pack(side="left", padx=(0,10), pady=(0,5))
    app.new_mistral_model_entry = ctk.CTkEntry(mistral_config_frame, placeholder_text="Add custom Mistral model")
    app.new_mistral_model_entry.pack(side="left", fill="x", expand=True, padx=(0,5), pady=(0,5))
    add_mistral_btn = ctk.CTkButton(mistral_config_frame, text="Add", width=40, command=lambda: add_custom_model(app, "mistral"))
    add_mistral_btn.pack(side="left", pady=(0,5))

    # Gemini Configuration
    gemini_config_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
    gemini_config_frame.pack(fill="x", pady=(5,0))
    ctk.CTkLabel(gemini_config_frame, text="Gemini Model: ").pack(side="left", padx=(0, 5), pady=(0,5))
    gemini_custom_models = models_conf.get("gemini_custom_models", [])
    all_gemini_models = sorted(list(set([DEFAULT_GEMINI_MODEL_NAME] + gemini_custom_models)))
    selected_gemini_model = models_conf.get("gemini_model_name", DEFAULT_GEMINI_MODEL_NAME)
    if selected_gemini_model not in all_gemini_models: selected_gemini_model = DEFAULT_GEMINI_MODEL_NAME
    app.gemini_model_var = ctk.StringVar(value=selected_gemini_model)
    app.gemini_model_menu = ctk.CTkOptionMenu(gemini_config_frame, variable=app.gemini_model_var, values=all_gemini_models, width=180)
    app.gemini_model_menu.pack(side="left", padx=(0,10), pady=(0,5))
    app.new_gemini_model_entry = ctk.CTkEntry(gemini_config_frame, placeholder_text="Add custom Gemini model")
    app.new_gemini_model_entry.pack(side="left", fill="x", expand=True, padx=(0,5), pady=(0,5))
    add_gemini_btn = ctk.CTkButton(gemini_config_frame, text="Add", width=40, command=lambda: add_custom_model(app, "gemini"))
    add_gemini_btn.pack(side="left", pady=(0,5))

    # Ollama Configuration
    ollama_config_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
    ollama_config_frame.pack(fill="x", pady=(5,0))
    icon_size = (20, 20)
    mistral_icon_image, gemini_icon_image, ollama_icon_image = None, None, None
    try:
        mistral_img_path = os.path.join(ASSETS_DIR, "mistral.png")
        if os.path.exists(mistral_img_path): mistral_icon_image = ctk.CTkImage(Image.open(mistral_img_path), size=icon_size)
    except Exception as e: print(f"Could not load mistral.png: {e}")
    try:
        gemini_img_path = os.path.join(ASSETS_DIR, "gemini.png")
        if os.path.exists(gemini_img_path): gemini_icon_image = ctk.CTkImage(Image.open(gemini_img_path), size=icon_size)
    except Exception as e: print(f"Could not load gemini.png: {e}")
    try:
        ollama_img_path = os.path.join(ASSETS_DIR, "ollama.png")
        if os.path.exists(ollama_img_path): ollama_icon_image = ctk.CTkImage(Image.open(ollama_img_path), size=icon_size)
    except Exception as e: print(f"Could not load ollama.png: {e}")
    if ollama_icon_image:
        ctk.CTkLabel(ollama_config_frame, image=ollama_icon_image, text="").pack(side="left", padx=(0, 5), pady=(0,5))
    ctk.CTkLabel(ollama_config_frame, text="Ollama Model:").pack(side="left", padx=(0, 5), pady=(0,5))

    # Initialize Ollama manager and get models
    if not hasattr(app, 'ollama_manager'):
        from backend.ai import initialize_ollama_manager
        initialize_ollama_manager(app)

    ollama_models = []
    if hasattr(app, 'ollama_manager') and app.ollama_manager.is_available:
        ollama_models = [model['name'] for model in app.ollama_manager.get_available_models()]

    if not ollama_models:
        ollama_models = ["No models available"]

    selected_ollama_model = models_conf.get("ollama_model_name", ollama_models[0] if ollama_models and ollama_models[0] != "No models available" else "")
    if selected_ollama_model not in ollama_models and ollama_models != ["No models available"]:
        selected_ollama_model = ollama_models[0] if ollama_models else ""

    app.ollama_model_var = ctk.StringVar(value=selected_ollama_model)
    app.ollama_model_menu = ctk.CTkOptionMenu(ollama_config_frame, variable=app.ollama_model_var, values=ollama_models, width=180)
    app.ollama_model_menu.pack(side="left", padx=(0,10), pady=(0,5))

    # Refresh button for Ollama models
    def refresh_ollama_models():
        if hasattr(app, 'ollama_manager'):
            app.ollama_manager.detect_ollama()
            ollama_models = []
            if app.ollama_manager.is_available:
                ollama_models = [model['name'] for model in app.ollama_manager.get_available_models()]
            if not ollama_models:
                ollama_models = ["No models available"]
            app.ollama_model_menu.configure(values=ollama_models)
            if ollama_models and ollama_models[0] != "No models available":
                app.ollama_model_var.set(ollama_models[0])
            print(f"Refreshed Ollama models: {ollama_models}")

    refresh_ollama_btn = ctk.CTkButton(ollama_config_frame, text="Refresh", width=60, command=refresh_ollama_models)
    refresh_ollama_btn.pack(side="left", padx=(10,0), pady=(0,5))

    # Ollama status indicator
    ollama_status_text = "Available" if hasattr(app, 'ollama_manager') and app.ollama_manager.is_available else "Not Available"
    ollama_status_color = "#4CAF50" if hasattr(app, 'ollama_manager') and app.ollama_manager.is_available else "#FF6B6B"
    app.ollama_status_label = ctk.CTkLabel(ollama_config_frame, text=f"Status: {ollama_status_text}", text_color=ollama_status_color)
    app.ollama_status_label.pack(side="left", padx=(10,0), pady=(0,5))

    # API Keys Section
    ctk.CTkLabel(ai_frame, text="API Keys:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(15,5))
    icon_size = (20, 20)
    mistral_icon_image, gemini_icon_image = None, None
    try:
        mistral_img_path = os.path.join(ASSETS_DIR, "mistral.png")
        if os.path.exists(mistral_img_path): mistral_icon_image = ctk.CTkImage(Image.open(mistral_img_path), size=icon_size)
    except Exception as e: print(f"Could not load mistral.png: {e}")
    try:
        gemini_img_path = os.path.join(ASSETS_DIR, "gemini.png")
        if os.path.exists(gemini_img_path): gemini_icon_image = ctk.CTkImage(Image.open(gemini_img_path), size=icon_size)
    except Exception as e: print(f"Could not load gemini.png: {e}")

    def toggle_visibility(entry_widget, button_widget):
        if entry_widget.cget("show") == "*":
            entry_widget.configure(show="")
            button_widget.configure(text="Hide")
        else:
            entry_widget.configure(show="*")
            button_widget.configure(text="Show")

    mistral_outer_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
    mistral_outer_frame.pack(fill="x", pady=(5,0))
    mistral_label_frame = ctk.CTkFrame(mistral_outer_frame, fg_color="transparent")
    mistral_label_frame.pack(side="left", fill="x", expand=True)
    if mistral_icon_image:
        ctk.CTkLabel(mistral_label_frame, image=mistral_icon_image, text="").pack(side="left", padx=(0,5))
    ctk.CTkLabel(mistral_label_frame, text="Mistral API Key:").pack(side="left", anchor="w")
    app.mistral_api_entry = ctk.CTkEntry(mistral_outer_frame, show="*")
    app.mistral_api_entry.insert(0, app.config.get("api_keys", {}).get("mistral", ""))
    app.mistral_api_entry.pack(side="left", fill="x", expand=True, padx=(5,5))
    mistral_toggle_btn = ctk.CTkButton(mistral_outer_frame, text="Show", width=60)
    mistral_toggle_btn.configure(command=lambda e=app.mistral_api_entry, b=mistral_toggle_btn: toggle_visibility(e, b))
    mistral_toggle_btn.pack(side="left", padx=(0,0))

    gemini_outer_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
    gemini_outer_frame.pack(fill="x", pady=(10,0))
    gemini_label_frame = ctk.CTkFrame(gemini_outer_frame, fg_color="transparent")
    gemini_label_frame.pack(side="left", fill="x", expand=True)
    if gemini_icon_image:
        ctk.CTkLabel(gemini_label_frame, image=gemini_icon_image, text="").pack(side="left", padx=(0,5))
    ctk.CTkLabel(gemini_label_frame, text="Gemini API Key:").pack(side="left", anchor="w")
    app.gemini_api_entry = ctk.CTkEntry(gemini_outer_frame, show="*")
    app.gemini_api_entry.insert(0, app.config.get("api_keys", {}).get("gemini", ""))
    app.gemini_api_entry.pack(side="left", fill="x", expand=True, padx=(5,5))
    gemini_toggle_btn = ctk.CTkButton(gemini_outer_frame, text="Show", width=60)
    gemini_toggle_btn.configure(command=lambda e=app.gemini_api_entry, b=gemini_toggle_btn: toggle_visibility(e, b))
    gemini_toggle_btn.pack(side="left", padx=(0,0))

    # Language Settings
    ctk.CTkLabel(ai_frame, text="Language Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(15,5))
    ctk.CTkLabel(ai_frame, text="Output Language:").pack(anchor="w", pady=(0,5))
    current_lang_code = app.config.get("language_config", {}).get("target_language", "en")
    current_lang_display = app.language_code_to_display.get(current_lang_code, "English")
    app.language_var = ctk.StringVar(value=current_lang_display)
    lang_menu = ctk.CTkOptionMenu(ai_frame, variable=app.language_var, values=list(app.language_display_to_code.keys()))
    lang_menu.pack(fill="x", pady=(0,10))

    # Language Preservation Option
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)
    app.preserve_original_languages_var = ctk.BooleanVar(value=preserve_original_languages)
    preserve_checkbox = ctk.CTkCheckBox(ai_frame, text="Preserve original languages (disable translation)", variable=app.preserve_original_languages_var)
    preserve_checkbox.pack(anchor="w", pady=(5,5))

    # Add explanatory text
    explanation_text = "When enabled: AI corrects ASR errors but keeps original language mix (e.g., French + English)\nWhen disabled: AI translates everything to the selected output language"
    ctk.CTkLabel(ai_frame, text=explanation_text, font=("Arial", 11), text_color="gray").pack(anchor="w", pady=(0,10))


    # System Tab - Audio, Logging, Hotkeys, UI Design
    system_frame = ctk.CTkFrame(tab_system, fg_color="transparent")
    system_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Audio Section
    ctk.CTkLabel(system_frame, text="Audio Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
    ctk.CTkLabel(system_frame, text="Input Audio Device:").pack(anchor="w", pady=(0,5))
    available_devices = get_audio_devices()
    current_device = app.config.get("audio_config", {}).get("device", "Default")
    if current_device not in available_devices:
        current_device = "Default"
    app.audio_device_var = ctk.StringVar(value=current_device)
    audio_menu = ctk.CTkOptionMenu(system_frame, variable=app.audio_device_var, values=available_devices)
    audio_menu.pack(fill="x", pady=(0,15))

    # Logging Section
    ctk.CTkLabel(system_frame, text="Logging Settings:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))

    logging_config = app.config.get("logging_config", {})
    app.logging_enabled_var = ctk.BooleanVar(value=logging_config.get("enabled", False))
    logging_enabled_checkbox = ctk.CTkCheckBox(
        system_frame,
        text="Enable logging",
        variable=app.logging_enabled_var
    )
    logging_enabled_checkbox.pack(anchor="w", pady=(0,5))

    # Log level selection
    ctk.CTkLabel(system_frame, text="Log Level:").pack(anchor="w", pady=(0,2))
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    current_level = logging_config.get("level", "INFO")
    app.log_level_var = ctk.StringVar(value=current_level)
    log_level_menu = ctk.CTkOptionMenu(system_frame, variable=app.log_level_var, values=log_levels)
    log_level_menu.pack(fill="x", pady=(0,5))

    # Max file size and backup count in one row
    file_settings_frame = ctk.CTkFrame(system_frame, fg_color="transparent")
    file_settings_frame.pack(fill="x", pady=(0,5))

    # Max file size
    size_frame = ctk.CTkFrame(file_settings_frame, fg_color="transparent")
    size_frame.pack(side="left", fill="x", expand=True, padx=(0,5))
    ctk.CTkLabel(size_frame, text="Max Log Size:").pack(anchor="w")
    current_size_mb = logging_config.get("max_file_size", 10485760) // (1024 * 1024)
    app.log_size_var = ctk.StringVar(value=str(current_size_mb))
    size_menu = ctk.CTkOptionMenu(size_frame, variable=app.log_size_var, values=["5", "10", "25", "50", "100"])
    size_menu.pack(fill="x")

    # Backup count
    backup_frame = ctk.CTkFrame(file_settings_frame, fg_color="transparent")
    backup_frame.pack(side="left", fill="x", expand=True, padx=(5,0))
    ctk.CTkLabel(backup_frame, text="Backup Files:").pack(anchor="w")
    current_backups = logging_config.get("backup_count", 3)
    app.log_backups_var = ctk.StringVar(value=str(current_backups))
    backup_menu = ctk.CTkOptionMenu(backup_frame, variable=app.log_backups_var, values=["1", "2", "3", "5", "10"])
    backup_menu.pack(fill="x")

    # Logging explanation
    logging_explanation = "Log files rotate automatically. Disable logging to save disk space."
    ctk.CTkLabel(system_frame, text=logging_explanation, font=("Arial", 9), text_color="gray").pack(anchor="w", pady=(0,15))

    # Hotkeys Section
    ctk.CTkLabel(system_frame, text="Hotkeys:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
    app.current_hotkey_label = ctk.CTkLabel(system_frame, text="Loading...", font=("Consolas", 12))
    app.current_hotkey_label.pack(anchor="w", pady=(0,5))
    app.set_hotkey_button = ctk.CTkButton(system_frame, text="Change Hotkey", command=lambda: start_hotkey_capture(app))
    app.set_hotkey_button.pack(anchor="w", pady=(0,15))
    update_hotkey_display(app)

    # UI Design Section
    ctk.CTkLabel(system_frame, text="UI Design:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))

    current_ui_design = app.config.get("ui_config", {}).get("ui_design", "default")
    app.ui_design_var = ctk.StringVar(value=current_ui_design)

    def on_ui_design_change():
        selected_design = app.ui_design_var.get()
        app.config["ui_config"]["ui_design"] = selected_design
        app._save_config()
        app._switch_ui_design(selected_design)

    # UI Design Options
    ui_options_frame = ctk.CTkFrame(system_frame, fg_color="transparent")
    ui_options_frame.pack(fill="x", pady=(0,5))

    default_radio = ctk.CTkRadioButton(
        ui_options_frame,
        text="Default UI",
        variable=app.ui_design_var,
        value="default",
        command=on_ui_design_change
    )
    default_radio.pack(anchor="w", pady=2)

    modern_radio = ctk.CTkRadioButton(
        ui_options_frame,
        text="Modern UI (Pill Button)",
        variable=app.ui_design_var,
        value="modern",
        command=on_ui_design_change
    )
    modern_radio.pack(anchor="w", pady=2)

    # UI design explanation
    ui_explanation = "Modern UI provides animated pill buttons. Changes take effect immediately."
    ctk.CTkLabel(system_frame, text=ui_explanation, font=("Arial", 9), text_color="gray").pack(anchor="w", pady=(0,10))

    # Streaming Tab
    streaming_frame = ctk.CTkFrame(tab_streaming, fg_color="transparent")
    streaming_frame.pack(pady=10, padx=10, fill="x")
    
    # Streaming Mode Toggle
    ctk.CTkLabel(streaming_frame, text="Streaming Mode:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
    streaming_config = app.config.get("streaming_config", {})
    app.streaming_enabled_var = ctk.BooleanVar(value=streaming_config.get("enabled", False))
    streaming_toggle = ctk.CTkCheckBox(streaming_frame, text="Enable real-time streaming during text processing", variable=app.streaming_enabled_var)
    streaming_toggle.pack(anchor="w", pady=(0,15))
    
    # Confidence Threshold
    ctk.CTkLabel(streaming_frame, text="Correction Confidence Threshold:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
    ctk.CTkLabel(streaming_frame, text="Only apply corrections when confidence is above this threshold", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0,5))
    app.confidence_threshold_var = ctk.DoubleVar(value=streaming_config.get("confidence_threshold", 0.5))
    confidence_slider = ctk.CTkSlider(streaming_frame, from_=0.1, to=1.0, variable=app.confidence_threshold_var, number_of_steps=18)
    confidence_slider.pack(fill="x", pady=(0,5))
    app.confidence_value_label = ctk.CTkLabel(streaming_frame, text=f"{app.confidence_threshold_var.get():.1f}")
    app.confidence_value_label.pack(anchor="w", pady=(0,15))
    confidence_slider.configure(command=lambda value: app.confidence_value_label.configure(text=f"{value:.1f}"))
    
    # Context Sensitivity
    app.context_sensitivity_var = ctk.BooleanVar(value=streaming_config.get("context_sensitivity", True))
    context_toggle = ctk.CTkCheckBox(streaming_frame, text="Enable context-aware correction analysis", variable=app.context_sensitivity_var)
    context_toggle.pack(anchor="w", pady=(0,10))
    
    # Show Corrections
    app.show_corrections_var = ctk.BooleanVar(value=streaming_config.get("show_corrections", True))
    corrections_toggle = ctk.CTkCheckBox(streaming_frame, text="Show correction indicators in streaming widget", variable=app.show_corrections_var)
    corrections_toggle.pack(anchor="w", pady=(0,10))

    # Save Button
    save_button = ctk.CTkButton(app.settings_window, text="Save & Close", command=lambda: save_settings_from_dialog(app))
    save_button.pack(pady=(15,10), side="bottom")
    app.settings_window.protocol("WM_DELETE_WINDOW", lambda: on_settings_close(app))

def add_custom_model(app, model_type: str):
    if model_type == "mistral":
        entry_widget = app.new_mistral_model_entry
        custom_list_key = "mistral_custom_models"
        default_model_name = DEFAULT_MISTRAL_MODEL_NAME
        option_menu_widget = app.mistral_model_menu
        model_var = app.mistral_model_var
    elif model_type == "gemini":
        entry_widget = app.new_gemini_model_entry
        custom_list_key = "gemini_custom_models"
        default_model_name = DEFAULT_GEMINI_MODEL_NAME
        option_menu_widget = app.gemini_model_menu
        model_var = app.gemini_model_var
    else:
        return

    new_model = entry_widget.get().strip()
    if new_model:
        models_config = app.config.setdefault("models_config", {})
        custom_models = models_config.get(custom_list_key, [])
        if new_model not in custom_models and new_model != default_model_name:
            custom_models.append(new_model)
            models_config[custom_list_key] = custom_models
            updated_model_list = [default_model_name] + custom_models
            unique_model_list = sorted(list(set(updated_model_list))) 
            option_menu_widget.configure(values=unique_model_list)
            model_var.set(new_model)
            entry_widget.delete(0, tk.END)
            print(f"Added custom {model_type} model: {new_model}")
        else:
            print(f"{model_type.capitalize()} model '{new_model}' is default or already in custom list.")
            entry_widget.delete(0, tk.END)
    else:
        print(f"No model name entered for {model_type}.")

def update_hotkey_display(app):
    hotkey_conf = app.config.get("hotkey_config", {})
    mods = hotkey_conf.get("modifiers", [])
    key = hotkey_conf.get("key", "")
    display_key = key
    if len(key) == 1 and 1 <= ord(key) <= 26:
        display_key = chr(ord(key) + 64)
    hotkey_str = " + ".join([m.capitalize() for m in mods] + [display_key.capitalize()])
    app.current_hotkey_label.configure(text=hotkey_str)

def start_hotkey_capture(app):
    app.set_hotkey_button.configure(state="disabled", text="Press any key combination...")
    app.hotkey_capture_listener = keyboard.Listener(on_press=lambda key: on_capture_key_press(app, key))
    app.hotkey_capture_listener.start()

def on_capture_key_press(app, key):
    modifiers = []
    key_str = ""
    if any(k in app.currently_pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
        modifiers.append("ctrl")
    if any(k in app.currently_pressed_keys for k in (keyboard.Key.shift_l, keyboard.Key.shift_r)):
        modifiers.append("shift")
    if any(k in app.currently_pressed_keys for k in (keyboard.Key.alt_l, keyboard.Key.alt_r)):
        modifiers.append("alt")

    if isinstance(key, keyboard.Key):
        if key not in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                       keyboard.Key.shift_l, keyboard.Key.shift_r,
                       keyboard.Key.alt_l, keyboard.Key.alt_r):
            key_str = key.name
    elif isinstance(key, keyboard.KeyCode) and key.char is not None:
        key_str = key.char

    if key_str:
        app.config["hotkey_config"] = {"modifiers": sorted(list(set(modifiers))), "key": key_str}
        app.master.after(0, update_hotkey_display, app)
        app.master.after(0, app.set_hotkey_button.configure, {"state": "normal", "text": "Click to Set New Hotkey"})
        if app.hotkey_capture_listener:
            app.hotkey_capture_listener.stop()
        return False

def save_settings_from_dialog(app):
    if app.settings_window is None or not app.settings_window.winfo_exists():
        return

    app.config.setdefault("api_keys", {})
    app.config.setdefault("mode_config", {})
    app.config.setdefault("models_config", {})
    app.config.setdefault("language_config", {})
    app.config.setdefault("audio_config", {})
    app.config.setdefault("hotkey_config", {})
    app.config.setdefault("streaming_config", {})

    # Get API key values
    mistral_key = app.mistral_api_entry.get()
    gemini_key = app.gemini_api_entry.get()

    app.config["api_keys"]["mistral"] = mistral_key
    app.config["api_keys"]["gemini"] = gemini_key

    app.config["mode_config"]["operation_mode"] = app.mode_var.get()
    app.config["models_config"]["text_processing_service"] = app.service_var.get()
    app.config["models_config"]["mistral_model_name"] = app.mistral_model_var.get()
    app.config["models_config"]["gemini_model_name"] = app.gemini_model_var.get()
    app.config["models_config"]["ollama_model_name"] = app.ollama_model_var.get()
    selected_display_language = app.language_var.get()
    app.config["language_config"]["target_language"] = app.language_display_to_code.get(selected_display_language, "en")
    app.config["language_config"]["preserve_original_languages"] = app.preserve_original_languages_var.get()
    app.config["audio_config"]["device"] = app.audio_device_var.get()
    app.config["streaming_config"]["enabled"] = app.streaming_enabled_var.get()
    app.config["streaming_config"]["confidence_threshold"] = app.confidence_threshold_var.get()
    app.config["streaming_config"]["context_sensitivity"] = app.context_sensitivity_var.get()
    app.config["streaming_config"]["show_corrections"] = app.show_corrections_var.get()

    # Save coder config
    app.config.setdefault("coder_config", {})
    app.config["coder_config"]["target_language"] = app.coder_language_var.get()

    # Save logging config
    app.config.setdefault("logging_config", {})
    app.config["logging_config"]["enabled"] = app.logging_enabled_var.get()
    app.config["logging_config"]["level"] = app.log_level_var.get()
    app.config["logging_config"]["max_file_size"] = int(app.log_size_var.get()) * 1024 * 1024  # Convert MB to bytes
    app.config["logging_config"]["backup_count"] = int(app.log_backups_var.get())

    app._save_config()

    # Reconfigure logging with new settings
    from backend.logger import setup_logging
    logging_config = app.config.get("logging_config", {})
    setup_logging(logging_config)

    app._update_hotkey_from_config()
    on_settings_close(app)

def on_settings_close(app):
    if app.hotkey_capture_listener and app.hotkey_capture_listener.is_alive():
        app.hotkey_capture_listener.stop()
    app.hotkey_capture_listener = None
    
    if app.settings_window is not None and app.settings_window.winfo_exists():
        app.settings_window.grab_release()
        app.settings_window.destroy()
    app.settings_window = None 