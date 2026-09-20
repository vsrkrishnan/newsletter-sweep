"""Notion sink — opt-in, via a Notion integration token (Settings →
Connections → Develop or manage integrations → New integration → copy the
token, then share the target page with it). Two clicks, no OAuth flow —
unlike Gmail, this is genuinely the easy case.

Talks to Notion's plain REST API directly rather than through an MCP
server: fewer moving parts to fail headlessly on a cron run, and no
dependency on an MCP host being present. If you're already running this
inside an MCP-capable agent, point that agent at the local markdown sink's
output instead and let its own Notion MCP connector mirror it — this sink
exists for the fully headless case.
"""
from __future__ import annotations

import os

import requests

from ..triage import TriagedItem
from .base import Sink

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"


class NotionSink(Sink):
    """Config:
    ```yaml
    - type: notion
      integration_token_env: NOTION_TOKEN
      parent_page_id: "your-notion-page-id"
    ```
    """

    def __init__(self, options: dict, dry_run: bool = True):
        super().__init__(options, dry_run)
        self.token = os.environ.get(options.get("integration_token_env", "NOTION_TOKEN"))
        self.parent_page_id = options.get("parent_page_id")
        if not self.parent_page_id:
            raise ValueError("Notion sink requires parent_page_id in config.yaml")

    def write_item(self, item: TriagedItem) -> str:
        if self.dry_run:
            return f"[dry-run] would create Notion page: {item.raw.title}"
        if not self.token:
            raise RuntimeError(
                "Notion sink configured but no token found. Set the env var named "
                "by integration_token_env (default: NOTION_TOKEN)."
            )
        resp = requests.post(
            f"{API_BASE}/pages",
            headers=self._headers(),
            json={
                "parent": {"page_id": self.parent_page_id},
                "properties": {"title": {"title": [{"text": {"content": item.raw.title}}]}},
                "children": self._blocks(item),
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Notion API error {resp.status_code}: {resp.text[:500]}")
        return f"created Notion page: {item.raw.title}"

    def write_digest(self, digest_markdown: str, digest_title: str) -> str:
        if self.dry_run:
            return f"[dry-run] would create Notion digest page: {digest_title}"
        if not self.token:
            raise RuntimeError("Notion sink configured but no token found.")
        resp = requests.post(
            f"{API_BASE}/pages",
            headers=self._headers(),
            json={
                "parent": {"page_id": self.parent_page_id},
                "properties": {"title": {"title": [{"text": {"content": digest_title}}]}},
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": digest_markdown[:2000]}}]},
                    }
                ],
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Notion API error {resp.status_code}: {resp.text[:500]}")
        return f"created Notion digest page: {digest_title}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _blocks(item: TriagedItem) -> list[dict]:
        def para(text: str) -> dict:
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": text[:2000]}}]},
            }

        return [
            para(f"Source: {item.raw.source_name}"),
            para(item.relevant_reason),
            para(f"Why this applies to me: {item.applies_to_me}"),
            para(item.raw.url),
        ]
