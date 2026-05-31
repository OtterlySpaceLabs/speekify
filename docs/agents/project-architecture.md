# Project Architecture

- Keep the CLI boundary in `src/speekify/__main__.py`: Typer/Click parsing, command routing, stdin handling, and compatibility wrappers live there.
- Keep user-facing terminal rendering in `src/speekify/cli_rendering.py`; keep setup model warmup/progress in `src/speekify/setup.py`.
- Keep orchestration in `src/speekify/workflow.py`: it resolves text vs URL input, optionally translates, prepares text, inspects or synthesizes, builds the output path, saves, and writes metadata.
- Keep runtime adapters separated: `extract.py` is the public extraction facade, `extract_common.py` has shared extraction primitives, `extractors/` handles provider-specific URL extraction, `translation.py` handles English-to-French Hugging Face translation, `tagging/` handles sparse Supertonic inline tags with rules and CardiffNLP sentiment, `tts.py` wraps Supertonic, `naming.py` creates safe timestamped WAV paths, `metadata.py` writes JSON sidecars plus the local RSS podcast feed, `user_config.py` owns optional TOML defaults, and `logging_utils.py` owns `logs/speekify.log` retention.
