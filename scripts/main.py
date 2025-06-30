import json, os, re, shutil, uuid
from pathlib import Path

import deepl
import numpy as np
import pandas as pd
import yaml
from openai import OpenAI
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings  


# Load environment variables from .env file
load_dotenv()

# Load config
CONFIG_PATH = yaml.safe_load(Path("config/config.yaml").read_text())
MODEL = CONFIG_PATH["model"]
TARGET_LANGUAGE = CONFIG_PATH["target_language"]
OUTPUT_LANGUAGE = CONFIG_PATH["output_language"]
LANGUAGE_LEVELS = CONFIG_PATH["language_levels"]
TARGET_DATA_PATH = Path(CONFIG_PATH["target_data_path"])
OUTPUT_DIR = Path(CONFIG_PATH["output_dir"])
CARD_COUNT = CONFIG_PATH["card_count"]
VOICE = CONFIG_PATH["voices"][TARGET_LANGUAGE]
COLLECTION_MEDIA  = CONFIG_PATH["ANKI_MEDIA"]

# Access .env api keys
OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepl_key = os.getenv("DEEPL_API_KEY")
TRANSLATOR = deepl.Translator(deepl_key) if deepl_key else None


def translate_sentence(sentence) -> str:
    """Receives a foreign langauge sentences and translates it to output language"""
    
    translated = TRANSLATOR.translate_text(
            sentence,
            source_lang=TARGET_LANGUAGE,
            target_lang=OUTPUT_LANGUAGE
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
    """Use DeepL to create translations for any missing ones"""
    if not TRANSLATOR:
        raise ValueError("DeepL API key not configured. Cannot translate sentences.")

    print(f"🈯 Translating {missing_translations.sum()} missing sentences...")
    sentences_df.loc[missing_translations, 'output_lang_sentence'] = sentences_df.loc[missing_translations, 'foreign_sentence'].apply(translate_sentence)
    return sentences_df


def generate_grammar_sentences(split_sentences, system_text):
    # Iterate through list of dfs and create grammar questions for each sentence
    for sentence_batch in split_sentences:
        for idx, row in sentence_batch.iterrows():

            user_content = f"Foreign sentence: {row["foreign_sentence"]}. Level: {row["language_level"]}"

            # pass these to agent so the can create a question
            response = OPENAI_CLIENT.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_text},
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
        column_order = ["foreign_sentence", "question", "audio_file", "answer", "idiomatic_note", "output_lang_sentence", "language_level"]
        sentence_batch = sentence_batch[column_order]

        sentence_batch.to_csv(f'{OUTPUT_DIR}/anki_import_{row["language_level"]}.tsv', sep='\t', index=False, header=False, encoding='utf-8')
        print(f'⬆️ Successfully exported Anki Deck: anki_import_{row["language_level"]}')


def ensure_output_dir(output_dir: Path):
    if not output_dir.exists():
        print(f"Output directory {output_dir} does not exist, creating it.")
        output_dir.mkdir(parents=True, exist_ok=True)


def load_system_instructions(sentence_gen=False) -> str:
    """Returns base instructions for agent plus language specific instructions or sentence-generation instructions, depending on sentence_gen flag"""

    if sentence_gen:
        base_instructions = Path(CONFIG_PATH["system_source_gen_instructions"]).read_text(encoding="utf-8")
        base_instructions = base_instructions + "\n\n" + f"Generate the sentences in {TARGET_LANGUAGE}"
        return base_instructions
    else:
        # Append language-specific instructions
        base_instructions = Path(CONFIG_PATH["system_instructions"]).read_text(encoding="utf-8")
        lang_specific_path = Path(f"system_instructions/{TARGET_LANGUAGE.lower()}_instructions.txt")

        if lang_specific_path.exists():
            lang_specific_instructions = lang_specific_path.read_text(encoding="utf-8")
            return base_instructions + "\n\n" + lang_specific_instructions
        
        return base_instructions # Just return base if not language-specific instructions exist

def generate_source_material(card_count, system_instructions):
    """Generate card_count cards of output langauge with """
    df = pd.DataFrame(index=range(card_count), columns=["index", "foreign_sentence", "question", "audio_file", "answer", "idiomatic_note", "output_lang_sentence", "language_level"])
    split_sentences = split_sentences_by_level(df)

    processed_dfs = []

    # fill out df with only those sentences, and empty values for the rest of the fields
    for sentence_batch in split_sentences:
        for idx, row in sentence_batch.iterrows():

            user_content = f"Level: {row["language_level"]}"

            # pass these to agent so the can create a question
            response = OPENAI_CLIENT.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_instructions},
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
                print(f"{idx}: Successfully parsed sentence. Reply was: {repr(reply)}")
            except json.JSONDecodeError as e:
                print(f"\nJson parsing failed: {e}")
                print(f"Reply was: {repr(reply)}\n")
                continue

            sentence_batch.at[idx, "foreign_sentence"] = parsed["sentence"]

        processed_dfs.append(sentence_batch)
    return processed_dfs


def generate_audio(translated_df_batches: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """
    Writes one MP3 per sentence into Anki's media folder
    Updates each row's `audio_file` field to  [sound:filename.mp3] and returns the same list of DataFrames.
    """
    print(f"🔊  Generating audio files...")

    api_key       = os.getenv("ELEVEN_LABS_API_KEY")
    client        = ElevenLabs(api_key=api_key)

    media_folder  = Path(CONFIG_PATH["ANKI_MEDIA"]).expanduser()
    media_folder.mkdir(parents=True, exist_ok=True)

    # helper: resolve "Otto" → voice_id, or treat string as id if already is
    def resolve_voice_id(name_or_id: str) -> str:
        voices = client.voices.get_all()
        for v in voices.voices:
            if v.name.lower() == name_or_id.lower() or v.voice_id == name_or_id:
                return v.voice_id
        raise ValueError(f"Voice '{name_or_id}' not found in your ElevenLabs account")

    VOICE_ID = resolve_voice_id(VOICE)

    #  Generate audio for every sentence
    for batch_idx, df in enumerate(translated_df_batches):
        for row_idx, row in df.iterrows():

            text = str(row.get("foreign_sentence", "")).strip()
            if not text:
                continue   # nothing to voice

            filename = f"{batch_idx:02d}_{row_idx:04d}_{VOICE_ID[:6]}.mp3"
            media_path = media_folder / filename

            if not media_path.exists():
                # call the new convert() endpoint – returns a chunk generator
                chunks = client.text_to_speech.convert(
                    voice_id      = VOICE_ID,
                    model_id      = "eleven_multilingual_v2",
                    text          = text,
                    output_format = "mp3_44100",
                    voice_settings = VoiceSettings( # optional tweaks
                        stability         = 0.2,
                        similarity_boost  = 1.0,
                        style             = 0.0,
                        use_speaker_boost = True,
                        speed             = 1.0,
                    ),
                )

                # write chunks to file
                with open(media_path, "wb") as f:
                    for chunk in chunks:
                        if chunk:
                            f.write(chunk)


            # set / update the Anki field
            df.at[row_idx, "audio_file"] = f"[sound:{filename}]"

    return translated_df_batches


def main():
    # config
    ensure_output_dir(OUTPUT_DIR)
    grammar_gen_system_instructions = load_system_instructions()
    sentence_gen_system_instructions = load_system_instructions(True)

    # Load data into df or generate it if it doesnt exist
    if not TARGET_DATA_PATH.exists():
        print("Generating sentences....")
        sentences_df = generate_source_material(CARD_COUNT, sentence_gen_system_instructions) # this however returns a big df
        
    #!! Disabling for now - it is unlikely that users will have their own sentences
        #!! Note to self: I should be able to uncomment else block and it will work. No other code was modified when disabling this feature.
        #!! On re-enable: ensure this still works with the new logic in place
        #!! On re-enable: ensure this doesnt break anything if you pass in a CSV with only one column (or at least only one with values in it)
        #!! On re-enable: Ensure that generate_audio will generate audio from source material
    # else:
    #     sentences_df = pd.read_csv(SOURCE_DATA_PATH, names=["index", "foreign_sentence", "output_lang_sentence", "audio_file"])
    #     sentences_df = sentences_df.head(50)
    #     # Divide the sentences into equal parts and add appropriate 'language_level' column to each split section
    #     sentences_df = split_sentences_by_level(sentences_df)

    # If there are missing translations in output language sentence, create them using DeepL
    translated_df_batches = []
    for sentence_batch in sentences_df:
        missing_translations = sentence_batch['output_lang_sentence'].isna() | (sentence_batch['output_lang_sentence'] == '')
        if missing_translations.any():
            sentence_batch = fill_missing_translations(missing_translations, sentence_batch)
        translated_df_batches.append(sentence_batch)

    # Generate audio files for sentence
    sentences_batches_with_audio = generate_audio(translated_df_batches)

    generate_grammar_sentences(sentences_batches_with_audio, grammar_gen_system_instructions)


if __name__ == "__main__":
    main()
