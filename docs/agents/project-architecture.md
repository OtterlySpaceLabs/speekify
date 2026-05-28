# Project Architecture

- Keep the CLI boundary in `src/speekify/__main__.py`: Typer/Click parsing, stdin handling, Rich status/progress/success/error rendering, and `setup` warmup live there.
- Keep orchestration in `src/speekify/workflow.py`: it resolves text vs URL input, optionally translates, prepares text, builds the output path, loads the model, synthesizes, and saves.
- Keep runtime adapters separated: `extract.py` handles readable URL/text normalization, `translation.py` handles English-to-French Hugging Face translation, `tagging/` handles sparse Supertonic inline tags with rules and CardiffNLP sentiment, `tts.py` wraps Supertonic, `naming.py` creates safe timestamped WAV paths, and `logging_utils.py` owns `logs/speekify.log` retention.