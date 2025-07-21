# Axo: Intelligent Voice Dictation & Prompt Engineering Assistant

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Example of how to embed an image (replace with an actual screenshot if available)https://i.ibb.co/m5NgFLv6/AXO-BANNER.png https://i.ibb.co/bgnJBKtg/Axo-Image.png-->
![Axo Image](https://i.ibb.co/bgnJBKtg/Axo-Image.png)


## Description

Axo is a desktop application designed to streamline your workflow by providing powerful voice dictation, intelligent text refinement, and AI prompt engineering capabilities. It listens to your voice, transcribes it using NVIDIA's NeMo ASR, and then leverages Large Language Models (currently Mistral AI) to correct, translate, or transform your speech into effective prompts for other AI systems.

The application features a minimalist, draggable UI with real-time audio visualization, global hotkeys for quick access, and a settings panel to customize its behavior. Whether you need to quickly type out thoughts, draft content in a specific language, or craft sophisticated prompts for advanced AI models, Axo aims to be your go-to assistant.

## Key Features

*   **High-Quality Speech-to-Text:** Utilizes NVIDIA NeMo ASR (`parakeet-tdt-0.6b-v2`) for accurate transcription.
*   **Intelligent Text Refinement (via Mistral AI, Gemini & Ollama):**
    *   **Typer Mode:** Corrects ASR errors (stutters, misspellings), adds punctuation, translates to your target language, preserves original meaning and style, and formats lists (e.g., bullet points).
    *   **Prompt Engineer Mode:** Transforms your spoken ideas into well-structured XML prompts optimized for other advanced AI models (e.g., GPT-4, Gemini, Claude).
    *   **Email Mode:** Transforms your spoken input into professionally formatted emails with proper structure, salutations, and closing.
*   **Real-time Audio Visualization:** Engaging UI with a pulsing indicator and audio bars that react to your voice.
*   **Minimalist & Draggable UI:** A small, always-on-top window that can be easily moved around your screen.
*   **Global Hotkeys:**
    *   `Ctrl + Shift + Space`: Start/Stop recording.
    *   `Ctrl + Shift + H`: Open settings dialog.
    *   `Ctrl + Shift + X`: Toggle UI visibility (hide/show).
*   **Configuration Panel:**
    *   Set API keys (Mistral, Gemini) or use local Ollama models.
    *   Choose operation mode (Typer, Prompt Engineer, Email).
    *   Select target language for output (16 languages supported including English, Arabic, French, Spanish, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Hindi, Dutch, Polish, Turkish, Swedish).
    *   Configure streaming options for real-time text processing.
    *   Customize audio input device selection.
*   **Clipboard & Auto-Paste:** Automatically copies the final text to your clipboard and attempts to paste it into your active window.
*   **Audio Cues:** Optional sounds for recording start/stop (requires `pydub`).
*   **Real-time Streaming:** View AI processing results as they are generated, token by token.
*   **Customizable Appearance:** Leverages `customtkinter` themes for a modern look and feel.
*   **Persistent Configuration:** Saves your settings in a `config.json` file.

## How it Works

1.  **Voice Input:** User activates recording via a global hotkey.
2.  **Audio Capture:** Axo records audio from the microphone, displaying real-time visualizations.
3.  **ASR Transcription:** The recorded audio is processed by the local NVIDIA NeMo ASR model to generate raw text.
4.  **Text Processing (Optional):**
    *   If a service like Mistral AI is configured and enabled:
        *   **Typer Mode:** The raw text is sent for correction, punctuation, translation, and light formatting.
        *   **Prompt Engineer Mode:** The raw text is interpreted to generate a structured XML prompt for another AI.
5.  **Output:** The processed text is copied to the clipboard and an attempt is made to paste it into the currently active application.

<p>
  <img src="https://github.com/user-attachments/assets/7d43f1ab-4a08-4776-a2d8-9e7607131f42"  width="640" />
</p>

## PC Specifications:

Here are the estimated minimum and recommended specifications:

**Minimum System Requirements:**

*   **Operating System:**
    *   Windows 10/11 (64-bit)
    *   Linux (e.g., Ubuntu 20.04+ recommended for NeMo)
    *   macOS (Note: GPU acceleration for NeMo might be more complex or limited on macOS compared to Linux/Windows with NVIDIA GPUs. CPU-only operation will be slower.)
*   **CPU:**
    *   **Intel:** Dual-core Intel Core i3/i5 (e.g., 6th gen or newer) or equivalent.
    *   **AMD:** Dual-core AMD Ryzen 3 or equivalent.
    *   **Mac:** Any Apple Silicon Mac (M1 or newer) should handle the Python/UI parts, but ASR performance will be CPU-bound and thus slower than GPU-accelerated systems.
*   **RAM:**
    *   8 GB RAM (While Parakeet states 2GB for the model, the OS, Python, UI, and other processes will require more).
*   **GPU (for ASR):**
    *   **NVIDIA:** While the model might run on CPU, for a usable experience, an older NVIDIA GPU (e.g., GeForce GTX 1050 with at least 4GB VRAM) is advisable. The Parakeet model itself needs ~2.1GB VRAM.
    *   **AMD/Intel Integrated:** ASR will likely run on the CPU, leading to slow transcription times. The UI will function.
*   **Storage:**
    *   50 GB HDD or SSD (SSD highly recommended for overall system responsiveness and faster model loading). Consider more if you plan to download multiple ASR models or have large audio files. NeMo toolkits and models can take up considerable space.
*   **Internet:**
    *   Broadband internet connection (for Mistral API and initial model download).
*   **Other:**
    *   Microphone.

**Recommended System Requirements:**

*   **Operating System:**
    *   Windows 10/11 (64-bit)
    *   Linux (e.g., Ubuntu 20.04+ recommended for NeMo)
*   **CPU:**
    *   **Intel:** Quad-core Intel Core i5/i7 (e.g., 8th gen or newer) or equivalent.
    *   **AMD:** Quad-core AMD Ryzen 5/7 (e.g., 2000 series or newer) or equivalent.
    *   **Mac:** Apple Silicon Mac (M1 Pro/Max/Ultra, M2 or newer) for better CPU performance, though ASR will still be CPU-bound.
*   **RAM:**
    *   16 GB RAM or more (especially if processing longer audio files or multitasking). Some sources suggest 32GB for more intensive AI/ML work.
*   **GPU (for ASR):**
    *   **NVIDIA:** NVIDIA GeForce RTX series (e.g., RTX 2060, RTX 3060, RTX 4060) or newer, with at least 6 GB VRAM (8GB+ VRAM is better). Supported architectures include Volta, Turing, Ampere, Hopper, and Blackwell. An NVIDIA T4 (16GB VRAM) is cited as a minimum for lightweight inference.
    *   **AMD/Intel:** While the application might run, ASR performance will be significantly slower than with a recommended NVIDIA GPU.
*   **Storage:**
    *   256 GB NVMe SSD or faster (for quick OS boot, application loading, and model access).
*   **Internet:**
    *   Stable, fast broadband internet connection.
*   **Other:**
    *   Good quality USB microphone.

**Important Notes for PC Specifications:**

*   **NVIDIA GPU is Key for ASR Performance:** The `parakeet-tdt-0.6b-v2` model is optimized for NVIDIA GPUs. While it might technically run on a CPU or other GPUs, the transcription speed will be drastically slower, potentially making real-time or near real-time use frustrating.
*   **VRAM:** For the ASR model, sufficient VRAM on the GPU is crucial. The Parakeet 0.6B model is relatively small (~2.1GB VRAM needed), but more VRAM allows for potentially larger models in the future or smoother operation.
*   **Mistral AI:** The requirements for Mistral AI are primarily internet-dependent.
*   **Initial Setup:** Downloading the NeMo ASR model for the first time will require a good internet connection and some patience.


## Installation

### Prerequisites

*   Python 3.8 or newer.
*   `pip` (Python package installer).
*   For audio cues (optional): `ffmpeg` or `libav` (often required by `pydub` backends).

### Steps

1.  **Clone the Repository (or download the source code):**
    ```bash
    git clone https://github.com/your-username/axo.git # Replace with actual repo URL
    cd axo
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file should include:
    ```
    customtkinter
    # tkinter is usually part of standard Python installs
    nemo_toolkit[asr] # For NeMo ASR
    sounddevice
    numpy
    wave
    pyperclip
    pyautogui
    pynput
    mistralai
    # Optional for audio cues:
    # pydub
    # simpleaudio (or another pydub backend)
    ```
    *Note: `nemo_toolkit[asr]` can be a large download. Ensure you have a stable internet connection.*
    *If you want audio cues, install `pydub` and its dependencies (like `simpleaudio`):*
    ```bash
    pip install pydub simpleaudio
    ```

4.  **Configure Axo:**
    *   When you first run Axo, or if `config.json` is missing, it will be created with default settings.
    *   Open Axo and press `Ctrl + Shift + H` to open the settings.
    *   **API Keys:** Go to the "Models" tab and enter your Mistral or Gemini API keys if you wish to use cloud-based text refinement features. Alternatively, install Ollama for local processing.
    *   **Ollama Setup (Optional):** For local AI processing:
        1. Download and install [Ollama](https://ollama.com/)
        2. Install Python library: `pip install ollama`
        3. Pull a model: `ollama pull llama3.2` (or any supported model)
        4. In the Models tab, the Ollama model list will be blank until you refresh and have at least one model downloaded. If you have only one, it will be picked automatically. There is no default model.
        5. Select "Ollama" as your text processing service in the Models tab
    *   **Mode & Language:** Configure your preferred operation mode and output language.
    *   Save settings. Your `config.json` will be updated.

    Example `config.json` structure:
    ```json
    {
      "api_keys": {
        "mistral": "YOUR_MISTRAL_API_KEY",
        "gemini": "YOUR_GEMINI_API_KEY"
      },
      "models_config": {
        "text_processing_service": "Mistral", // "Mistral", "Gemini", "Ollama", or "None (Raw ASR)"
        "mistral_model_name": "mistral-medium-latest",
        "gemini_model_name": "gemini-2.0-flash",
        "ollama_model_name": "", // Local Ollama model (Blank unless you have downloaded a model)
        "mistral_custom_models": ["mistral-large-latest"],
        "gemini_custom_models": ["gemini-2.5-flash-preview-05-20"]
      },
      "language_config": {
        "target_language": "en" // "es", "fr", "ar", "de", "it", "pt", "ru", "zh", "ja", "ko", "hi", "nl", "pl", "tr", "sv"
      },
      "mode_config": {
        "operation_mode": "typer" // "typer", "prompt_engineer", or "email"
      },
      "hotkey_config": {
        "modifiers": ["ctrl", "shift"],
        "key": "space"
      },
      "audio_config": {
        "device": "Default"
      },
      "streaming_config": {
        "enabled": true,
        "confidence_threshold": 0.5,
        "context_sensitivity": true,
        "show_corrections": true
      }
    }
    ```

5.  **Application Icon:**
    The application attempts to load `Axo Icon.ico`. Ensure this file is in the assets directory if you want a custom icon for the window (may depend on OS and window manager for `overrideredirect` windows).

## Usage

1.  **Run the Application:**
    ```bash
    python Axo.py
    ```

2.  **Using Axo:**
    *   The Axo window will appear (default position is bottom-center of the screen). It's draggable.
    *   **Initial State:** Shows a static line, indicating it's ready and the ASR model is loaded.
    *   **Start Recording:** Hold `Ctrl + Shift + Space`. The UI will change to a listening animation (pulsing circle, audio bars).
    *   Speak clearly.
    *   **Stop Recording:** Release `Ctrl + Shift + Space` again. The UI will show a processing animation.
    *   **Output:** Once processing is complete, the refined text will be copied to your clipboard, and Axo will attempt to paste it into your active application. The UI will return to the initial state.
    *   **Open Settings:** Press `Ctrl + Shift + H` at any time to open the settings dialog.

3.  **UI States:**
    *   **Loading Model:** Displayed on startup while the ASR model loads.
    *   **Initial (Ready):** A calm line indicates Axo is ready to listen.
    *   **Listening:** A pulsing circle and dynamic audio bars show Axo is actively recording.
    *   **Processing:** Animated dots indicate transcription and text refinement are in progress.
    *   **Error Loading:** If the ASR model fails to load.

## Roadmap

### Current Features (Implemented)

*   ✅ Core voice dictation using NVIDIA NeMo ASR.
*   ✅ Text refinement and prompt engineering via Mistral AI and Gemini integration.
*   ✅ Three distinct operation modes: "Typer", "Prompt Engineer", and "Email".
*   ✅ **Email Mode:** Transform speech into professionally formatted emails with proper structure.
*   ✅ **Real-time Streaming:** View AI processing results as they are generated, token by token.
*   ✅ **Gemini Integration:** Full support for Google's Gemini models as text processing backend.
*   ✅ **Ollama Integration:** Full support for local AI models including streaming, all operation modes, and language processing.
*   ✅ Configurable target language for output.
*   ✅ Global hotkeys for recording (`Ctrl+Shift+Space`) and settings (`Ctrl+Shift+H`).
*   ✅ **Customizable Hotkeys:** Full hotkey customization through the settings UI.
*   ✅ Settings UI for API keys, mode, language, streaming, and audio device selection.
*   ✅ **Input Audio Device Selection:** Choose microphone input device from within the application.
*   ✅ **Custom Model Selection:** Support for custom Mistral and Gemini model variants.
*   ✅ Automatic clipboard copying and simulated paste of results.
*   ✅ Optional audio cues for recording start/stop (requires `pydub`).
*   ✅ Real-time audio input visualization.
*   ✅ Draggable, always-on-top UI.
*   ✅ Persistent configuration via `config.json`.

### Future Enhancements (Planned)

*   ⬜️ **Expanded ASR Model Selection:** Allow users to choose from a list of compatible ASR models beyond the current Parakeet model.
*   ⬜️ **Additional Language Support:** Continue expanding language options beyond the current 16 supported languages.
*   ⬜️ **Packaging:** Create distributable executables for major OS (Windows, macOS, Linux).