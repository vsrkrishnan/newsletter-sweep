from .base import RawItem, Source
from .imap_source import IMAPSource
from .rss import RSSSource

SOURCE_REGISTRY: dict[str, type[Source]] = {
    "rss": RSSSource,
    "imap": IMAPSource,
}


def build_source(source_type: str, options: dict) -> Source:
    try:
        cls = SOURCE_REGISTRY[source_type]
    except KeyError:
        raise ValueError(
            f"Unknown source type '{source_type}'. Available: {', '.join(SOURCE_REGISTRY)}. "
            "A Gmail MCP server is documented as a power-user path in "
            "references/connector-setup.md but isn't a built-in source type — "
            "point an IMAP source at Gmail with an app password instead."
        )
    return cls(options)


__all__ = ["Source", "RawItem", "SOURCE_REGISTRY", "build_source"]
