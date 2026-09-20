from pathlib import Path

from .base import Sink
from .markdown_sink import MarkdownSink
from .notion_sink import NotionSink

SINK_REGISTRY = {
    "markdown": MarkdownSink,
    "notion": NotionSink,
}


def build_sink(sink_type: str, options: dict, *, dry_run: bool, knowledge_path: Path) -> Sink:
    if sink_type == "markdown":
        return MarkdownSink(options, dry_run=dry_run, knowledge_path=knowledge_path)
    if sink_type == "notion":
        return NotionSink(options, dry_run=dry_run)
    raise ValueError(
        f"Unknown sink type '{sink_type}'. Available: {', '.join(SINK_REGISTRY)}."
    )


__all__ = ["Sink", "SINK_REGISTRY", "build_sink"]
