
# Purpose

To generate grammar questions based on provided sentences at the difficulty level (A1, B2, etc) that you set.

Optionally adds included audio and translates to target language when translations are not included.

## Setup

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Create .env file** with your API keys, labeled "DEEPL_API_KEY" and "OPENAI_API_KEY"
3. **Place source material** in `data/source_material.csv`
4. **Configure settings** in `config/config.yaml`
5. **Run:** `python scripts/analyze_sentences.py`

## Usage

#### Source Material

This takes a csv with the columns: *index, foreign_sentence, target_lang_sentence, anki-format sound file*.

Place the csv in the data folder with the name 'source_material.csv'.

Dont worry if you dont have sound files, it will work fine without them.

You can even pass a version without translated versions of the sentences and it will use DeepL (requires API key) to automatically create them.

#### User Settings

In config/config.yaml, you can adjust the settings of the script:

Add or remove `language_levels`, the values inside will determine the difficulty levels that you want to generate questions for e.g ["A1", "A2", etc]. Source material will be split evenly according to how many difficulty levels you have.

Note: I think its beneficial to see grammar questions that are above your currently level anyways.

Add any personal considerations you would like the agent to make in file `prompts/grammar_generator_agent.txt`. **DO NOT** change the output format section.

#### Importing cards into Anki

Do not allow HTML media when importing

Currently Anki doesnt offer a way to skip the header, so I had to remove them.

I reordered the column names to be a bit more logical, but its still annoying.
