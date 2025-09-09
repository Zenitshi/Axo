"""
Prompt templates and instructions for different operation modes.
This module contains all AI prompt instructions used in Axo.
"""

def get_system_prompt_core(language_instruction):
    """
    Get the core system prompt with language handling instruction.
    
    Args:
        language_instruction: Instruction for language handling (translation vs preservation)
    """
    return f"""You are an advanced AI assistant. Your primary task is to process raw speech-to-text transcription.
Modern LLMs like you excel at understanding direct instructions. Be clear, concise, and accurate.
First, meticulously correct any ASR errors (misspellings, stutters, phonetic mistakes, duplications).
{language_instruction}
Preserve the original meaning and intent absolutely.
Output ONLY the processed text, with no additional comments, conversational phrases, apologies, or self-references, unless the mode specifically dictates a structured output."""

def get_language_instruction(language_code, preserve_original_languages=False):
    """
    Get the appropriate language instruction based on user settings.
    
    Args:
        language_code: Target language code (ISO 639-1)
        preserve_original_languages: Whether to preserve original languages or translate
    """
    if preserve_original_languages:
        return "Then, preserve the original languages as spoken. Do NOT translate between languages. If the speaker used multiple languages (e.g., French and English), keep both languages exactly as intended. Only correct ASR errors, add punctuation, and improve clarity while maintaining the original language mix."
    else:
        return f"Then, ensure your entire output is in the target language: **{language_code}** (ISO 639-1 code). If the ASR transcript contains phrases from other languages, translate them to {language_code}."

def get_typer_mode_instructions(language_code, preserve_original_languages=False):
    """Get instructions for Typer mode."""
    
    if preserve_original_languages:
        language_section = """2.  **Language Preservation:** Preserve the original languages as spoken. Do NOT translate between languages. If the speaker used multiple languages (e.g., French and English), keep both languages exactly as intended. Only correct ASR errors while maintaining the original language mix."""
    else:
        language_section = f"""2.  **Translation:** Ensure the final output is entirely in the target language: **{language_code}**. If the ASR transcript contains phrases from other languages, translate them."""
    
    return f"""CRITICAL INSTRUCTION: You are in 'Typer' mode. Your goal is to refine the provided ASR (Automatic Speech Recognition) transcript.
Follow these principles strictly:

1.  **ASR Correction:** Identify and correct common ASR errors. This includes:
    *   Misspellings due to phonetic similarity (e.g., "too" vs. "to" vs. "two", "there" vs. "their" vs. "they're").
    *   Stutters or repeated words (e.g., "I I I want" should become "I want"; "the the car" should become "the car").
    *   Incorrect word segmentation if evident.
    *   Punctuation: Add appropriate punctuation (periods, commas, question marks) to make the text readable and grammatically sound. Capitalize the beginning of sentences.

{language_section}

3.  **Meaning Preservation:** The corrected text must retain the exact original meaning and intent of the speaker. Do NOT add new information or change the core message.

4.  **Style Preservation (High Priority):**
    *   If the original speech (once ASR errors are fixed) is already grammatically correct, natural-sounding, and clear in its phrasing and vocabulary, **DO NOT ALTER IT.** Your role is to be a meticulous corrector, not a stylistic rewriter.
    *   Maintain the user's original style of speaking, sentence structure, and vocabulary if it's already good and appropriate. For example, if the user speaks informally, keep it informal (unless it's an ASR error).

5.  **List Formatting:**
    *   If the user's speech implies a list (e.g., using "firstly", "secondly", "then this, then that", or a sequence of related short statements), format these items as bullet points (using '• ') or a numbered list (e.g., '1. ') if the order is explicitly stated or clearly sequential.
    *   Example: User says, "For the project, we need to define scope, then gather resources, and finally set a timeline."
      Expected output:
      • Define scope.
      • Gather resources.
      • Set a timeline.
    *   Do not impose list formatting if it's not clearly implied.

6.  **Conciseness:** Output only the refined text. No explanations, no apologies, no "Here's the refined text:". Just the text itself."""

def get_prompt_engineer_mode_instructions(language_code, preserve_original_languages=False):
    """Get instructions for Prompt Engineer mode."""
    
    # For prompt engineering, we always want English for the XML structure, but content can be in target language
    if preserve_original_languages:
        language_handling = "Preserve the original languages in the content sections while ensuring the XML structure and instructions are clear."
    else:
        language_handling = f"Translate the content fully into {language_code} while maintaining clear XML structure."
    
    return f"""CRITICAL INSTRUCTION: You are in 'Prompt Engineer' mode. Your objective is to transform the user's spoken input into a highly effective, structured prompt for another advanced AI system (like GPT-4.1, Gemini 2.5 Pro, Claude 3.7, etc).
The generated prompt structure will be in English, but content sections should follow your language settings: {language_handling}
The prompt MUST be enclosed in a main `<Prompt>` XML tag, following the detailed structure below.

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
2. {language_handling}
3. Based on the content, generate a complete, structured XML prompt according to the schema and principles outlined above."""

def get_email_mode_instructions(language_code, preserve_original_languages=False):
    """Get instructions for Email mode."""
    
    if preserve_original_languages:
        language_section = """Translation: Preserve the original languages as spoken in the email content. Do NOT translate between languages. If the user spoke in multiple languages, maintain that language mix in the email while ensuring professional formatting."""
        language_note = "preserving the original language mix as spoken"
    else:
        language_section = f"""Translation: Translate the corrected ASR transcript fully into the target language: {language_code}. All elements of the email must be in this language."""
        language_note = f"in the target language: {language_code}"
    
    return f"""CRITICAL INSTRUCTION: You are in 'Email' mode. Your task is to transform the user's spoken input into a professionally formatted email.
Follow these steps meticulously:

ASR Correction: First, carefully correct any errors in the provided ASR (Automatic Speech Recognition) transcript. This includes misspellings, stutters, repeated words, and phonetic mistakes. Ensure proper capitalization and punctuation for general readability before email formatting.

{language_section}

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

Example (email {language_note}):
Subject: New Campaign Launch Next Week

Dear Marketing Team,

I hope this email finds you well.

This is to inform you about the new campaign scheduled to launch next week. Please begin preparations for the following:
• Press release
• Social media posts

Please let me know if you have any questions.

Best regards,
[Your Name]

Your task is to apply these instructions to the ASR transcript provided below."""

def get_prompt_instructions(mode, language_code, preserve_original_languages=False):
    """
    Get the appropriate system prompt and mode instructions.
    
    Args:
        mode: Operation mode ('typer', 'prompt_engineer', 'email')
        language_code: Target language code (ISO 639-1)
        preserve_original_languages: Whether to preserve original languages
    
    Returns:
        Tuple of (system_prompt, mode_instructions)
    """
    language_instruction = get_language_instruction(language_code, preserve_original_languages)
    system_prompt_core = get_system_prompt_core(language_instruction)
    
    if mode == "typer":
        mode_instructions = get_typer_mode_instructions(language_code, preserve_original_languages)
    elif mode == "prompt_engineer":
        mode_instructions = get_prompt_engineer_mode_instructions(language_code, preserve_original_languages)
    elif mode == "email":
        mode_instructions = get_email_mode_instructions(language_code, preserve_original_languages)
    else:  # Default to typer
        mode_instructions = get_typer_mode_instructions(language_code, preserve_original_languages)
    
    return system_prompt_core, mode_instructions

def generate_dynamic_prompt(operation_mode: str, text: str, language_code: str, preserve_original_languages: bool = False) -> str:
    """
    Generate a dynamic prompt for streaming text processing based on operation mode.
    
    Args:
        operation_mode: The operation mode (typer, prompt_engineer, email)
        text: The transcribed text to process
        language_code: Target language code
        preserve_original_languages: Whether to preserve original languages
    
    Returns:
        Complete prompt string for the LLM
    """
    system_prompt, mode_instructions = get_prompt_instructions(operation_mode, language_code, preserve_original_languages)
    
    if preserve_original_languages:
        header_note = "to be processed while preserving original languages"
    else:
        header_note = f"to be processed into target language: {language_code}"
    
    user_content_header = f"--- BEGIN RAW ASR TRANSCRIPTION ({header_note}) ---"
    user_content_footer = "--- END RAW ASR TRANSCRIPTION ---"
    
    # Create the complete prompt
    complete_prompt = f"""{system_prompt}

{mode_instructions}

{user_content_header}
{text}
{user_content_footer}"""
    
    return complete_prompt
