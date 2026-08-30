"""
Small helpers shared by every handler module: name/ID lookups with a cache,
and posting into a channel by name. Kept separate from app.py so the handler
modules do not have to import the Bolt app.
"""
_name_cache = {}
_id_cache = {}
_user_cache = {}


def channel_name(client, channel_id):
    if channel_id not in _name_cache:
        try:
            info = client.conversations_info(channel=channel_id)
            _name_cache[channel_id] = info["channel"]["name"] if info.get("ok") else ""
        except Exception:
            _name_cache[channel_id] = ""
    return _name_cache[channel_id]


def channel_id(client, name):
    """Look up a channel ID by name, across public and private channels."""
    if name in _id_cache:
        return _id_cache[name]

    cursor = None
    found = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel", limit=200, cursor=cursor, exclude_archived=True
        )
        for channel in resp.get("channels", []):
            if channel["name"] == name:
                found = channel["id"]
                break
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if found or not cursor:
            break

    _id_cache[name] = found
    return found


def actor_name(client, user_id):
    if user_id in _user_cache:
        return _user_cache[user_id]
    label = user_id
    try:
        info = client.users_info(user=user_id)
        if info.get("ok"):
            label = info["user"].get("real_name") or info["user"].get("name") or user_id
    except Exception:
        pass
    _user_cache[user_id] = label
    return label


def post_to(client, name, text, blocks=None, thread_ts=None):
    """Post into a channel by name. Returns the API response, or None if missing."""
    target = channel_id(client, name)
    if not target:
        print(f"CHANNEL NOT FOUND: #{name} — run setup_journey.py")
        return None
    kwargs = {"channel": target, "text": text}
    if blocks:
        kwargs["blocks"] = blocks
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    return client.chat_postMessage(**kwargs)


def ephemeral(client, channel, user, text, blocks=None):
    kwargs = {"channel": channel, "user": user, "text": text}
    if blocks:
        kwargs["blocks"] = blocks
    try:
        return client.chat_postEphemeral(**kwargs)
    except Exception as exc:
        print(f"EPHEMERAL FAILED: {exc}")
        return None


def clear_caches():
    _name_cache.clear()
    _id_cache.clear()
    _user_cache.clear()
