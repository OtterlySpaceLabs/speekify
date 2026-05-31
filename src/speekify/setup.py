from __future__ import annotations

import logging
from collections.abc import Callable

from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn

from speekify.console import console


def warm_up_models(
    *,
    synthesizer: object,
    translator: object,
    sentiment_analyzer: object,
    include_translation: bool,
    include_sentiment: bool,
    logger: logging.Logger,
) -> None:
    logger.info(
        "Warmup started include_translation=%s include_sentiment=%s",
        include_translation,
        include_sentiment,
    )
    warmups: list[tuple[str, Callable[[], object]]] = [
        ("Supertonic model", lambda: getattr(synthesizer, "engine")),
    ]
    if include_translation:
        warmups.append(("Translation model", lambda: getattr(translator, "backend")))
    if include_sentiment:
        warmups.append(("Emotion model", lambda: getattr(sentiment_analyzer, "backend")))

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Preparing models", total=len(warmups))
        for label, load_model in warmups:
            progress.update(task_id, description=label)
            load_model()
            progress.advance(task_id)

    logger.info(
        "Warmup finished include_translation=%s include_sentiment=%s",
        include_translation,
        include_sentiment,
    )