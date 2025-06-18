import json
from pathlib import Path
import re

import pandas as pd
from openai import OpenAI
import numpy as np
import yaml

# Load config
config = yaml.safe_load(Path("config/config.yaml").read_text())
model_4o = config.get("model", "gpt-4o")
language_levels = ["A1", "A2", "B1", "B2"] #! Set the skill level of the questions asked (source material will be split equally.)
client = OpenAI(api_key=config["api_key"])

# Load prompts
system_prompt = Path("prompts/grammar_generator_agent.txt").read_text(encoding="utf-8")

# Grab CSV and load it into df (debug mode: starting with a few only)
sentences_df = pd.read_csv("data/source_material.csv", names=["index", "foreign_sentence", "english_sentence", "audio_file"])
# sentences_df = sentences_df.head(4) #!! DEBUG MODE

# todo - check if any english translations are missing and add them using DeepL
# todo - install a check to note add audio if its missing - fail gracefully

def SplitSentences(sentences_df) -> list[pd.DataFrame]:
    """Split df into equal parts for each langauge level desired, return list of dfs"""
    return np.array_split(sentences_df, len(language_levels))


split_sentences = SplitSentences(sentences_df)
print(f" type of split_sentences {type(split_sentences)}")

# Add appropriate 'language_level' column to each split section
for df, language_level in zip(split_sentences, language_levels):
    df["language_level"] = language_level

# Iterate through list of dfs and create grammar questions for each sentence
for sentence_batch in split_sentences:
    if sentence_batch["language_level"].iloc[0] != "A1": #!! DEBUG: Only generating A1's for now
        print("Now beyond AI, skipping...")
        break #!! Remember to swap this so I dont regenerate ones I already have

    for idx, row in sentence_batch.iterrows():

        user_content = f"Foreign sentence: {row["foreign_sentence"]}. Level: {row["language_level"]}"

        # pass these to agent so the can create a question
        response = client.chat.completions.create(
            model=model_4o,
            messages=[
                {"role": "system", "content": system_prompt},
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
    column_order = ["foreign_sentence", "question", "audio_file", "answer", "idiomatic_note", "english_sentence", "language_level"]
    sentence_batch = sentence_batch[column_order]

    sentence_batch.to_csv(f'data/anki_decks/anki_import_{row["language_level"]}.tsv', sep='\t', index=False, header=False, encoding='utf-8')
    print(f'Successfully exported Anki Deck: anki_import_{row["language_level"]}')
