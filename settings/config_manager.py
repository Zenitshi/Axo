import json
import os
from backend.ai import initialize_mistral_client, initialize_gemini_client, initialize_ollama_manager

CONFIG_FILE = "config.json"
DEFAULT_MISTRAL_MODEL_NAME = "mistral-medium-latest"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.0-flash"

def load_config():
    default_config = {
        "api_keys": {"mistral": "", "gemini": ""},
        "models_config": {
            "text_processing_service": "Mistral",
            "mistral_model_name": DEFAULT_MISTRAL_MODEL_NAME,
            "gemini_model_name": DEFAULT_GEMINI_MODEL_NAME,
            "ollama_model_name": "",  # No default model
            "mistral_custom_models": [],
            "gemini_custom_models": []
        },
        "language_config": {"target_language": "en", "preserve_original_languages": True},
        "mode_config": {"operation_mode": "typer"},
        "hotkey_config": {"modifiers": ["ctrl", "shift"], "key": "space"},
        "audio_config": {"device": "Default"},
        "streaming_config": {
            "enabled": False,
            "confidence_threshold": 0.5,
            "context_sensitivity": True,
            "show_corrections": True
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                def update_dict(target, source):
                    for key, value in source.items():
                        if key not in target:
                            target[key] = value
                        elif isinstance(value, dict) and isinstance(target.get(key), dict):
                            update_dict(target[key], value)
                update_dict(loaded_config, default_config)
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

def save_config(app):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(app.config, f, indent=2)
        print("Configuration saved.")
        app.mistral_api_key = app.config.get("api_keys", {}).get("mistral")
        app.gemini_api_key = app.config.get("api_keys", {}).get("gemini")
        initialize_mistral_client(app)
        initialize_gemini_client(app)
        initialize_ollama_manager(app)
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}") 