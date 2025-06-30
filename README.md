
# Purpose

Generates grammar question Anki flashcards based on the difficulty level (A1, B2, etc) you set.

- Will generate sentences for each difficulty level provided, in the target language you set
- Will generate a grammar question at the appropriate difficulty level, and a "fun fact" about the sentence structure
- Will generate translations for sentences using DeepL, if none are present in CSV.
- Will generate audio for cards using ElevenLabs, if none is present in CSV.

## Setup

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Create .env file** in root with your API keys, labeled "DEEPL_API_KEY" and "OPENAI_API_KEY" and "ELEVEN_LABS_API_KEY"
3. **Configure settings** in `config/config.yaml`
    - See 'config.yaml' for more a more detailed explanation
4. **Run:** `scripts/main.py`

## Usage

### User Settings

In config/config.yaml, you can adjust the settings of the script:

Comment or uncomment `language_levels`, the values inside will determine the difficulty levels that you want to generate questions for e.g ["A1", "A2", etc]. Sentences will be split evenly according to how many difficulty levels you have.

Note: I think its beneficial to see grammar questions that are above your currently level.

### System instructions

There are three system instruction files: grammar_generator_agent.txt, system_source_gen_instructions, langauge specific instructions (e.g german_instructions.txt) (Note: **DO NOT** change the output format sections.)

- grammar_generator_agent.txt: generic instructions to be used no matter what the language. Add any general considerations you would like the agent to make there.
- langauge_specific_instructions: Instructions containing grammatical concepts that are appropriate to each level. Everything will run fine without it, but you can fine-tune what grammar concepts you want examined at each level by creating this file for your source language.
- system_source_gen_instructions.txt: Instructions for how the agent should generate example sentences

## Importing cards into Anki

Just import your 'anki_import.tsv' files directly into Anki. In data/anki_formatting, I have provided the html and css for creating this note type in Anki. Just remember to also add the fields to the 'Fields' section in Anki.

Do not allow HTML media when importing

Currently Anki doesnt offer a way to skip the header, so I had to remove them.

I reordered the column names to be a bit more logical, but its still annoying.

## Future improvements

- Batch the sentence-gen requests, to avoid the occasional duplicates.
