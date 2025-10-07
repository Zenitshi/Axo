import nemo.collections.asr as nemo_asr
from mistralai import Mistral
import google.generativeai as genai
import numpy as np
import wave
import pyperclip
import pyautogui
import time
import os
import json
import re
from typing import Generator, Dict, Any, Optional, List
import threading
from .prompts import get_prompt_instructions, generate_dynamic_prompt as generate_prompt_template

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3" # "nvidia/parakeet-tdt-0.6b-v2"
ASSETS_DIR = "assets"
TEMP_AUDIO_FILENAME = os.path.join(ASSETS_DIR, "temp_axo_audio.wav")
SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_MISTRAL_MODEL_NAME = "mistral-medium-latest"
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.0-flash"

def initialize_mistral_client(app):
    config_models = app.config.get("models_config", {})
    text_processing_service = config_models.get("text_processing_service")
    current_mistral_key = app.config.get("api_keys", {}).get("mistral")

    if text_processing_service == "Mistral" and current_mistral_key:
        if not app.mistral_client or getattr(app.mistral_client, 'api_key', None) != current_mistral_key:
            try:
                app.mistral_client = Mistral(api_key=current_mistral_key)
                print(f"Mistral client initialized/re-initialized.")
            except Exception as e:
                print(f"Error initializing Mistral client: {e}")
                app.mistral_client = None
    else:
        if app.mistral_client:
            print("Mistral service not selected or API key removed. De-initializing Mistral client.")
        app.mistral_client = None

def initialize_gemini_client(app):
    config_models = app.config.get("models_config", {})
    text_processing_service = config_models.get("text_processing_service")
    current_gemini_key = app.config.get("api_keys", {}).get("gemini")
    gemini_model_name = config_models.get("gemini_model_name", DEFAULT_GEMINI_MODEL_NAME)

    if text_processing_service == "Gemini" and current_gemini_key:
        current_internal_model_name = app.gemini_model_instance.model_name if app.gemini_model_instance else None
        if not app.gemini_model_instance or current_internal_model_name != gemini_model_name:
            try:
                genai.configure(api_key=current_gemini_key)
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                app.gemini_model_instance = genai.GenerativeModel(
                    model_name=gemini_model_name,
                    safety_settings=safety_settings
                )
                print(f"Gemini client initialized/re-initialized with model: {gemini_model_name}.")
            except Exception as e:
                print(f"Error initializing Gemini client with model {gemini_model_name}: {e}")
                app.gemini_model_instance = None
    else:
        if app.gemini_model_instance:
            print("Gemini service not selected or API key removed. De-initializing Gemini client.")
        app.gemini_model_instance = None


def load_asr_model(app):
    try:
        app.asr_model = nemo_asr.models.ASRModel.from_pretrained(MODEL_NAME)
        app.model_loaded_event.set(); print("ASR model loaded successfully.")
        app.current_state = "initial"
        app.master.after(0, app._update_ui_elements)
    except Exception as e:
        print(f"Error loading ASR model: {e}"); app.current_state = "error_loading"
        app.master.after(0, app._update_ui_elements)

# get_prompt_instructions function moved to backend/prompts.py

# generate_dynamic_prompt function moved to backend/prompts.py

def process_text_with_mistral(app, text):
    """Process text with Mistral API with robust error handling."""
    # Input validation
    if not app.mistral_client:
        print("Mistral client not initialized. Skipping text refinement.")
        return text
    if not text or not text.strip():
        print("No text from ASR to refine.")
        return ""

    print("Refining text with Mistral...")

    try:
        # Get configuration with safe defaults
        model_name = app.config.get("models_config", {}).get("mistral_model_name", DEFAULT_MISTRAL_MODEL_NAME)
        language_code = app.config.get("language_config", {}).get("target_language", "en")
        preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)
        mode = app.config.get("mode_config", {}).get("operation_mode", "typer")

        # Get prompts with error handling
        try:
            system_prompt, mode_instructions = get_prompt_instructions(mode, language_code, preserve_original_languages)
        except Exception as e:
            print(f"Error getting prompt instructions: {e}")
            return text

        # Build messages
        if preserve_original_languages:
            header_note = "to be processed while preserving original languages"
        else:
            header_note = f"to be processed into target language: {language_code}"

        user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
        user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
        ]

        # API call with error handling
        try:
            chat_response = app.mistral_client.chat.complete(
                model=model_name,
                messages=messages,
                temperature=0.05
            )
        except Exception as api_error:
            print(f"Mistral API call failed: {api_error}")
            return text

        # Validate response
        if not chat_response or not hasattr(chat_response, 'choices') or not chat_response.choices:
            print("Mistral API returned invalid response structure")
            return text

        choice = chat_response.choices[0]
        if not hasattr(choice, 'message') or not hasattr(choice.message, 'content'):
            print("Mistral API response missing content")
            return text

        refined_text = choice.message.content.strip()
        if not refined_text:
            print("Mistral API returned empty response")
            return text

        # Post-process based on mode
        try:
            if mode == "prompt_engineer":
                if refined_text.startswith("```xml") and refined_text.endswith("```"):
                    refined_text = refined_text.removeprefix("```xml").removesuffix("```").strip()
                elif refined_text.startswith("```") and refined_text.endswith("```"):
                    refined_text_lines = refined_text.splitlines()
                    if len(refined_text_lines) > 1 and refined_text_lines[0].strip().lower().startswith("xml"):
                        refined_text = "\n".join(refined_text_lines[1:-1]).strip()
                    else:
                         refined_text = refined_text.removeprefix("```").removesuffix("```").strip()
            elif mode == "email":
                if refined_text.startswith("```") and refined_text.endswith("```"):
                    refined_text_lines = refined_text.splitlines()
                    if len(refined_text_lines) > 1 and refined_text_lines[0].strip().lower() in ["", "text", "email"]:
                         refined_text = "\n".join(refined_text_lines[1:-1]).strip()
                    else:
                         refined_text = refined_text.removeprefix("```").removesuffix("```").strip()
                if (refined_text.startswith('"') and refined_text.endswith('"')) or \
                   (refined_text.startswith("'") and refined_text.endswith("'")):
                    refined_text = refined_text[1:-1]
            else: # Typer mode
                if not (refined_text.startswith("+ ") or refined_text.startswith("1.")):
                    if (refined_text.startswith('"') and refined_text.endswith('"')) or \
                       (refined_text.startswith("'") and refined_text.endswith("'")):
                        refined_text = refined_text[1:-1]

            print(f"Mistral refined text (Model: {model_name}, Mode: {mode}, Lang: {language_code}):\n{refined_text}")
            return refined_text

        except Exception as processing_error:
            print(f"Error processing Mistral response: {processing_error}")
            return text

    except Exception as general_error:
        print(f"Unexpected error in Mistral processing: {general_error}")
        return text

def process_text_with_gemini(app, text):
    if not app.gemini_model_instance:
        print("Gemini client not initialized. Skipping text refinement.")
        return text
    if not text.strip():
        print("No text from ASR to refine.")
        return ""
    
    selected_gemini_model_name = app.config.get("models_config", {}).get("gemini_model_name", DEFAULT_GEMINI_MODEL_NAME)
    print(f"Refining text with Gemini (Model: {selected_gemini_model_name})...")

    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)
    mode = app.config.get("mode_config", {}).get("operation_mode", "typer")

    system_prompt, mode_instructions = get_prompt_instructions(mode, language_code, preserve_original_languages)
    
    if preserve_original_languages:
        header_note = "to be processed while preserving original languages"
    else:
        header_note = f"to be processed into target language: {language_code}"
    
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    full_prompt_text = f"{system_prompt}\n\n{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"

    try:
        response = app.gemini_model_instance.generate_content(
            full_prompt_text,
            generation_config=genai.types.GenerationConfig(temperature=0.05)
        )
        refined_text = response.text.strip()

        if mode == "prompt_engineer":
            if refined_text.startswith("```xml") and refined_text.endswith("```"):
                refined_text = refined_text.removeprefix("```xml").removesuffix("```").strip()
            elif refined_text.startswith("```") and refined_text.endswith("```"):
                refined_text_lines = refined_text.splitlines()
                if len(refined_text_lines) > 1 and refined_text_lines[0].strip().lower().startswith("xml"):
                    refined_text = "\n".join(refined_text_lines[1:-1]).strip()
                else:
                     refined_text = refined_text.removeprefix("```").removesuffix("```").strip()
        elif mode == "email":
            if refined_text.startswith("```") and refined_text.endswith("```"):
                refined_text_lines = refined_text.splitlines()
                if len(refined_text_lines) > 1 and refined_text_lines[0].strip().lower() in ["", "text", "email"]:
                     refined_text = "\n".join(refined_text_lines[1:-1]).strip()
                else:
                     refined_text = refined_text.removeprefix("```").removesuffix("```").strip()
            if (refined_text.startswith('"') and refined_text.endswith('"')) or \
               (refined_text.startswith("'") and refined_text.endswith("'")):
                refined_text = refined_text[1:-1]
        else: # Typer mode
            if not (refined_text.startswith("+ ") or refined_text.startswith("1.")):
                if (refined_text.startswith('"') and refined_text.endswith('"')) or \
                   (refined_text.startswith("'") and refined_text.endswith("'")):
                    refined_text = refined_text[1:-1]

        print(f"Gemini refined text (Model: {selected_gemini_model_name}, Mode: {mode}, Lang: {language_code}):\n{refined_text}")
        return refined_text
    except Exception as e:
        print(f"Error during Gemini API call with model {selected_gemini_model_name}: {e}")
        try:
            if response and response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"Gemini prompt blocked due to: {response.prompt_feedback.block_reason}")
        except:
            pass
        return text

def transcribe_and_refine_audio_data(app, frames_to_process):
    final_text_to_output = ""
    try:
        if not frames_to_process:
            print("Transcription thread: No frames received.")
            app.master.after(0, app._set_initial_state_after_processing)
            return
        audio_data = np.concatenate(frames_to_process, axis=0)
        if audio_data.size == 0:
            print("Concatenated audio data is empty.")
            app.master.after(0, app._set_initial_state_after_processing)
            return
        sample_width_bytes = 2
        with wave.open(TEMP_AUDIO_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(sample_width_bytes)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        transcribed_text = ""
        if app.asr_model:
            print("Transcribing audio with NeMo...")
            nemo_result_list = app.asr_model.transcribe([TEMP_AUDIO_FILENAME])
            if nemo_result_list and isinstance(nemo_result_list, list) and len(nemo_result_list) > 0:
                actual_result_item = nemo_result_list[0]
                if isinstance(actual_result_item, str):
                    transcribed_text = actual_result_item
                elif hasattr(actual_result_item, 'text') and isinstance(getattr(actual_result_item, 'text'), str):
                    transcribed_text = actual_result_item.text
                elif actual_result_item is None: transcribed_text = ""
                else: print(f"ASR: Unexpected type for NeMo's result item: {type(actual_result_item)}")
            elif nemo_result_list is None: print("ASR: NeMo transcribe returned None.")
            elif isinstance(nemo_result_list, list) and len(nemo_result_list) == 0: print("ASR: NeMo transcribe returned an empty list.")
            else: print(f"ASR: NeMo transcribe returned unexpected structure: {type(nemo_result_list)}")

            if transcribed_text: print(f"ASR Transcription: {transcribed_text}")
            else: print("ASR Transcription by NeMo resulted in empty text.")
        else:
            print("ASR model not available. Transcription skipped.")

        text_processing_service = app.config.get("models_config", {}).get("text_processing_service", "Mistral")
        streaming_config = app.config.get("streaming_config", {})
        
        if transcribed_text:
            # Check if streaming is enabled
            if streaming_config.get("enabled", False):
                print("Starting streaming text processing...")
                start_streaming_text_processing(app, transcribed_text)
                return  # Exit early for streaming mode
            else:
                # Check operation mode
                operation_mode = app.config.get("mode_config", {}).get("operation_mode", "typer")

                if operation_mode == "coder":
                    # Use coder mode processing
                    final_text_to_output = process_text_with_coder_mode(app, transcribed_text)
                else:
                    # Use existing batch processing for other modes
                    if text_processing_service == "Mistral" and app.mistral_client:
                        final_text_to_output = process_text_with_mistral(app, transcribed_text)
                    elif text_processing_service == "Gemini" and app.gemini_model_instance:
                        final_text_to_output = process_text_with_gemini(app, transcribed_text)
                    elif text_processing_service == "Ollama":
                        # Initialize Ollama manager if not already done
                        if not hasattr(app, 'ollama_manager'):
                            initialize_ollama_manager(app)
                        final_text_to_output = process_text_with_ollama(app, transcribed_text)
                    elif text_processing_service == "None (Raw ASR)":
                        print("Using raw ASR output.")
                        final_text_to_output = transcribed_text
                    else:
                        print(f"Service '{text_processing_service}' not available or client not ready. Using raw ASR.")
                        final_text_to_output = transcribed_text
        else:
            final_text_to_output = ""

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
            print("No final text to output.")
    except ValueError as ve:
        print(f"ValueError during audio processing: {ve}")
    except Exception as e:
        print(f"Error during transcription/refinement: {e}")
    finally:
        app._play_sound_async("close.wav")
        app.master.after(0, app._set_initial_state_after_processing) 

def stream_mistral_text_processing(app, text: str, operation_mode: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream text processing with Mistral AI using correct API pattern.
    
    Args:
        app: The application instance
        text: The transcribed text to process
        operation_mode: The operation mode (typer, prompt_engineer, email, coder)
    
    Yields:
        Dict containing streaming data with keys: 'type', 'content'
    """
    if not app.mistral_client:
        yield {"type": "error", "content": "Mistral client not initialized"}
        return
    
    # This function no longer needs to check for the streaming_config enabled flag,
    # as it's only called when streaming is already intended.
    
    # Generate prompt based on operation mode
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code, preserve_original_languages)
    
    if preserve_original_languages:
        header_note = "to be processed while preserving original languages"
    else:
        header_note = f"to be processed into target language: {language_code}"
    
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
    ]
    
    try:
        # Use correct Mistral streaming pattern
        stream_response = app.mistral_client.chat.stream(
            model=app.config.get("models_config", {}).get("mistral_model_name", DEFAULT_MISTRAL_MODEL_NAME),
            messages=messages,
            temperature=0.05
        )
        
        # Stream tokens naturally as they come from the API
        for chunk in stream_response:
            # CORRECTED: Access chunk.data.choices for Mistral streaming API
            if chunk.data.choices[0].delta.content is not None:
                token_content = chunk.data.choices[0].delta.content
                yield {
                    "type": "token",
                    "content": token_content
                }
            
            # CORRECTED: Check for completion reason correctly
            if chunk.data.choices[0].finish_reason == "stop":
                yield {"type": "final"}
                break
                
    except Exception as e:
        yield {"type": "error", "content": f"Streaming error: {str(e)}"}

def analyze_and_correct_context(original_text: str, current_output: str, token: str, 
                               context_window: list, streaming_config: dict) -> Dict[str, Any]:
    """
    Analyze context and apply intelligent corrections based on confidence thresholds.
    
    Args:
        original_text: The original transcribed text
        current_output: The current accumulated output
        token: The current token being processed
        context_window: Recent context for analysis
        streaming_config: Configuration for streaming corrections
    
    Returns:
        Dict containing correction analysis results
    """
    confidence_threshold = streaming_config.get("confidence_threshold", 0.5)
    context_sensitivity = streaming_config.get("context_sensitivity", True)
    
    if not context_sensitivity:
        return {"confidence": 1.0, "correction": None, "original_token": token}
    
    # Analyze token for nonsensical content
    nonsensical_confidence = analyze_token_sensibility(token, current_output, original_text)
    
    # If confidence is below threshold, consider correction
    if nonsensical_confidence < confidence_threshold:
        # Check if we're 100% sure of the correction
        correction_candidate = suggest_correction(token, current_output, original_text)
        if correction_candidate and correction_candidate["certainty"] >= 1.0:
            return {
                "confidence": nonsensical_confidence,
                "correction": correction_candidate["corrected_token"],
                "original_token": token
            }
    
    return {"confidence": nonsensical_confidence, "correction": None, "original_token": token}

def analyze_token_sensibility(token: str, current_output: str, original_text: str) -> float:
    """
    Analyze if a token makes sense in the current context.
    
    Returns:
        Float between 0.0 and 1.0 indicating confidence that the token is sensible
    """
    # Check for obvious nonsensical patterns
    nonsensical_patterns = [
        r'^[^a-zA-Z0-9\s\.,!?;:\'"-]+$',  # Non-alphanumeric gibberish
        r'^([a-zA-Z])\1{3,}',  # Repeated character patterns (e.g., "aaaa", "bbbb")
        r'^[bcdfghjklmnpqrstvwxyz]{4,}$',  # Too many consonants
        r'^[aeiou]{4,}$',  # Too many vowels
    ]
    
    for pattern in nonsensical_patterns:
        if re.match(pattern, token.strip()):
            return 0.1  # Very low confidence for nonsensical patterns
    
    # Check for context appropriateness
    if len(token.strip()) > 20 and not any(c.isspace() for c in token):
        return 0.3  # Suspicious long tokens without spaces
    
    # Default to high confidence if no issues detected
    return 0.9

def suggest_correction(token: str, current_output: str, original_text: str) -> Optional[Dict[str, Any]]:
    """
    Suggest a correction for a token if we're 100% certain.
    
    Returns:
        Dict with correction suggestion or None if not certain enough
    """
    # Only suggest corrections for obvious nonsensical content
    if re.match(r'^[^a-zA-Z0-9\s\.,!?;:\'"-]+$', token.strip()):
        # If it's complete gibberish, suggest removing it
        return {
            "corrected_token": "",
            "certainty": 1.0,
            "reason": "nonsensical_characters"
        }
    
    # For now, be very conservative - only correct obvious gibberish
    return None

def stream_gemini_text_processing(app, text: str, operation_mode: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream text processing with Gemini AI using correct API pattern.
    
    Args:
        app: The application instance
        text: The transcribed text to process
        operation_mode: The operation mode (typer, prompt_engineer, email)
    
    Yields:
        Dict containing streaming data with keys: 'type', 'content'
    """
    if not app.gemini_model_instance:
        yield {"type": "error", "content": "Gemini model not initialized"}
        return
    
    streaming_config = app.config.get("streaming_config", {})
    if not streaming_config.get("enabled", False):
        # Fallback to existing batch processing
        result = process_text_with_gemini(app, text)
        yield {"type": "final", "content": result}
        return
    
    # Generate prompt based on operation mode
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code, preserve_original_languages)
    
    if preserve_original_languages:
        header_note = "to be processed while preserving original languages"
    else:
        header_note = f"to be processed into target language: {language_code}"
    
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    
    complete_prompt = f"""{system_prompt}

{mode_instructions}

{user_content_header}
{text}
{user_content_footer}"""
    
    try:
        # Use correct Gemini streaming pattern from research
        response = app.gemini_model_instance.generate_content(
            complete_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.05,
                max_output_tokens=2048,
            ),
            stream=True
        )
        
        # Stream tokens naturally as they come from the API
        for chunk in response:
            if chunk.text:
                yield {
                    "type": "token",
                    "content": chunk.text
                }
        
        yield {"type": "final"}
                
    except Exception as e:
        yield {"type": "error", "content": f"Streaming error: {str(e)}"} 

def start_streaming_text_processing(app, transcribed_text: str):
    """
    Start streaming text processing in a separate thread.

    Args:
        app: The application instance
        transcribed_text: The transcribed text to process
    """
    # Ensure streaming widget exists before proceeding
    if not app._ensure_streaming_widget_exists():
        print("Error: Cannot start streaming - streaming widget unavailable")
        return

    # Show streaming widget immediately before calling API
    def show_widget_safe():
        if app.streaming_widget is not None:
            app.streaming_widget.show_streaming_widget(transcribed_text)
        else:
            print("Warning: Streaming widget not available, skipping widget display")
    app.master.after(0, show_widget_safe)
    
    def streaming_worker():
        try:
            # Small delay to ensure widget is shown
            time.sleep(0.1)
            
            # Get the current operation mode
            operation_mode = app.config.get("mode_config", {}).get("operation_mode", "typer")
            
            # Determine which LLM service to use
            text_processing_service = app.config.get("models_config", {}).get("text_processing_service", "Mistral")
            
            # Choose streaming function based on service and mode
            if text_processing_service == "Mistral":
                stream_generator = stream_mistral_text_processing(app, transcribed_text, operation_mode)
            elif text_processing_service == "Gemini":
                stream_generator = stream_gemini_text_processing(app, transcribed_text, operation_mode)
            elif text_processing_service == "Ollama":
                # Initialize Ollama manager if not already done
                if not hasattr(app, 'ollama_manager'):
                    initialize_ollama_manager(app)
                stream_generator = stream_ollama_text_processing(app, transcribed_text, operation_mode)
            else:
                # Fallback to batch processing
                if text_processing_service == "Mistral" and app.mistral_client:
                    result = process_text_with_mistral(app, transcribed_text)
                elif text_processing_service == "Gemini" and app.gemini_model_instance:
                    result = process_text_with_gemini(app, transcribed_text)
                else:
                    result = transcribed_text
                def update_fallback_result_safe(res):
                    if app.streaming_widget is not None:
                        app.streaming_widget.update_streaming_content({
                            "type": "final",
                            "content": res
                        })
                    else:
                        print("Warning: Streaming widget not available, skipping fallback result update")
                app.master.after(0, lambda: update_fallback_result_safe(result))
                return
            
            # Process streaming results naturally
            for stream_data in stream_generator:
                # Update UI in main thread - timing handled by UI layer
                def update_content_safe(data):
                    if app.streaming_widget is not None:
                        app.streaming_widget.update_streaming_content(data)
                    else:
                        print("Warning: Streaming widget not available, skipping content update")
                app.master.after(0, lambda data=stream_data: update_content_safe(data))
                
        except Exception as e:
            error_data = {"type": "error", "content": f"Streaming processing error: {str(e)}"}
            def handle_error_safe(data):
                if app.streaming_widget is not None:
                    app.streaming_widget.update_streaming_content(data)
                else:
                    print(f"Error: {data['content']}")
            app.master.after(0, lambda: handle_error_safe(error_data))
    
    # Start streaming in a separate thread
    streaming_thread = threading.Thread(target=streaming_worker, daemon=True)
    streaming_thread.start() 

class OllamaManager:
    """Manager for Ollama integration - detection and model listing."""
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.is_available = False
        self.client = None
        
    def detect_ollama(self) -> bool:
        """Check if Ollama is installed and running."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            if response.status_code == 200:
                self.is_available = True
                try:
                    import ollama
                    self.client = ollama.Client(host=self.base_url)
                except ImportError:
                    print("Ollama Python library not installed. Run: pip install ollama")
                    self.is_available = False
                return self.is_available
        except (requests.exceptions.ConnectionError, ImportError) as e:
            print(f"Ollama not available: {e}")
            self.is_available = False
        return False
        
    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available Ollama models."""
        if not self.is_available or not self.client:
            return []
        
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get('models', []):
                    # Extract model name and remove tag if it's just ":latest"
                    model_name = model['name']
                    if model_name.endswith(':latest'):
                        model_name = model_name[:-7]  # Remove ":latest"
                    models.append({
                        'name': model_name,
                        'full_name': model['name'],  # Keep full name with tag
                        'size': self._format_size(model.get('size', 0)),
                        'modified': model.get('modified_at', 'Unknown')
                    })
                return models
        except Exception as e:
            print(f"Error getting Ollama models: {e}")
        return []
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        if size_bytes == 0:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


def initialize_ollama_manager(app):
    """Initialize Ollama manager for the application."""
    if not hasattr(app, 'ollama_manager'):
        app.ollama_manager = OllamaManager()
        app.ollama_manager.detect_ollama()


def stream_ollama_text_processing(app, text: str, operation_mode: str) -> Generator[Dict[str, Any], None, None]:
    """
    Stream text processing with Ollama using the selected model.

    Args:
        app: The application instance
        text: The transcribed text to process
        operation_mode: The operation mode (typer, prompt_engineer, email, coder)

    Yields:
        Dict containing streaming data with keys: 'type', 'content'
    """
    if not hasattr(app, 'ollama_manager') or not app.ollama_manager.is_available:
        yield {"type": "error", "content": "Ollama not available or not initialized"}
        return

    # Get selected Ollama model from config
    ollama_model = app.config.get("models_config", {}).get("ollama_model_name", "")
    if not ollama_model:
        yield {"type": "error", "content": "No Ollama model selected"}
        return

    # Generate prompt based on operation mode
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)

    # For coder mode, get target language
    target_language = None
    if operation_mode == "coder":
        target_language = app.config.get("coder_config", {}).get("target_language", "Python")

    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code, preserve_original_languages, target_language)

    if operation_mode == "coder":
        # For coder mode, simpler prompt structure
        full_prompt = f"{system_prompt}\n\n{mode_instructions}\n\nUser request: {text}"
    else:
        if preserve_original_languages:
            header_note = "to be processed while preserving original languages"
        else:
            header_note = f"to be processed into target language: {language_code}"

        user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
        user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
        full_prompt = f"{system_prompt}\n\n{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"

    try:
        import ollama

        # Stream response from Ollama
        stream = ollama.chat(
            model=ollama_model,
            messages=[{
                'role': 'user',
                'content': full_prompt
            }],
            stream=True,
        )

        for chunk in stream:
            content = chunk.get('message', {}).get('content', '')
            if content:
                yield {
                    "type": "token",
                    "content": content
                }

        yield {"type": "final"}

    except Exception as e:
        yield {"type": "error", "content": f"Ollama streaming error: {str(e)}"}


def process_text_with_ollama(app, text: str) -> str:
    """
    Process text with Ollama (non-streaming) as fallback.

    Args:
        app: The application instance
        text: The transcribed text to process

    Returns:
        str: The processed text result
    """
    if not hasattr(app, 'ollama_manager') or not app.ollama_manager.is_available:
        return f"Error: Ollama not available"

    operation_mode = app.config.get("mode_config", {}).get("operation_mode", "typer")
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)

    # For coder mode, get target language from config
    target_language = None
    if operation_mode == "coder":
        target_language = app.config.get("coder_config", {}).get("target_language", "Python")

    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code, preserve_original_languages, target_language)

    ollama_model = app.config.get("models_config", {}).get("ollama_model_name", "")
    if not ollama_model:
        return "Error: No Ollama model selected"

    if operation_mode == "coder":
        # For coder mode, simpler prompt structure
        full_prompt = f"{system_prompt}\n\n{mode_instructions}\n\nUser request: {text}"
    else:
        if preserve_original_languages:
            header_note = "to be processed while preserving original languages"
        else:
            header_note = f"to be processed into target language: {language_code}"

        user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
        user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
        full_prompt = f"{system_prompt}\n\n{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"

    try:
        import ollama

        response = ollama.chat(
            model=ollama_model,
            messages=[{
                'role': 'user',
                'content': full_prompt
            }]
        )

        return response['message']['content']

    except Exception as e:
        return f"Error processing with Ollama: {str(e)}"

def process_text_with_coder_mode(app, text: str) -> str:
    """
    Process text in coder mode - translate natural language to code.

    Args:
        app: The application instance
        text: The transcribed text to process

    Returns:
        str: The generated code
    """
    target_language = app.config.get("coder_config", {}).get("target_language", "Python")
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    preserve_original_languages = app.config.get("language_config", {}).get("preserve_original_languages", True)

    system_prompt, mode_instructions = get_prompt_instructions("coder", language_code, preserve_original_languages, target_language)

    # Create the full prompt
    full_prompt = f"{system_prompt}\n\n{mode_instructions}\n\nUser request: {text}"

    # Use the configured LLM service
    text_processing_service = app.config.get("models_config", {}).get("text_processing_service", "Mistral")

    try:
        if text_processing_service == "Mistral" and app.mistral_client:
            chat_response = app.mistral_client.chat.complete(
                model=app.config.get("models_config", {}).get("mistral_model_name", DEFAULT_MISTRAL_MODEL_NAME),
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.05
            )
            return chat_response.choices[0].message.content.strip()

        elif text_processing_service == "Gemini" and app.gemini_model_instance:
            response = app.gemini_model_instance.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.05)
            )
            return response.text.strip()

        elif text_processing_service == "Ollama":
            if not hasattr(app, 'ollama_manager'):
                initialize_ollama_manager(app)
            if hasattr(app, 'ollama_manager') and app.ollama_manager.is_available:
                ollama_model = app.config.get("models_config", {}).get("ollama_model_name", "")
                if ollama_model:
                    import ollama
                    response = ollama.chat(
                        model=ollama_model,
                        messages=[{'role': 'user', 'content': full_prompt}]
                    )
                    return response['message']['content']
            return f"Error: Ollama not available or no model selected"

        else:
            return f"Error: No LLM service available for coder mode"

    except Exception as e:
        return f"Error in coder mode processing: {str(e)}" 