from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from speekify.config import (
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_TTS_LANG,
    DEFAULT_VOICE,
    SUPPORTED_TTS_LANGUAGES,
    UNKNOWN_TTS_LANGUAGE,
    VOICE_NAMES,
)
from speekify.logging_utils import configure_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speekify",
        description="Genere un fichier WAV depuis un texte ou une URL.",
        epilog=_build_cli_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        nargs="*",
        help="Texte a lire ou URL unique a extraire. Omettre seulement avec stdin.",
    )
    parser.add_argument("--url", action="store_true", help="Force le mode URL.")
    parser.add_argument("--title", default="", help="Titre de sortie optionnel.")
    parser.add_argument("--voice", choices=VOICE_NAMES, default=DEFAULT_VOICE, help="Voix Supertonic.")
    parser.add_argument(
        "--lang",
        default=DEFAULT_TTS_LANG,
        type=_parse_language_code,
        help="Code ISO 639-1 supporte par Supertonic, par exemple en, fr ou ja. Defaut: en.",
    )
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED, help="Vitesse de lecture.")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Nombre de steps de synthese.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Dossier de sortie. Par defaut: repertoire courant.",
    )
    return parser


def build_setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speekify setup",
        description="Telecharge et prechauffe les modeles utilises par Speekify.",
    )
    parser.add_argument(
        "--skip-translation",
        action="store_true",
        help="Ne prechauffe pas le modele de traduction anglais vers francais.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == "setup":
        return _run_setup(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    source = _read_source(args.source)
    if source is None:
        parser.error("une source texte, URL ou stdin est requise")

    logger, log_path = configure_logger()
    synthesizer = _build_synthesizer()
    translator = _build_translator()

    try:
        generation = asyncio.run(
            generate_audio(
                _build_generation_request(
                    source_text=source,
                    voice=args.voice,
                    language_code=args.lang,
                    speed=args.speed,
                    steps=args.steps,
                    title=args.title.strip(),
                    is_url_mode=args.url,
                    output_dir=args.output_dir or Path.cwd(),
                ),
                synthesizer=synthesizer,
                translator=translator,
                logger=logger,
            )
        )
    except Exception as exc:
        logger.exception("CLI generation failed")
        print(_format_error_message(exc, log_path), file=sys.stderr)
        return 1

    print(_format_success_message(generation.output_path, generation.artifact))
    return 0


def _run_setup(argv: list[str]) -> int:
    parser = build_setup_parser()
    args = parser.parse_args(argv)
    logger, log_path = configure_logger()
    synthesizer = _build_synthesizer()
    translator = _build_translator()

    try:
        _warm_up_models(
            synthesizer=synthesizer,
            translator=translator,
            include_translation=not args.skip_translation,
            logger=logger,
        )
    except Exception as exc:
        logger.exception("CLI setup failed")
        print(_format_error_message(exc, log_path), file=sys.stderr)
        return 1

    print("Modele Supertonic pret.")
    if args.skip_translation:
        print("Modele de traduction ignore.")
    else:
        print("Modele de traduction pret.")
    return 0


def _build_synthesizer() -> object:
    from speekify.tts import SupertonicSynthesizer

    return SupertonicSynthesizer()


def _build_translator() -> object:
    from speekify.translation import HuggingFaceTranslator

    return HuggingFaceTranslator()


def _build_generation_request(**kwargs: Any) -> object:
    from speekify.workflow import GenerationRequest

    return GenerationRequest(**kwargs)


def generate_audio(*args: Any, **kwargs: Any) -> Awaitable[Any]:
    from speekify.workflow import generate_audio as run_generate_audio

    return run_generate_audio(*args, **kwargs)


def _warm_up_models(*, synthesizer: object, translator: object, include_translation: bool, logger) -> None:
    logger.info("Warmup started include_translation=%s", include_translation)
    _ = getattr(synthesizer, "engine")
    if include_translation:
        _ = getattr(translator, "backend")
    logger.info("Warmup finished include_translation=%s", include_translation)


def _parse_language_code(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_TTS_LANGUAGES:
        available = ", ".join(SUPPORTED_TTS_LANGUAGES)
        raise argparse.ArgumentTypeError(
            "Le code langue doit etre supporte par Supertonic. "
            f"Valeurs disponibles: {available}"
        )
    return normalized


def _build_cli_epilog() -> str:
    examples = [
        "Exemples:",
        '  speekify "Hello world"',
        '  speekify --lang fr "Bonjour tout le monde"',
        '  speekify --lang ja https://example.com/article',
        "  speekify setup --help",
        "",
        f"Langues supportees: {', '.join(SUPPORTED_TTS_LANGUAGES)}",
        f"Utilisez {UNKNOWN_TTS_LANGUAGE} pour le mode language-agnostic si necessaire.",
    ]
    return "\n".join(examples)


def _read_source(source_parts: list[str]) -> str | None:
    inline_source = " ".join(source_parts).strip()
    if inline_source:
        return inline_source

    try:
        is_tty = sys.stdin.isatty()
    except OSError:
        return None

    if not is_tty:
        try:
            piped_source = sys.stdin.read().strip()
        except OSError:
            return None
        return piped_source or None

    return None


def _format_error_message(error: Exception, log_path: Path) -> str:
    message = str(error)
    if "caracteres non supportes par Supertonic" in message:
        return f"{message}. Supprime ou remplace ces caracteres. Voir {log_path}"
    return f"{message} (voir {log_path})"


def _format_success_message(output_path: Path, artifact: Any) -> str:
    lines = [str(output_path), f"{artifact.duration_seconds:.2f}s"]
    notes = artifact.summary_notes()
    if notes:
        lines.append("Auto: " + "; ".join(notes))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
