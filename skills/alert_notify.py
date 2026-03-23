"""
🧬 Endocrine Skill: Alert Notify
Category: Scheduling & Communication
Trigger: Any high-priority spike

Sends notifications via webhook (Slack, Discord, or generic HTTP POST)
for critical events. The organism's "adrenaline rush" — ensures important
spikes reach the human operator.

Configure webhook URLs via environment variables or memory/notify_config.json.
"""

import os
import json
import time
import urllib.request
import urllib.error
from utils.ssrf_protection import is_safe_url, safe_urlopen


CONFIG_FILE = "memory/notify_config.json"
NOTIFY_LOG = "memory/notify_log.json"


def run(data=None):
    """
    Send a notification for a critical event.

    data: str describing the event to notify about.
    """
    if not data:
        return "No event data to notify about."

    config = _load_config()
    results = []

    # Try each configured channel
    for channel in config.get("channels", []):
        channel_type = channel.get("type", "webhook")
        url = channel.get("url")


        if not url:
            continue

        if not is_safe_url(url):
            results.append(f"{channel.get('name', channel_type)}: BLOCKED (SSRF protection)")
            continue

        try:
            if channel_type == "slack":
                success = _send_slack(url, data)
            elif channel_type == "discord":
                success = _send_discord(url, data)
            else:
                success = _send_webhook(url, data)

            status = "SENT" if success else "FAILED"
            results.append(f"{channel.get('name', channel_type)}: {status}")
        except Exception as e:
            results.append(f"{channel.get('name', channel_type)}: ERROR ({e})")

    # Log the notification attempt
    _log_notify(data, results)

    if not results:
        # No channels configured — log locally as fallback
        _log_local_alert(data)
        results.append("No webhook channels configured — logged locally")

    result = f"ALERT NOTIFY: {'; '.join(results)}"
    print(f"[Cerebellum]: {result}")
    return result


def _load_config():
    """Load notification configuration."""
    # Check environment variables first
    config = {"channels": []}

    slack_url = os.environ.get("NSA_SLACK_WEBHOOK")
    if slack_url:
        config["channels"].append({
            "type": "slack", "name": "Slack", "url": slack_url
        })

    discord_url = os.environ.get("NSA_DISCORD_WEBHOOK")
    if discord_url:
        config["channels"].append({
            "type": "discord", "name": "Discord", "url": discord_url
        })

    generic_url = os.environ.get("NSA_WEBHOOK_URL")
    if generic_url:
        config["channels"].append({
            "type": "webhook", "name": "Webhook", "url": generic_url
        })

    # Merge with config file if it exists
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                file_config = json.load(f)
            config["channels"].extend(file_config.get("channels", []))
        except (json.JSONDecodeError, IOError):
            pass

    return config


def _send_slack(url, message):
    """Send a Slack webhook notification."""
    payload = json.dumps({
        "text": f"🧠 *NSA Alert*\n{message}",
        "username": "NSA Nervous System",
        "icon_emoji": ":brain:",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = safe_urlopen(req, timeout=10)
    return resp.status == 200


def _send_discord(url, message):
    """Send a Discord webhook notification."""
    payload = json.dumps({
        "content": f"🧠 **NSA Alert**\n{message}",
        "username": "NSA Nervous System",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = safe_urlopen(req, timeout=10)
    return 200 <= resp.status < 300


def _send_webhook(url, message):
    """Send a generic HTTP POST webhook."""
    payload = json.dumps({
        "source": "nsa_nervous_system",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": message,
        "severity": "high",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = safe_urlopen(req, timeout=10)
    return 200 <= resp.status < 300


def _log_notify(data, results):
    """Log notification attempts."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": data[:200],
        "results": results,
    }

    log = []
    if os.path.exists(NOTIFY_LOG):
        try:
            with open(NOTIFY_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)
    log = log[-100:]  # Keep last 100

    os.makedirs(os.path.dirname(NOTIFY_LOG), exist_ok=True)
    with open(NOTIFY_LOG, "w") as f:
        json.dump(log, f, indent=2)


def _log_local_alert(data):
    """Fallback: Log alert to a local file."""
    alert_file = "memory/local_alerts.log"
    os.makedirs(os.path.dirname(alert_file), exist_ok=True)
    with open(alert_file, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {data}\n")
