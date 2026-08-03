"""create_specialist_group — Hermes native tool.

Creates a Feishu group using App B (user_access_token from .lark-cli-user-token.json),
adds the bot, invites the user, writes channel_overrides with specialist_id,
and sends an initial message. Always uses App B CLI identity.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

import yaml

from tools.registry import registry

logger = logging.getLogger(__name__)

SPECIALISTS = {
    "req-agent": {
        "name": "REQ Agent",
        "domains": "requirements, PRD, user stories, SYS.2, SWE.1",
    },
    "test-agent": {
        "name": "Test Agent",
        "domains": "test cases, test plans, QA, test automation",
    },
    "arch-agent": {
        "name": "Arch Agent",
        "domains": "architecture, system design, detailed design, microservices",
    },
}

_FEISHU_BASE = "https://open.feishu.cn"


def _get_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))


def _feishu_get(token: str, path: str) -> dict:
    url = f"{_FEISHU_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _feishu_post(token: str, path: str, body: dict) -> dict:
    url = f"{_FEISHU_BASE}{path}"
    payload = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _get_user_access_token() -> tuple[str, str, str]:
    """Resolve App B access token. Returns (token, app_id, error).

    Tries user_access_token first (user-owned groups), falls back to
    tenant_access_token from app credentials (bot-owned groups).
    """
    token_path = _get_hermes_home() / ".lark-cli-user-token.json"
    if not token_path.exists():
        # Fallback: get tenant_access_token from config.yaml App B credentials
        return _get_bot_token_from_config()

    try:
        data = json.loads(token_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return "", "", f"Failed to read App B token file: {exc}"

    app_id = data.get("app_id", "")
    app_secret = data.get("app_secret", "")
    if not app_id or not app_secret:
        return "", "", (
            "App B credentials incomplete. "
            "Please re-register on the Channels page."
        )

    access_token = data.get("access_token", "")
    expires_at = data.get("expires_at", 0)

    if access_token and expires_at > time.time() + 60:
        return access_token, app_id, ""

    refresh_token = data.get("refresh_token", "")
    if refresh_token:
        new_token, new_refresh, err = _refresh_user_token(app_id, app_secret, refresh_token)
        if new_token:
            data["access_token"] = new_token
            data["refresh_token"] = new_refresh or refresh_token
            data["expires_at"] = int(time.time()) + 6900
            try:
                token_path.write_text(json.dumps(data, indent=2))
            except OSError:
                pass
            return new_token, app_id, ""

    # No valid user token — fallback to tenant_access_token (bot-owned groups)
    return _get_bot_token_from_config()


def _get_bot_token_from_config() -> tuple[str, str, str]:
    """Fallback: get tenant_access_token using App B app_id/app_secret from config.yaml."""
    config_path = _get_hermes_home() / "config.yaml"
    if not config_path.exists():
        return "", "", "App B (Feishu CLI) is not configured. Please complete setup on the Channels page."

    try:
        cfg = yaml.safe_load(config_path.read_text()) or {}
        extra = cfg.get("platforms", {}).get("feishu_app_b", {}).get("extra", {})
        app_id = extra.get("app_id", "")
        app_secret = extra.get("app_secret", "")
    except Exception as exc:
        return "", "", f"Failed to read App B config: {exc}"

    if not app_id or not app_secret:
        return "", "", "App B (Feishu CLI) is not configured. Please complete setup on the Channels page."

    # Get tenant_access_token (bot identity)
    url = f"{_FEISHU_BASE}/open-apis/auth/v3/app_access_token/internal"
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        token = data.get("app_access_token", "")
        if not token:
            return "", "", f"Failed to get App B token: {data}"
        return token, app_id, ""
    except Exception as exc:
        return "", "", f"App B token request failed: {exc}"


def _refresh_user_token(app_id: str, app_secret: str, refresh_token: str) -> tuple[str, str, str]:
    app_token_url = f"{_FEISHU_BASE}/open-apis/auth/v3/app_access_token/internal"
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        app_token_url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        app_access_token = data.get("app_access_token", "")
        if not app_access_token:
            return "", "", f"Failed to get app_access_token for refresh: {data}"
    except Exception as exc:
        return "", "", f"App access token request failed: {exc}"

    url = f"{_FEISHU_BASE}/open-apis/authen/v1/oidc/refresh_access_token"
    refresh_payload = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(
        url, data=refresh_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_access_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("code") != 0:
            return "", "", f"Token refresh failed: {data.get('msg', data)}"
        token_data = data.get("data", {})
        return token_data.get("access_token", ""), token_data.get("refresh_token", ""), ""
    except Exception as exc:
        return "", "", f"Token refresh request failed: {exc}"


def _load_specialist_soul(specialist_id: str) -> str:
    soul_path = _get_hermes_home() / "souls" / f"{specialist_id}.md"
    if soul_path.exists():
        return soul_path.read_text()
    return f"You are the {SPECIALISTS[specialist_id]['name']}. Domains: {SPECIALISTS[specialist_id]['domains']}."


def _update_config(chat_id: str, specialist_id: str, system_prompt: str, group_name: str) -> None:
    config_path = _get_hermes_home() / "config.yaml"
    config = {}
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}

    platforms = config.setdefault("platforms", {})
    feishu_app_b = platforms.setdefault("feishu_app_b", {})
    channel_overrides = feishu_app_b.setdefault("channel_overrides", {})
    channel_overrides[chat_id] = {
        "model": "claude-sonnet-4.6",
        "provider": "bedrock",
        "system_prompt": system_prompt,
        "api_mode": "claude_code_sdk",
        "specialist_id": specialist_id,
    }

    config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))


def _create_specialist_group(args: dict, **kwargs) -> str:
    specialist_id = args.get("specialist_id", "")
    title = args.get("title", "")
    context_summary = args.get("context_summary", "")

    if specialist_id not in SPECIALISTS:
        return json.dumps({"error": f"Unknown specialist_id: {specialist_id}. Valid: {list(SPECIALISTS.keys())}"})

    specialist = SPECIALISTS[specialist_id]

    user_token, app_id, err = _get_user_access_token()
    if not user_token:
        return json.dumps({"error": err})

    group_name = title[:50]

    # Create group via user_access_token (user-owned)
    try:
        resp = _feishu_post(user_token, "/open-apis/im/v1/chats", {
            "name": group_name,
            "description": context_summary[:200],
            "chat_type": "group",
        })
    except Exception as exc:
        return json.dumps({"error": f"Failed to create group: {exc}"})

    if resp.get("code") != 0:
        return json.dumps({"error": f"Feishu API error: {resp.get('msg', resp)}"})

    chat_id = (resp.get("data") or {}).get("chat_id", "")
    if not chat_id:
        return json.dumps({"error": f"No chat_id in response: {resp}"})

    # Add App B bot to group
    try:
        _feishu_post(user_token, f"/open-apis/im/v1/chats/{chat_id}/members", {
            "member_id_type": "app_id",
            "id_list": [app_id],
        })
    except Exception:
        logger.debug("Failed to add bot to group %s", chat_id)

    # Invite user
    user_open_id = os.environ.get("FEISHU_USER_OPEN_ID", "")
    if user_open_id:
        try:
            _feishu_post(user_token, f"/open-apis/im/v1/chats/{chat_id}/members", {
                "member_id_type": "open_id",
                "id_list": [user_open_id],
            })
        except Exception:
            pass

    # Write channel_overrides
    system_prompt = _load_specialist_soul(specialist_id)
    _update_config(chat_id, specialist_id, system_prompt, group_name)

    # Generate a permanent share/invite link so non-members can join
    chat_link = f"https://applink.feishu.cn/client/chat/open?chatId={chat_id}"
    try:
        link_resp = _feishu_post(
            user_token,
            f"/open-apis/im/v1/chats/{chat_id}/link",
            {"validity_period": "permanently"},
        )
        share_link = (link_resp.get("data") or {}).get("share_link", "")
        if share_link:
            chat_link = share_link
    except Exception:
        pass

    # Send initial message
    initial_msg = (
        f"{specialist['name']} is ready.\n\n"
        f"Context:\n{context_summary}\n\n"
        f"You can message directly in this group — no need to @mention the bot."
    )
    try:
        _feishu_post(user_token, "/open-apis/im/v1/messages?receive_id_type=chat_id", {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": initial_msg}),
        })
    except Exception:
        pass

    return json.dumps({
        "chat_id": chat_id,
        "chat_link": chat_link,
        "group_name": group_name,
        "specialist_id": specialist_id,
        "specialist_name": specialist["name"],
        "api_mode": "claude_code_sdk",
        "message": f"Group created. Share this link with the user: {chat_link}",
    })


def _check_requirements(**kwargs) -> bool:
    """Available when App B credentials are accessible (token file or config.yaml)."""
    if (_get_hermes_home() / ".lark-cli-user-token.json").exists():
        return True
    # Fallback: check if App B config is in config.yaml
    config_path = _get_hermes_home() / "config.yaml"
    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text()) or {}
            extra = cfg.get("platforms", {}).get("feishu_app_b", {}).get("extra", {})
            if extra.get("app_id") and extra.get("app_secret"):
                return True
        except Exception:
            pass
    return False


CREATE_SPECIALIST_GROUP_SCHEMA = {
    "name": "create_specialist_group",
    "description": (
        "Create a dedicated Feishu group chat for a specialist agent (Test Agent, "
        "Arch Agent, or REQ Agent). Uses App B CLI identity to create the group. "
        "The specialist group runs an isolated Claude Code SDK session with its own "
        "system prompt. Returns chat_link to share with the user."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "specialist_id": {
                "type": "string",
                "enum": ["req-agent", "test-agent", "arch-agent"],
                "description": "ID of the specialist agent to delegate to",
            },
            "title": {
                "type": "string",
                "description": "Group name (max 50 chars), e.g. 'REQ: Order System User Stories'",
            },
            "context_summary": {
                "type": "string",
                "description": "Brief context/task description to hand off to the specialist",
            },
        },
        "required": ["specialist_id", "title", "context_summary"],
    },
}

registry.register(
    name="create_specialist_group",
    toolset="feishu",
    schema=CREATE_SPECIALIST_GROUP_SCHEMA,
    handler=_create_specialist_group,
    check_fn=_check_requirements,
    emoji="👥",
    description="Create a specialist Feishu group (App B CLI identity)",
)
