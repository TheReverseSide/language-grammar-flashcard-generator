
# Purpose

To generate grammar questions based on provided sentences at the difficulty level (A1, B2, etc) that you set.

## Usage

This takes a csv with the format: index, foreign_sentence, english_sentence, link to anki-format sound file (if you have them)
You can also pass a version without english_sentences and it will use DeepL (add API key to .env file) to automatically create them

In the list `language_levels`, add the difficulty levels that you want to generate questions for e.g ["A1", "A2", etc].
It will then split your source material evenly according to how many difficulty levels you add.
Note: I think its beneficial to see grammar questions that are above your currently level anyways.

Add any personal considerations you would like the agent to make in file `prompts/grammar_generator_agent.txt`.

### Importing cards into Anki

Do not allow HTML media when importing

Currently Anki doesnt offer a way to skip the header, so I had to remove them.
I reordered the column names to be a bit more logical, but its still annoying.