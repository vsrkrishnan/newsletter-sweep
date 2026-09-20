"""IMAP source — the practical path to Gmail (or any mailbox) without OAuth.

An app password (Google: Account → Security → App Passwords) is dramatically
simpler for a user to set up than a Google Cloud OAuth consent screen, which
is what a self-hosted Gmail MCP server would otherwise require — Google
blocks generic OAuth clients from requesting restricted Gmail scopes, so
every user of an OAuth-based tool has to register their own app first. IMAP
sidesteps that entirely. See references/connector-setup.md.

Stdlib only: imaplib + email. No third-party IMAP dependency.
"""
from __future__ import annotations

import email
import imaplib
import logging
import os
import re
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

from .base import RawItem, Source

logger = logging.getLogger(__name__)

# Heuristics for "this is a newsletter, not personal/transactional mail" —
# ported from the original command's Step 1 characteristics list.
NEWSLETTER_HEADER_HINTS = ("list-unsubscribe",)
NEWSLETTER_SENDER_HINTS = (
    "substack.com", "beehiiv.com", "mailchimp", "convertkit", "ghost.io",
    "campaign-archive", "mailgun", "sendgrid",
)


class IMAPSource(Source):
    """Config:
    ```yaml
    - type: imap
      host: imap.gmail.com
      port: 993
      username_env: NEWSLETTER_IMAP_USER
      password_env: NEWSLETTER_IMAP_APP_PASSWORD
      mailbox: INBOX
      unread_only: true
    ```
    Credentials are read from environment variables, never written to config —
    the config file is meant to be shareable/committable.
    """

    def fetch_since(self, watermark: datetime) -> list[RawItem]:
        host = self.options["host"]
        port = self.options.get("port", 993)
        username = os.environ.get(self.options.get("username_env", "NEWSLETTER_IMAP_USER"))
        password = os.environ.get(self.options.get("password_env", "NEWSLETTER_IMAP_APP_PASSWORD"))
        mailbox = self.options.get("mailbox", "INBOX")
        unread_only = self.options.get("unread_only", True)

        if not username or not password:
            raise RuntimeError(
                "IMAP source configured but credentials are missing. Set the "
                f"env vars named by username_env/password_env in config.yaml "
                "(defaults: NEWSLETTER_IMAP_USER, NEWSLETTER_IMAP_APP_PASSWORD)."
            )

        with imaplib.IMAP4_SSL(host, port) as conn:
            conn.login(username, password)
            conn.select(mailbox)

            criteria = ["SINCE", watermark.strftime("%d-%b-%Y")]
            if unread_only:
                criteria.insert(0, "UNSEEN")
            status, data = conn.search(None, *criteria)
            if status != "OK":
                logger.warning("IMAP search failed: %s", status)
                return []

            items: list[RawItem] = []
            for msg_id in data[0].split():
                item = self._fetch_message(conn, msg_id, watermark)
                if item is not None:
                    items.append(item)
            return items

    def _fetch_message(self, conn, msg_id: bytes, watermark: datetime) -> RawItem | None:
        try:
            status, msg_data = conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                return None
            msg = email.message_from_bytes(msg_data[0][1])
        except Exception as exc:
            logger.warning("Failed to fetch/parse message %s, skipping: %s", msg_id, exc)
            return None

        if not self._looks_like_newsletter(msg):
            return None

        published = self._message_date(msg) or datetime.now(timezone.utc)
        if published <= watermark:
            return None

        return RawItem(
            source_name=self._decode(msg.get("From", "")),
            title=self._decode(msg.get("Subject", "(no subject)")),
            url="",  # the body itself carries the links; canonical URL is resolved during triage
            published=published,
            body=self._extract_body(msg),
            sender=self._decode(msg.get("From", "")),
        )

    @staticmethod
    def _looks_like_newsletter(msg) -> bool:
        if any(h in msg for h in ("List-Unsubscribe", "List-Unsubscribe-Post")):
            return True
        sender = (msg.get("From") or "").lower()
        return any(hint in sender for hint in NEWSLETTER_SENDER_HINTS)

    @staticmethod
    def _decode(value: str) -> str:
        parts = decode_header(value)
        return "".join(
            p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p
            for p, enc in parts
        )

    @staticmethod
    def _message_date(msg) -> datetime | None:
        date_header = msg.get("Date")
        if not date_header:
            return None
        try:
            dt = parsedate_to_datetime(date_header)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_body(msg) -> str:
        """Plaintext preferred, HTML stripped-to-text as fallback. Never
        filters out URL-bearing lines — see the module docstring in base.py.
        """
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get(
                    "Content-Disposition"
                ):
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
            for part in msg.walk():
                if part.get_content_type() == "text/html" and not part.get(
                    "Content-Disposition"
                ):
                    html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    return _strip_html(html)
            return ""
        payload = msg.get_payload(decode=True)
        if payload is None:
            return msg.get_payload() or ""
        text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        return _strip_html(text) if msg.get_content_type() == "text/html" else text


def _strip_html(html: str) -> str:
    """Minimal tag stripping — keeps link hrefs visible (as `text (url)`)
    so triage still has real URLs to work with, rather than reducing an
    email to prose with no links at all.
    """
    html = re.sub(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: f"{re.sub('<[^>]+>', '', m.group(2))} ({m.group(1)})",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()
