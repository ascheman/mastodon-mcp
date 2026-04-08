#!/usr/bin/env python3
"""
Mastodon MCP Server — create, edit, read, and delete toots via Claude Code.

Environment variables:
    MASTODON_INSTANCE_URL  e.g. https://mastodon.social
    MASTODON_MCP_TOKEN  OAuth access token with read + write:statuses + write:media
"""

import json
import os
import sys

from mastodon import Mastodon, MastodonError
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Mastodon client
# ---------------------------------------------------------------------------

_instance_url = os.environ.get("MASTODON_INSTANCE_URL", "https://mastodon.social")
_access_token = os.environ.get("MASTODON_MCP_TOKEN")

if not _access_token:
    print("MASTODON_MCP_TOKEN environment variable is required", file=sys.stderr)
    sys.exit(1)

_client = Mastodon(
    access_token=_access_token,
    api_base_url=_instance_url,
)

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("mastodon")


def _status_to_dict(status) -> dict:
    """Extract the fields we care about from a Mastodon status object."""
    # Boosts have their real content in the nested 'reblog' object.
    reblog = status.get("reblog")
    source = reblog if reblog else status
    result = {
        "id": str(status["id"]),
        "url": source.get("url") or source.get("uri"),
        "content": source["content"],
        "text": source.get("text", ""),
        "visibility": status["visibility"],
        "created_at": str(status["created_at"]),
        "reblogs_count": source["reblogs_count"],
        "favourites_count": source["favourites_count"],
        "account": source["account"]["acct"],
    }
    if reblog:
        result["boosted_by"] = status["account"]["acct"]
    return result


@mcp.tool()
def create_toot(
    content: str,
    visibility: str = "public",
    spoiler_text: str = "",
) -> str:
    """Create a new toot (status post).

    Args:
        content: The text of the toot (up to 500 characters on most instances).
        visibility: One of 'public', 'unlisted', 'private', 'direct'.
        spoiler_text: Optional content warning / subject line.
    """
    try:
        status = _client.status_post(
            content,
            visibility=visibility,
            spoiler_text=spoiler_text or None,
        )
        return json.dumps(_status_to_dict(status), indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def upload_media(
    file_path: str,
    description: str = "",
) -> str:
    """Upload an image file to Mastodon and return its media ID.

    The returned ID can be passed to create_toot or edit_toot_with_media.

    Args:
        file_path: Absolute path to the image file on disk.
        description: Alt text for the image (accessibility).
    """
    try:
        media = _client.media_post(
            file_path,
            description=description or None,
        )
        return json.dumps({
            "id": str(media["id"]),
            "url": media.get("url") or media.get("preview_url"),
            "description": media.get("description", ""),
        }, indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def edit_toot(
    toot_id: str,
    content: str,
    spoiler_text: str = "",
    media_ids: str = "",
) -> str:
    """Edit an existing toot by its ID, optionally replacing its media.

    Args:
        toot_id: The numeric ID of the toot to edit.
        content: The new text content.
        spoiler_text: Optional updated content warning.
        media_ids: Comma-separated media IDs (from upload_media) to replace
                   the toot's current attachments. Leave empty to keep existing media.
    """
    try:
        kwargs = {
            "status": content,
            "spoiler_text": spoiler_text or None,
        }
        if media_ids.strip():
            kwargs["media_ids"] = [int(mid.strip()) for mid in media_ids.split(",")]
        status = _client.status_update(int(toot_id), **kwargs)
        return json.dumps(_status_to_dict(status), indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def delete_toot(toot_id: str) -> str:
    """Delete a toot by its ID.

    Args:
        toot_id: The numeric ID of the toot to delete.
    """
    try:
        _client.status_delete(int(toot_id))
        return json.dumps({"deleted": toot_id})
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_toot(toot_id: str) -> str:
    """Fetch a single toot by its ID.

    Args:
        toot_id: The numeric ID of the toot.
    """
    try:
        status = _client.status(int(toot_id))
        return json.dumps(_status_to_dict(status), indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_timeline(limit: int = 20) -> str:
    """Fetch the home timeline.

    Args:
        limit: Number of toots to fetch (max 40).
    """
    try:
        statuses = _client.timeline_home(limit=min(limit, 40))
        return json.dumps([_status_to_dict(s) for s in statuses], indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search(query: str, search_type: str = "statuses") -> str:
    """Search Mastodon for toots, accounts, or hashtags.

    Args:
        query: The search query string.
        search_type: One of 'statuses', 'accounts', 'hashtags'.
    """
    try:
        results = _client.search_v2(query, result_type=search_type)
        if search_type == "statuses":
            return json.dumps([_status_to_dict(s) for s in results["statuses"]], indent=2)
        elif search_type == "accounts":
            return json.dumps(
                [{"id": str(a["id"]), "acct": a["acct"], "url": a["url"]} for a in results["accounts"]],
                indent=2,
            )
        elif search_type == "hashtags":
            return json.dumps(
                [{"name": t["name"], "url": t["url"]} for t in results["hashtags"]],
                indent=2,
            )
        return json.dumps(results)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_notifications(limit: int = 10) -> str:
    """Fetch recent notifications (mentions, boosts, favourites, follows).

    Args:
        limit: Number of notifications to fetch (max 40).
    """
    try:
        notifs = _client.notifications(limit=min(limit, 40))
        result = []
        for n in notifs:
            entry = {
                "id": str(n["id"]),
                "type": n["type"],
                "created_at": str(n["created_at"]),
                "account": n["account"]["acct"],
            }
            if n.get("status"):
                entry["status"] = _status_to_dict(n["status"])
            result.append(entry)
        return json.dumps(result, indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_my_statuses(limit: int = 10) -> str:
    """Fetch my own recent toots (not boosts).

    Args:
        limit: Number of toots to fetch (max 40).
    """
    try:
        me = _client.me()
        statuses = _client.account_statuses(me["id"], limit=min(limit, 40), exclude_reblogs=True)
        return json.dumps([_status_to_dict(s) for s in statuses], indent=2)
    except MastodonError as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
