# Connector setup: IMAP, Gmail MCP, and Notion

## IMAP (recommended path to Gmail or any other inbox)

1. In your email provider, generate an **app password** — for Gmail: Google
   Account → Security → 2-Step Verification → App passwords. This is a
   16-character password scoped to one application; it is not your login
   password and can be revoked independently.
2. Set two environment variables (never put credentials in `config.yaml` —
   the config file is meant to be shareable/committable):
   ```bash
   export NEWSLETTER_IMAP_USER="you@gmail.com"
   export NEWSLETTER_IMAP_APP_PASSWORD="the 16-char app password"
   ```
3. Add a source to `config.yaml`:
   ```yaml
   sources:
     - type: imap
       host: imap.gmail.com
       port: 993
       username_env: NEWSLETTER_IMAP_USER
       password_env: NEWSLETTER_IMAP_APP_PASSWORD
       mailbox: INBOX
       unread_only: true
   ```

This is the practical default for Gmail. It's minutes of setup, not an
OAuth consent flow.

## Gmail via a self-hosted MCP server (power-user path)

If you're already running this inside an MCP-capable agent (Claude Code,
etc.), you might expect to point it at a Gmail MCP server instead of IMAP.
Two things worth knowing before you do:

- **The hosted Gmail connector some agent products offer (e.g. claude.ai's)
  cannot be reused here.** That connector's OAuth is held by the host
  platform, not exposed as a general-purpose endpoint a separate process
  can call into. A *self-hosted* Gmail MCP server is a different thing —
  and one you'd run and authenticate yourself.
- **Self-hosting it means registering your own Google Cloud OAuth
  application and publishing a consent screen.** Google blocks generic/
  third-party OAuth clients from requesting Gmail's restricted scopes, so
  a shared client id won't work — every user of a self-hosted Gmail MCP
  server has to go through Google Cloud Console once, which is a
  30+ minute detour the first time. IMAP + an app password sidesteps this
  entirely, which is why it's the default recommendation above.

If you still want the MCP path (e.g. you want unified tool access across
several MCP-based agents), point `newsletter-sweep` at your self-hosted
Gmail MCP server's endpoint and treat message fetch as equivalent to the
IMAP source's contract (title, sender, date, plaintext body). This isn't a
built-in source type as of v0.1 — see `references/adapter-authoring.md` to
add one.

## Notion (opt-in sink)

Genuinely the easy case — two clicks, no OAuth flow:

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) →
   **New integration** → give it a name → copy the **Internal Integration
   Token**.
2. Open the Notion page you want items written under → **···** menu →
   **Connections** → add your integration.
3. Copy that page's id from its URL (the 32-character hex string after the
   last `-` or as the whole path segment).
4. Set the token as an environment variable and reference the page id in
   config:
   ```bash
   export NOTION_TOKEN="secret_..."
   ```
   ```yaml
   sinks:
     - type: markdown
     - type: notion
       integration_token_env: NOTION_TOKEN
       parent_page_id: "your-32-char-page-id"
   ```

The built-in Notion sink talks to Notion's REST API directly, so it works
the same whether you're running this by hand, on cron, or in GitHub
Actions — it doesn't depend on an MCP host being present.
