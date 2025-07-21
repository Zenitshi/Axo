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

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v2"
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

def get_prompt_instructions(mode, language_code):
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
    *   If the user's speech implies a list (e.g., using "firstly", "secondly", "then this, then that", or a sequence of related short statements), format these items as bullet points (using '• ') or a numbered list (e.g., '1. ') if the order is explicitly stated or clearly sequential.
    *   Example (if target language is English): User says, "For the project, we need to define scope, then gather resources, and finally set a timeline."
      Expected output:
      + Define scope.
      + Gather resources.
      + Set a timeline.
    *   Do not impose list formatting if it's not clearly implied.

6.  **Conciseness:** Output only the refined text. No explanations, no apologies, no "Here's the refined text:". Just the text itself.
"""

    prompt_engineer_mode_instructions = f"""
CRITICAL INSTRUCTION: You are in 'Prompt Engineer' mode. Your objective is to transform the user's spoken input into a highly effective, structured prompt for another advanced AI system (like GPT-4.1, Gemini 2.5 Pro, Claude 3.7, etc).
The generated prompt MUST be in **{{language_code}}** and enclosed in a main `<Prompt>` XML tag, following the detailed structure below.

**Core Principles to Apply (Think step-by-step for each section):**

1.  **Deconstruct User Input:** Carefully analyze the user's raw ASR transcript to understand their core intent, the task they want the target AI to perform, key entities, desired output, and any implicit or explicit instructions.
2.  **Adhere to Modern Prompting Best Practices:** Construct the prompt using the XML-delimited sections. These sections are based on proven strategies for guiding LLMs effectively.
3.  **Clarity and Directness:** Instructions within the generated prompt should be clear, direct, and unambiguous. Modern LLMs follow direct instructions well.
4.  **Negative Instructions:** Use negative instructions (e.g., "Do not include...") sparingly but appropriately if they clarify the task significantly.
5.  **Sandwich Method for Critical Instructions:** If there are overriding critical instructions for the target AI, ensure they are mentioned early (e.g., in `<RoleAndObjective>` or `<Instructions>`) and reiterated in `<FinalInstructions>`.
6.  **Chain-of-Thought (CoT) Encouragement:** Where appropriate, include a "Think step-by-step" instruction within the generated prompt's `<FinalInstructions>` or relevant instruction sections to guide the target AI's reasoning process.
7.  **Conditional Tag Generation:** Only include an XML tag in the output if it contains specific, relevant content derived from the user's input. If a section like `<Examples>` or `<Constraints>` has no specific content to add (e.g., no relevant examples can be formulated, or no constraints are mentioned), then the entire XML tag for that section MUST be omitted from the generated prompt. Do not include tags with placeholder text like 'No examples provided.' or 'No constraints specified.' or similar statements indicating absence of content; instead, omit the tag itself.

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
        <!-- If user says "I want you to write an email to John about the meeting", this section might be empty or describe what information the email should contain. If no direct input data is provided or described for the target AI, this tag MAY be omitted if it would be empty. -->
        <!-- Based on user input: [Place or describe the primary input data here. If truly nothing, consider omitting the tag as per principle 7.] -->
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
        <!-- If providing an example is not beneficial or no relevant example can be constructed from the user's request, this entire <Examples> tag MUST BE OMITTED. Do not include it with placeholder text. -->
        <!-- Example (if the task was to extract names and roles):
        <Example>
            <Input>Text: "Alice is the project manager and Bob is the lead developer."</Input>
            <Output>JSON: [ {{"name": "Alice", "role": "project manager"}}, {{"name": "Bob", "role": "lead developer"}} ]</Output>
        </Example>
        -->
        <!-- Based on user input and task complexity: [Construct a relevant, simple example if beneficial. If not, OMIT THE ENTIRE <Examples> TAG.] -->
    </Examples>

    <Constraints>
        <!-- List any constraints or things the target AI should avoid. -->
        <!-- Example: Do not use technical jargon. The summary should not exceed 200 words. -->
        <!-- Based on user input: [Identify and list any constraints. If no constraints are explicitly mentioned or clearly implied by the user's request, OMIT THE ENTIRE <Constraints> TAG.] -->
    </Constraints>

    <FinalInstructions>
        <!-- Reiterate the most critical instructions, especially regarding the output format and core task. -->
        <!-- Include a "Think step-by-step to ensure accuracy." or similar CoT prompt. -->
        <!-- Example: Ensure the output strictly adheres to the specified <OutputFormat>. Double-check all extracted entities for accuracy. Think step-by-step. -->
        <!-- Based on user input: [Reiterate key instructions and add CoT encouragement] -->
    </FinalInstructions>
</Prompt>
```
Your task:
1. Correct ASR errors in the following raw transcript.
2. Translate the corrected transcript fully into {language_code}.
3. Based on the translated content, generate a complete, structured XML prompt according to the schema and principles outlined above.
"""
    email_mode_instructions = f"""
Use code with caution.
CRITICAL INSTRUCTION: You are in 'Email' mode. Your task is to transform the user's spoken input into a professionally formatted email.
The entire email MUST be in the target language: {language_code}.
Follow these steps meticulously:
ASR Correction: First, carefully correct any errors in the provided ASR (Automatic Speech Recognition) transcript. This includes misspellings, stutters, repeated words, and phonetic mistakes. Ensure proper capitalization and punctuation for general readability before email formatting.
Translation: Translate the corrected ASR transcript fully into the target language: {language_code}. All elements of the email must be in this language.
Email Structure - Infer and Generate:
Subject Line: Based on the user's speech, create a concise and informative subject line. Prefix it with "Subject: ".
Salutation:
If the user mentions a recipient's name (e.g., "write an email to John," "tell Sarah that..."), use a formal or semi-formal salutation like "Dear John," or "Hi Sarah,".
If no recipient is clearly identified, use a generic salutation like "Dear Team," "To Whom It May Concern," or a contextually appropriate greeting. If a very casual interaction is implied, a simple "Hi," might be acceptable.
Email Body:
Transform the core message from the user's speech into clear, well-structured paragraphs.
Maintain the original intent and key information.
Use polite and professional language appropriate for an email.
If the user implies a list or bullet points, format them clearly within the body (e.g., using hyphens '-' or asterisks '* ').
Closing: Provide a standard professional closing (e.g., "Sincerely,", "Best regards,", "Regards,").
Sender's Name (Optional Placeholder): If the user doesn't explicitly state their name for the signature, you can add a placeholder like "[Your Name]" after the closing. If the context strongly implies anonymity or the sender is obvious, you might omit this.
Formatting and Conciseness:
The final output should be ONLY the complete email text, ready to be pasted.
Do NOT include any of your own conversational phrases, comments, apologies, or self-references (e.g., "Here is the email:", "I have drafted an email for you:").
Ensure there's a blank line between the subject, salutation, each paragraph in the body, the closing, and the sender's name placeholder (if used).
Example (if target language is English and user says "draft an email to marketing about the new campaign launch next week, tell them to prepare the press release and social media posts"):
Subject: New Campaign Launch Next Week
Dear Marketing Team,
I hope this email finds you well.
This is to inform you about the new campaign scheduled to launch next week. Please begin preparations for the following:
Press release
Social media posts
Please let me know if you have any questions.
Best regards,
[Your Name]
Your task is to apply these instructions to the ASR transcript provided below.
"""

    if mode == "typer":
        return system_prompt_core, typer_mode_instructions
    elif mode == "prompt_engineer":
        return system_prompt_core, prompt_engineer_mode_instructions
    elif mode == "email":
        return system_prompt_core, email_mode_instructions
    else: # Default to typer
        return system_prompt_core, typer_mode_instructions

def generate_dynamic_prompt(operation_mode: str, text: str, language_code: str) -> str:
    """
    Generate a dynamic prompt for streaming text processing based on operation mode.
    
    Args:
        operation_mode: The operation mode (typer, prompt_engineer, email)
        text: The transcribed text to process
        language_code: Target language code
    
    Returns:
        Complete prompt string for the LLM
    """
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    
    # Create the complete prompt
    complete_prompt = f"""{system_prompt}

{mode_instructions}

{user_content_header}
{text}
{user_content_footer}"""
    
    return complete_prompt

def process_text_with_mistral(app, text):
    if not app.mistral_client:
        print("Mistral client not initialized. Skipping text refinement.")
        return text
    if not text.strip():
        print("No text from ASR to refine.")
        return ""
    print("Refining text with Mistral...")
    model_name = app.config.get("models_config", {}).get("mistral_model_name", DEFAULT_MISTRAL_MODEL_NAME)
    language_code = app.config.get("language_config", {}).get("target_language", "en")
    mode = app.config.get("mode_config", {}).get("operation_mode", "typer")

    system_prompt, mode_instructions = get_prompt_instructions(mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{mode_instructions}\n\n{user_content_header}\n{text}\n{user_content_footer}"}
    ]
    try:
        chat_response = app.mistral_client.chat.complete(
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
    except Exception as e:
        print(f"Error during Mistral API call with model {model_name}: {e}")
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
    mode = app.config.get("mode_config", {}).get("operation_mode", "typer")

    system_prompt, mode_instructions = get_prompt_instructions(mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
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
                # Use existing batch processing
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
        operation_mode: The operation mode (typer, prompt_engineer, email)
    
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
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
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
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
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
    # Show streaming widget immediately before calling API
    app.master.after(0, lambda: app.streaming_widget.show_streaming_widget(transcribed_text))
    
    def streaming_worker():
        try:
            # Small delay to ensure widget is shown
            time.sleep(0.1)
            
            # Get the current operation mode
            operation_mode = app.config.get("mode_config", {}).get("operation_mode", "typer")
            
            # Determine which LLM service to use
            text_processing_service = app.config.get("models_config", {}).get("text_processing_service", "Mistral")
            
            # Choose streaming function based on service
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
                result = process_text_with_mistral(app, transcribed_text, operation_mode)
                app.master.after(0, lambda: app.streaming_widget.update_streaming_content({
                    "type": "final",
                    "content": result
                }))
                return
            
            # Process streaming results naturally
            for stream_data in stream_generator:
                # Update UI in main thread - timing handled by UI layer
                app.master.after(0, lambda data=stream_data: app.streaming_widget.update_streaming_content(data))
                
        except Exception as e:
            error_data = {"type": "error", "content": f"Streaming processing error: {str(e)}"}
            app.master.after(0, lambda: app.streaming_widget.update_streaming_content(error_data))
    
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
        operation_mode: The operation mode (typer, prompt_engineer, email)
    
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
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code)
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
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
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code)
    
    ollama_model = app.config.get("models_config", {}).get("ollama_model_name", "")
    if not ollama_model:
        return "Error: No Ollama model selected"
    
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION (to be processed into target language: {language_code}) ---"
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