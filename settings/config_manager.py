import json
import os
from backend.ai import initialize_mistral_client, initialize_gemini_client, initialize_ollama_manager
from backend.security import SecureConfig

CONFIG_FILE = "config.json"
DEFAULT_MISTRAL_MODEL_NAME = "mistral-medium-latest"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.0-flash"

def get_master_password() -> str:
    """Get the master password from the security configuration."""
    return SecureConfig.get_password()

def load_config():
    default_config = {
        "api_keys": {"mistral": "", "gemini": ""},
        "models_config": {
            "text_processing_service": "Gemini",
            "mistral_model_name": DEFAULT_MISTRAL_MODEL_NAME,
            "gemini_model_name": DEFAULT_GEMINI_MODEL_NAME,
            "ollama_model_name": "",  # No default model
            "mistral_custom_models": [],
            "gemini_custom_models": []
        },
        "language_config": {"target_language": "en", "preserve_original_languages": True},
        "mode_config": {"operation_mode": "typer"},
        "coder_config": {"target_language": "Python"},
        "hotkey_config": {"modifiers": ["ctrl", "shift"], "key": "space"},
        "audio_config": {"device": "Default"},
        "streaming_config": {
            "enabled": False,
            "confidence_threshold": 0.5,
            "context_sensitivity": True,
            "show_corrections": True
        },
        "ui_config": {
            "design_theme": "modern",
            "ui_design": "modern"
        },
        "logging_config": {
            "enabled": False,
            "level": "INFO",
            "max_file_size": 10485760,  # 10MB
            "backup_count": 3
        }
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Handle encrypted config
            if loaded_config.get('encrypted', False):
                try:
                    password = get_master_password()
                    loaded_config = SecureConfig.decrypt_api_keys(loaded_config, password)
                except Exception as e:
                    print(f"Failed to decrypt config: {e}. Using encrypted values as-is.")
                    # Continue with encrypted config, API calls will fail but app won't crash

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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print(f"Default configuration saved to {CONFIG_FILE}.")
    except Exception as e:
        print(f"Error creating default {CONFIG_FILE}: {e}")
    return default_config

def save_config(app):
    try:
        # Create a copy of config for saving (without decrypted keys in memory)
        config_to_save = app.config.copy()

        # Encrypt API keys before saving
        try:
            # Get the master password
            password = get_master_password()

            # Remove the 'encrypted' flag temporarily for re-encryption
            temp_config = config_to_save.copy()
            if 'encrypted' in temp_config:
                del temp_config['encrypted']

            # Save updated config first
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            # Encrypt and save
            success = SecureConfig.encrypt_api_keys(CONFIG_FILE, password)
            if not success:
                print("Warning: Failed to encrypt API keys, saving unencrypted")
                # Fall back to regular save
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Encryption failed, saving unencrypted: {e}")
            # Fall back to regular save
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)

        print("Configuration saved.")
        app.mistral_api_key = app.config.get("api_keys", {}).get("mistral")
        app.gemini_api_key = app.config.get("api_keys", {}).get("gemini")
        initialize_mistral_client(app)
        initialize_gemini_client(app)
        initialize_ollama_manager(app)
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}") 