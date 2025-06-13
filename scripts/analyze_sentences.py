from openai import OpenAI
import pandas as pd
import json
from pathlib import Path
import numpy as np
import yaml

"""Runs our ChatGPT grammar analyzer"""

print("German Grammar Nut awakens.")

# Load config
config = yaml.safe_load(Path("config/config.yaml").read_text())
model_4o = config.get("model", "gpt-4o")
language_levels = ["A1", "A2", "B1", "B2"] #! Set the skill level of the questions asked (source material will be split equally.)
client = OpenAI(api_key=config["api_key"])

# Load prompts
system_prompt = Path("prompts/grammar_generator_agent.txt").read_text(encoding="utf-8")

# Grab CSV and load it into df (debug mode: starting with a few only)
sentences_df = pd.read_csv("data/German Grammar Flashcards.csv", names=["index", "german_sentence", "english_sentence", "audio_file"])
# sentences_df = sentences_df.head(4) #!! DEBUG MODE

def QuarterSentences(sentences_df):
    """Get the whole df of sentences and split it into equal parts for each langauge level desired"""
    return np.array_split(sentences_df, len(language_levels))


sentence_quarters = QuarterSentences(sentences_df)

# Add a 'language_levels' column to each quarter
for df, language_level in zip(sentence_quarters, language_levels):
    df["language_level"] = language_level

# Iterate through list of dfs and create grammar questions for each sentence
for sentence_batch in sentence_quarters:
    if sentence_batch["language_level"].iloc[0] != "A1": #!! DEBUG: Only generating A1's for now 
        break #!! Remember to swap this so I dont regenerate ones I already have

    for idx, row in sentence_batch.iterrows():

        user_content = f"German sentence: {row["german_sentence"]}. Level: {row["language_level"]}"

        # pass these to agent so he can create a question
        response = client.chat.completions.create(
            model=model_4o,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )

        reply = response.choices[0].message.content
        try:
            parsed = json.loads(reply)
            print("REPLY FROM OPENAI:", repr(reply))
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for sentence {row["german_sentence"]}. Reply was:", repr(reply))
            continue

        parsed = json.loads(reply) #? I guess this doesnt need to be ran twice
        sentence_batch.at[idx, "question"] = parsed["question"]
        sentence_batch.at[idx, "answer"] = parsed["answer"]
        sentence_batch.at[idx, "idiomatic_note"] = parsed.get("idiomatic_note")

    column_order = ["german_sentence", "question", "audio_file", "answer", "idiomatic_note", "english_sentence", "language_level"]
    sentence_batch = sentence_batch[column_order] # Changing the order to be a bit (slightly) more anki friendly
    sentence_batch.to_csv(f'data/anki_decks/anki_import_{row["language_level"]}.tsv', sep='\t', index=False, header=False, encoding='utf-8')
    print(f'Saved: anki_import_{row["language_level"]}')
