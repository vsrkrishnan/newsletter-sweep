import email
from datetime import datetime, timedelta, timezone

from newsletter_sweep.sources.imap_source import IMAPSource, _strip_html
from newsletter_sweep.sources.rss import RSSSource

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Test Newsletter</title>
<item>
  <title>Old post</title>
  <link>https://example.com/old</link>
  <pubDate>Mon, 01 Jan 2020 00:00:00 GMT</pubDate>
  <description>old content</description>
</item>
<item>
  <title>New post — check out https://example.com/deep-link and https://another.com</title>
  <link>https://example.com/new</link>
  <pubDate>{recent}</pubDate>
  <description>new content with links</description>
</item>
</channel></rss>
"""


def test_rss_source_filters_by_watermark_and_keeps_links(tmp_path, monkeypatch):
    recent = (datetime.now(timezone.utc)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(SAMPLE_RSS.format(recent=recent))

    source = RSSSource({"feeds": [str(feed_path)]})
    watermark = datetime(2024, 1, 1, tzinfo=timezone.utc)
    items = source.fetch_since(watermark)

    assert len(items) == 1  # old post filtered out by watermark
    assert items[0].title.startswith("New post")
    assert "https://example.com/deep-link" in items[0].title  # link text preserved, not stripped


def test_rss_source_survives_a_bad_feed(monkeypatch):
    source = RSSSource({"feeds": ["not-a-real-url-at-all://nope"]})
    # Must not raise — a single bad feed is logged and skipped.
    items = source.fetch_since(datetime.now(timezone.utc) - timedelta(days=1))
    assert items == []


def test_imap_looks_like_newsletter_by_header():
    msg = email.message.EmailMessage()
    msg["List-Unsubscribe"] = "<mailto:unsub@example.com>"
    msg["From"] = "someone@personal-domain.com"
    assert IMAPSource._looks_like_newsletter(msg) is True


def test_imap_looks_like_newsletter_by_sender_hint():
    msg = email.message.EmailMessage()
    msg["From"] = "digest@substack.com"
    assert IMAPSource._looks_like_newsletter(msg) is True


def test_imap_personal_email_is_not_a_newsletter():
    msg = email.message.EmailMessage()
    msg["From"] = "friend@gmail.com"
    assert IMAPSource._looks_like_newsletter(msg) is False


def test_strip_html_preserves_link_hrefs():
    html = '<p>Check out <a href="https://example.com/x">this piece</a> today.</p>'
    text = _strip_html(html)
    assert "https://example.com/x" in text
    assert "this piece" in text
