# Axo: Intelligent Voice Dictation & Ai Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Example of how to embed an image (replace with an actual screenshot if available)https://i.ibb.co/m5NgFLv6/AXO-BANNER.png https://i.ibb.co/bgnJBKtg/Axo-Image.png-->
![Axo Image](https://i.ibb.co/bgnJBKtg/Axo-Image.png)

## Description

Axo is a desktop application designed to streamline your workflow by providing powerful voice dictation, intelligent text refinement, AI prompt engineering, and code generation capabilities. It listens to your voice, transcribes it using NVIDIA's NeMo ASR, and then leverages Large Language Models (currently Gemini, Mistral and Ollama models) to correct, translate, transform, or generate code from your speech into effective prompts and functional code.

The application features a sophisticated modern UI with real-time audio visualization, global hotkeys for quick access, and an enhanced settings panel. Whether you need to quickly type out thoughts, draft content in a specific language, craft sophisticated prompts for advanced AI models, or generate code from natural language descriptions, Axo aims to be your go-to assistant.

## Key Features

*   **High-Quality Speech-to-Text:** Utilizes NVIDIA NeMo ASR (`nvidia/parakeet-tdt-0.6b-v3`) for accurate transcription.
*   **Intelligent Text Refinement (via Mistral AI, Gemini & Ollama):**
    *   **Typer Mode:** Corrects ASR errors (stutters, misspellings), adds punctuation, translates to your target language, preserves original meaning and style, and formats lists (e.g., bullet points).
    *   **Prompt Engineer Mode:** Transforms your spoken ideas into well-structured XML prompts optimized for other advanced AI models (e.g., GPT, Gemini, Claude) or Ide's (eg. Cursor, Claude Code, Codex, Cline...).
    *   **Email Mode:** Transforms your spoken input into professionally formatted emails with proper structure, salutations, and closing.
    *   **Coder Mode:** Translates natural language descriptions into working, production-ready code in multiple programming languages (Python, JavaScript, Java, C++, and more).
*   **Real-time Audio Visualization:** Engaging UI with a pulsing indicator and audio bars that react to your voice.
*   **Modern UI Design:** Sophisticated pill-shaped interface with smooth animations and multiple visual states.
*   **Global Hotkeys:**
    *   `Ctrl + Shift + Space`: Start/Stop recording (customizable via settings).
    *   `Ctrl + Shift + H`: Open settings dialog.
    *   `Ctrl + Shift + X`: Toggle UI visibility (hide/show).
*   **Enhanced Configuration Panel:**
    *   Set API keys (Mistral, Gemini) or use local Ollama models.
    *   Choose operation mode (Typer, Prompt Engineer, Email, Coder).
    *   Select target language for output (16 languages supported including English, Arabic, French, Spanish, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Hindi, Dutch, Polish, Turkish, Swedish).
    *   Configure programming language for Coder mode.
    *   Customize hotkeys through an intuitive capture system.
    *   Choose audio input device selection.
*   **Security:** API key encryption with master password protection and secure configuration handling.
*   **Advanced Logging:** Rotating file handler with configurable log levels and structured logging.
*   **Clipboard & Auto-Paste:** Automatically copies the final text to your clipboard and attempts to paste it into your active window.
*   **Audio Cues:** Optional sounds for recording start/stop (requires `pydub`).
*   **Real-time Streaming:** View AI processing results as they are generated, token by token.
*   **Persistent Configuration:** Enhanced `config.json` with encryption support and new configuration sections.

## Model Recommendations

The following table provides optimized model recommendations for different operation modes and parameter ranges (subject to change as models evolve):

| Mode | Low Level (<8B Parameters) | Moderate Level (8-32B Parameters) | High Level (>32B Parameters) | Mistral | Gemini |
|------|---------------------------|-----------------------------------|-----------------------------|---------|--------|
| Typer Mode | gemma3n:e4b; gemma3:4b; deepseek-r1:8b/7b | mistral-small3.2:24b; gpt-oss:20b; qwen3:30b | qwen3:235b; gpt-oss:120b | mistral-medium-latest | gemini-2.5-flash-lite |
| Prompt Engineer Mode | gemma3n:e4b; qwen3:4b; deepseek-r1:8b/7b | mistral-small3.2:24b; gpt-oss:20b; qwen3:30b | qwen3:235b; gpt-oss:120b | mistral-medium-latest | gemini-2.5-pro |
| Email Mode | gemma3:4b; gemma3n:e4b; deepseek-r1:8b/7b | mistral-small3.2:24b; gpt-oss:20b; qwen3:30b | qwen3:235b; gpt-oss:120b | mistral-medium-latest | gemini-2.5-pro |
| Coder Mode | qwen2.5-coder:7b; gemma3n:e4b; deepseek-r1:8b/7b | devstral:24b; gpt-oss:20b; qwen3-coder:30b | qwen3:235b; gpt-oss:120b | codestral-latest | gemini-2.5-pro |

## How It Works

1.  **Voice Input:** User activates recording via a global hotkey.
2.  **Audio Capture:** Axo records audio from the microphone, displaying real-time visualizations.
3.  **ASR Transcription:** The recorded audio is processed by the local NVIDIA NeMo ASR model to generate raw text.
4.  **Text Processing (Optional):**
    *   If an AI service is configured and enabled:
        *   **Typer Mode:** The raw text is sent for correction, punctuation, translation, and light formatting.
        *   **Prompt Engineer Mode:** The raw text is interpreted to generate a structured XML prompt for another AI.
        *   **Email Mode:** The raw text is transformed into professionally formatted emails.
        *   **Coder Mode:** The raw text is translated into functional code in the specified programming language.
5.  **Output:** The processed text is copied to the clipboard and an attempt is made to paste it into the currently active application.

## PC Specifications

### Minimum System Requirements:
- **Operating System:** Windows 10/11 (64-bit), Linux (Ubuntu 20.04+), macOS
- **CPU:** Dual-core Intel Core i3/i5 or AMD Ryzen 3 equivalent
- **RAM:** 8 GB RAM
- **GPU (for ASR):** NVIDIA GeForce GTX 1050 with 4GB VRAM (CPU-only operation supported but slower)
- **Storage:** 50 GB HDD/SSD
- **Internet:** Broadband connection (for API services and initial model download)
- **Other:** Microphone

### Recommended System Requirements:
- **Operating System:** Windows 10/11 (64-bit), Linux (Ubuntu 20.04+)
- **CPU:** Quad-core Intel Core i5/i7 or AMD Ryzen 5/7 equivalent
- **RAM:** 16 GB RAM or more
- **GPU (for ASR):** NVIDIA GeForce RTX 2060 or better with 6GB+ VRAM
- **Storage:** 256 GB NVMe SSD or faster
- **Internet:** Stable, fast broadband connection
- **Other:** High-quality USB microphone

## Installation

### Prerequisites
- Python 3.8 or newer
- `pip` (Python package installer)
- For audio cues (optional): `ffmpeg` or `libav`

### Steps

1. **Clone or Download:**
   ```bash
   git clone <repository-url>
   cd Axo
   ```

2. **Create Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install customtkinter nemo_toolkit[asr] sounddevice numpy wave pyperclip pyautogui pynput mistralai google-generativeai ollama pillow cryptography
   ```

   For audio cues (optional):
   
   ```bash
   pip install pydub simpleaudio
   ```
   
<details>
<summary>Click to expand: Important Notes on NeMo ASR Installation</summary>

**⚠️ Important Notes on NeMo ASR Installation:**
- **Windows Users:** Installing `nemo_toolkit[asr]` can be complex and may require additional setup due to C++ compilation dependencies. Ensure you have:
  - **NVIDIA GPU and CUDA:** A compatible NVIDIA GPU with CUDA Toolkit installed (visit [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads) for your OS).
  - **Microsoft Visual Studio:** Install Visual Studio 2019 or later with "Desktop development with C++" workload. You may need to run `pip install` from a Visual Studio Developer Command Prompt to set up the compiler environment properly.
  - **FFmpeg (for Audio Processing):** Download and install FFmpeg from [FFmpeg.org](https://ffmpeg.org/download.html). Add it to your system PATH. This is often required for audio handling in ASR pipelines.
- **Common Issues:** If you encounter compiler errors (e.g., "invalid numeric argument" or missing MSVC), ensure your Visual Studio Build Tools are correctly configured.

</details>

4. **Security Setup:**
   - First run will prompt for a master password to encrypt API keys
   - API keys are encrypted using Fernet encryption with PBKDF2 key derivation

5. **Configure Axo:**
   - Run `Axo.py` or `Axo.bat` (Windows)
   - Press `Ctrl + Shift + H` to open settings
   - Configure operation mode, target language, and programming language (for Coder mode)
   - **Configure API keys:** Go to the "Ai" tab and enter your Mistral or Gemini API keys if you wish to use cloud-based text refinement features. Alternatively, install Ollama for local processing.
    *   **Ollama Setup (Optional):** For local AI processing:
        1. Download and install [Ollama](https://ollama.com/)
        2. Install Python library: `pip install ollama`
        3. Pull a model: `ollama pull qwen3:4b` (or any supported model)
        4. In the Models tab, the Ollama model list will be blank until you refresh and have at least one model downloaded. If you have only one, it will be picked automatically. There is no default model.
        5. Select "Ollama" as your text processing service in the Models tab
    *   **Mode & Language:** Configure your preferred operation mode and output language.
    *   Save settings. Your `config.json` will be updated.

### Example Configuration Structure:
```json
{
  "api_keys": {
    "mistral": "ENCRYPTED_API_KEY",
    "gemini": "ENCRYPTED_API_KEY"
  },
  "models_config": {
    "text_processing_service": "Ollama",
    "mistral_model_name": "codestral-latest",
    "gemini_model_name": "gemini-2.5-flash-lite-preview-06-17",
    "ollama_model_name": "gemma3:4b-it-qat"
  },
  "mode_config": {
    "operation_mode": "coder"
  },
  "coder_config": {
    "target_language": "Python"
  },
  "hotkey_config": {
    "modifiers": [
      "ctrl",
      "shift"
    ],
    "key": "space"
  },
  "audio_config": {
    "device": "Default"
  },
  "streaming_config": {
    "enabled": false,
    "confidence_threshold": 0.5,
    "context_sensitivity": true,
    "show_corrections": true
  },
  "ui_config": {
    "design_theme": "modern",
    "ui_design": "modern"
  },
  "logging_config": {
    "enabled": false,
    "level": "INFO",
    "max_file_size": 10485760,
    "backup_count": 3
  },
  "encrypted": true
}
```

## Usage

1. **Run the Application:**
   ```bash
   python Axo.py
   # or on Windows: Axo.bat
   ```

2. **Basic Usage:**
   - Axo window appears (bottom-center by default)
   - **Initial State:** Shows ready indicator
   - **Start Recording:** Hold `Ctrl + Shift + Space`
   - **Speak:** Describe what you want to write or code
   - **Stop Recording:** Release `Ctrl + Shift + Space`
   - **Output:** Text/code copied to clipboard and pasted to active application

3. **Operation Modes:**
   - **Typer:** Speak naturally, get corrected text
   - **Prompt Engineer:** Describe what you want, get structured prompts
   - **Email:** Dictate email content, get formatted email
   - **Coder:** Describe code functionality, get working code

4. **Settings Access:**
   - Press `Ctrl + Shift + H` anytime to open settings
   - Configure API keys, models, languages, and preferences

<details>
<summary>Click to expand: Quick Desktop Launch Tip for Windows Users</summary>

For Windows users who want a convenient desktop shortcut without opening VS Code or your IDE every time:

1. **Create a Launcher Batch File:**
   - Open Notepad or any text editor.
   - Copy and paste the following template, replacing `YOUR_FULL_PATH_TO_AXO_FOLDER` with your actual Axo project folder path (e.g., `C:\Users\YourUsername\Documents\Axo`):

     ```
     @echo off
     set "APP_DIR=YOUR_FULL_PATH_TO_AXO_FOLDER"

     echo Starting Axo (python Axo.py)...
     start "Axo Dictation App" cmd /k "cd /d "%APP_DIR%" && python Axo.py"

     echo.
     echo You can close this window now.
     pause >nul
     ```

   - Save the file as `Axo.bat` in your Axo project folder (or anywhere convenient).

2. **Create a Desktop Shortcut:**
   - Right-click on the `Axo.bat` file and select "Create shortcut."
   - Drag the shortcut to your desktop (or any preferred location).
   - (Optional) Right-click the shortcut, select "Properties," and under "Shortcut" tab, click "Change Icon" to use `Axo Icon.ico` from your `assets` folder for a custom icon.

3. **Launch Axo Easily:**
   - Double-click the desktop shortcut anytime to launch Axo without navigating folders or opening your IDE.

This provides a seamless, one-click experience tailored to your specific folder structure, making Axo feel like a native desktop application.
</details>

## Roadmap

### Current Features ✅
- ✅ Core voice dictation using NVIDIA NeMo ASR
- ✅ Text refinement and prompt engineering via Mistral AI and Gemini integration
- ✅ Four distinct operation modes: "Typer", "Prompt Engineer", "Email", and "Coder"
- ✅ **NEW: Coder Mode for code generation from natural language**
- ✅ **NEW: API key encryption and security features**
- ✅ **NEW: Advanced logging with rotating file handler**
- ✅ **NEW: Modern pill-shaped UI with smooth animations**
- ✅ **NEW: Enhanced configuration system**
- ✅ Real-time streaming for all AI services
- ✅ Ollama integration for local AI processing
- ✅ 16 language support for translation
- ✅ Global hotkeys with full customization
- ✅ Audio device selection
- ✅ Custom model selection for all services
- ✅ Automatic clipboard copying and paste functionality
- ✅ Optional audio cues for recording feedback
- ✅ Draggable, always-on-top UI
- ✅ Persistent encrypted configuration

### Future Enhancements 🚀
- Database that stores sessions.