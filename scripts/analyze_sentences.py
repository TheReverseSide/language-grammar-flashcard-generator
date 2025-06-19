import json
import os
import re
from pathlib import Path

import deepl
import numpy as np
import pandas as pd
import yaml
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load config
CONFIG_PATH = yaml.safe_load(Path("config/config.yaml").read_text())
MODEL = CONFIG_PATH["model"]
SOURCE_LANGUAGE = CONFIG_PATH["source_language"]
TARGET_LANGUAGE = CONFIG_PATH["target_language"]
LANGUAGE_LEVELS = CONFIG_PATH["language_levels"]
SOURCE_DATA_PATH = Path(CONFIG_PATH["source_data_path"])
OUTPUT_DIR = Path(CONFIG_PATH["output_dir"])

# Access .env api keys
OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepl_key = os.getenv("DEEPL_API_KEY")
TRANSLATOR = deepl.Translator(deepl_key) if deepl_key else None


def translate_sentence(sentence) -> str:
    """Receives a foreign langauge sentences and translates it to target language"""
    
    translated = TRANSLATOR.translate_text(
            sentence,
            source_lang=SOURCE_LANGUAGE,
            target_lang=TARGET_LANGUAGE
    )
    return translated.text.strip().capitalize()


def split_sentences_by_level(sentences_df) -> list[pd.DataFrame]:
    """Split df into equal parts for each langauge level desired, return list of dfs"""
    _split_sentences = np.array_split(sentences_df, len(LANGUAGE_LEVELS))

    # Add a column designating language level for each list
    for df, language_level in zip(_split_sentences, LANGUAGE_LEVELS):
        df["language_level"] = language_level
    
    return _split_sentences


def fill_missing_translations(missing_translations, sentences_df):
    if not TRANSLATOR:
        raise ValueError("DeepL API key not configured. Cannot translate sentences.")

    print(f"Translating {missing_translations.sum()} missing sentences...")
    sentences_df.loc[missing_translations, 'target_lang_sentence'] = sentences_df.loc[missing_translations, 'foreign_sentence'].apply(translate_sentence)


def generate_grammar_sentences(split_sentences, prompt_text):
    # Iterate through list of dfs and create grammar questions for each sentence
    for sentence_batch in split_sentences:
        # if sentence_batch["language_level"].iloc[0] != "A1": #!! DEBUG: Only generating A1's for now
        #     print("Now beyond A1, skipping...")
        #     break #!! Remember to swap this so I dont regenerate ones I already have

        for idx, row in sentence_batch.iterrows():

            user_content = f"Foreign sentence: {row["foreign_sentence"]}. Level: {row["language_level"]}"

            # pass these to agent so the can create a question
            response = OPENAI_CLIENT.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": user_content}
                ]
            )

            reply = response.choices[0].message.content

            # Remove markdown code blocks and strip
            reply = re.sub(r'^```json\s*', '', reply)
            reply = re.sub(r'\s*```$', '', reply)
            reply = reply.strip()

            try:
                parsed = json.loads(reply)
                print(f"{idx} Successfully parsed sentence: {row["foreign_sentence"]}")
            except json.JSONDecodeError as e:
                print(f"\nJson parsing failed: {e}")
                print(f"Reply was: {repr(reply)}\n")
                continue

            sentence_batch.at[idx, "question"] = parsed["question"]
            sentence_batch.at[idx, "answer"] = parsed["answer"]
            sentence_batch.at[idx, "idiomatic_note"] = parsed.get("idiomatic_note")

        # Changing the order to be a bit (slightly) more anki friendly
        column_order = ["foreign_sentence", "question", "audio_file", "answer", "idiomatic_note", "target_lang_sentence", "language_level"]
        sentence_batch = sentence_batch[column_order]

        sentence_batch.to_csv(f'{OUTPUT_DIR}/anki_import_{row["language_level"]}.tsv', sep='\t', index=False, header=False, encoding='utf-8')
        print(f'Successfully exported Anki Deck: anki_import_{row["language_level"]}')


def ensure_output_dir(output_dir: Path):
    if not output_dir.exists():
        print(f"Output directory {output_dir} does not exist, creating it.")
        output_dir.mkdir(parents=True, exist_ok=True)


def load_prompt_text(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


def main():
    #! config
    ensure_output_dir(OUTPUT_DIR)
    prompt_text = load_prompt_text(CONFIG_PATH["prompt_path"])

    #! Load data into df
    sentences_df = pd.read_csv(SOURCE_DATA_PATH, names=["index", "foreign_sentence", "target_lang_sentence", "audio_file"])
    # sentences_df = sentences_df.head(5) #!! DEBUG
    print(f"FIRST TARGET SENTENCE {sentences_df['target_lang_sentence']}")
   
    #! If there are missing translations in target language sentence, create them using DeepL
    missing_translations = sentences_df['target_lang_sentence'].isna() | (sentences_df['target_lang_sentence'] == '')
    if missing_translations.any():
        fill_missing_translations(missing_translations, sentences_df)

    #! Divide the sentences into equal parts and add appropriate 'language_level' column to each split section
    split_sentences = split_sentences_by_level(sentences_df)

    generate_grammar_sentences(split_sentences, prompt_text)


if __name__ == "__main__":
    main()