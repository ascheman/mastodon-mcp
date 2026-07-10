# Mastodon MCP Server

A lightweight [MCP](https://modelcontextprotocol.io/) server that lets Claude Code
create, edit, read, and delete Mastodon toots via the
[Mastodon.py](https://mastodonpy.readthedocs.io/) library.

## Tools

| Tool | Description |
|---|---|
| `create_toot` | Post a new toot (content, visibility, spoiler, images, thread reply) |
| `upload_media` | Upload an image and return its media ID (for `create_toot`) |
| `edit_toot` | Edit an existing toot by ID |
| `delete_toot` | Delete a toot by ID |
| `get_toot` | Fetch a single toot by ID |
| `get_timeline` | Fetch the home timeline |
| `search` | Search toots, accounts, or hashtags |
| `get_notifications` | Fetch recent notifications |

### Images and threads

To attach images, first `upload_media` each file (with its alt text) to get
a media ID, then pass the IDs to `create_toot` via `media_ids`
(comma-separated, up to **4 images** per toot). To build a thread, pass the
previous toot's `id` as `in_reply_to_id` on the next `create_toot` call.

## Setup

### 1. Create a Mastodon application

1. Log in to your Mastodon instance (e.g. https://mastodon.social)
2. Go to **Preferences → Development → New Application**
3. Name: `Claude Code MCP` (or whatever you like)
4. Scopes: `read`, `write:statuses`, `write:media`
5. Submit, then copy the **access token** (scroll down on the application
   details page — it's below the client key and client secret)

### 2. Install dependencies

```bash
cd mastodon-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Export the access token

Add to your shell profile (`.zshrc`, `.bashrc`, or `.envrc`):

```bash
export MASTODON_MCP_TOKEN="<your-access-token>"
# Optional — defaults to https://mastodon.social if not set:
# export MASTODON_INSTANCE_URL="https://your.instance"
```

The token is **not** stored in Claude Code's settings — it is inherited
from the shell environment at runtime. Keep it in one place (your shell
config or a secrets manager) and nowhere else.

### 4. Configure in Claude Code

```bash
claude mcp add mastodon \
  --transport stdio \
  -- ${PWD}/.venv/bin/python3 \
     ${PWD}/server.py
```

Run this from the `mastodon-mcp` directory after activating the venv.

No `-e` flags needed — the server reads `MASTODON_MCP_TOKEN` (and
optionally `MASTODON_INSTANCE_URL`) from the inherited environment.

### 5. Verify

```
claude mcp list          # should show "mastodon"
```

Then in a Claude Code session, try: "Show me my Mastodon timeline" or
"Post a direct message to myself saying 'test from Claude Code'".

## License

MIT
