
# Purpose

To generate grammar questions based on provided sentences at the difficulty level (A1, B2, etc) that you set.

Optionally adds included audio and translates to target language when translations are not included.

## Setup

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Create .env file** with your API keys, labeled "DEEPL_API_KEY" and "OPENAI_API_KEY"
    - Simply create a new file with the name '.env' and add a line for the api keys in the format: "DEEPL_API_KEY={your api key}"
3. **Place source material** in `data/` with name `source_material.csv`
    - See Source Material section for instructions
4. **Configure settings** in `config/config.yaml`
5. **Run:** `python scripts/analyze_sentences.py`

## Usage

#### Source Material

This takes a csv with the columns: *index, foreign_sentence, target_lang_sentence, anki-format sound file*.
Place the csv in the data folder with the name 'source_material.csv'.

Dont worry if you dont have sound files, it will work fine without them. (I will add automatic TTS in the future)

You can also pass a version without translated versions of the sentences and it will use DeepL (requires API key) to automatically create them.

#### User Settings

In config/config.yaml, you can adjust the settings of the script:

Add or remove `language_levels`, the values inside will determine the difficulty levels that you want to generate questions for e.g ["A1", "A2", etc]. Source material will be split evenly according to how many difficulty levels you have.

Note: I think its beneficial to see grammar questions that are above your currently level anyways.

#### System instructions

There are two system instruction files: grammar_generator_agent.txt, and langauge specific instructions (e.g german_instructions.txt)

- Grammar Generator Agent: generic instructions to be used no matter what the language. Add any general considerations you would like the agent to make there.
- Note: **DO NOT** change the output format section.
- Language specific instructions: Instructions containing grammatical concepts that are appropriate to each level. Everything will run fine without it, but you can fine-tune what grammar concepts you want examined at each level by creating this file for your source language.

#### Importing cards into Anki

Just import your 'anki_import.tsv' files directly into Anki. In data/anki_formatting, I have provided the html and css for creating this note type in Anki. Just remember to also add the fields to the 'Fields' section in Anki.

Do not allow HTML media when importing

Currently Anki doesnt offer a way to skip the header, so I had to remove them.

I reordered the column names to be a bit more logical, but its still annoying.

## Future ideas

Generate audio using ElevenLabs if audio content is missing - Need to investigate anki audio requirements
Analyze sentences as higher difficulty levels (ex: C1) to see if the sentences are sufficiently difficult to ask C1-level questions (ex: "the cat is red" isnt valid as a C1 level grammar investigation)