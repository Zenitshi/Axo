"""
Security utilities for Axo application.
Handles encryption/decryption of sensitive configuration data.
"""
from cryptography.fernet import Fernet
import base64
import json
import os
import hashlib
from typing import Dict, Any, Optional


class SecureConfig:
    """
    Handles encryption and decryption of sensitive configuration data.
    Uses a master password derived key for encryption.
    """

    # Default master password - CHANGE THIS TO YOUR DESIRED PASSWORD
    DEFAULT_MASTER_PASSWORD = "AXO"

    @staticmethod
    def derive_key(password: str) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: User-provided master password

        Returns:
            32-byte encryption key
        """
        # Use a simple but effective key derivation
        # In production, consider using proper PBKDF2 with salt
        key_seed = password.encode() + b"axo_salt_2024"
        key = hashlib.sha256(key_seed).digest()
        return base64.urlsafe_b64encode(key)

    @staticmethod
    def encrypt_api_keys(config_path: str, password: str) -> bool:
        """
        Encrypt API keys in the configuration file.

        Args:
            config_path: Path to config.json
            password: Master password for encryption

        Returns:
            True if encryption successful, False otherwise
        """
        try:
            # Read current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Check if already encrypted
            if config.get('encrypted', False):
                print("Configuration is already encrypted")
                return True

            # Get API keys
            api_keys = config.get('api_keys', {})
            if not api_keys:
                print("No API keys to encrypt")
                return True

            # Derive encryption key
            key = SecureConfig.derive_key(password)
            fernet = Fernet(key)

            # Encrypt each API key
            encrypted_keys = {}
            for service, api_key in api_keys.items():
                if api_key and isinstance(api_key, str):  # Only encrypt non-empty string keys
                    try:
                        encrypted_keys[service] = fernet.encrypt(api_key.encode()).decode()
                    except Exception as e:
                        print(f"Failed to encrypt {service} key: {e}")
                        encrypted_keys[service] = api_key  # Keep original if encryption fails
                else:
                    encrypted_keys[service] = api_key

            # Update config
            config['api_keys'] = encrypted_keys
            config['encrypted'] = True

            # Write back encrypted config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print("API keys encrypted successfully")
            return True

        except Exception as e:
            print(f"Failed to encrypt API keys: {e}")
            return False

    @staticmethod
    def decrypt_api_keys(config: Dict[str, Any], password: str) -> Dict[str, Any]:
        """
        Decrypt API keys from configuration.

        Args:
            config: Configuration dictionary (potentially encrypted)
            password: Master password for decryption

        Returns:
            Configuration with decrypted API keys
        """
        try:
            if not config.get('encrypted', False):
                return config  # Not encrypted, return as-is

            # Derive decryption key
            key = SecureConfig.derive_key(password)
            fernet = Fernet(key)

            # Decrypt API keys
            decrypted_config = config.copy()
            decrypted_keys = {}

            api_keys = config.get('api_keys', {})
            for service, encrypted_key in api_keys.items():
                if encrypted_key and isinstance(encrypted_key, str):
                    try:
                        decrypted_keys[service] = fernet.decrypt(encrypted_key.encode()).decode()
                    except Exception as e:
                        print(f"Failed to decrypt {service} key, keeping encrypted: {e}")
                        decrypted_keys[service] = encrypted_key  # Keep encrypted if decryption fails
                else:
                    decrypted_keys[service] = encrypted_key

            decrypted_config['api_keys'] = decrypted_keys
            decrypted_config['encrypted'] = False  # Mark as decrypted for runtime use

            return decrypted_config

        except Exception as e:
            print(f"Failed to decrypt API keys: {e}")
            # Return original config if decryption fails
            return config

    @staticmethod
    def get_password() -> str:
        """
        Get the master password for encryption/decryption.
        Uses the default password defined in DEFAULT_MASTER_PASSWORD.

        To change the password, modify DEFAULT_MASTER_PASSWORD above.

        Returns:
            The master password string
        """
        return SecureConfig.DEFAULT_MASTER_PASSWORD
