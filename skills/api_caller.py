"""
🦾 Motor Cortex Skill: API Caller
Category: Environment Interaction
Trigger: Cortex delegation / Scheduled tasks

Makes HTTP requests to pre-configured external APIs (health checks,
status pages, data fetchers). The organism's ability to "reach out
and touch" external services without burning Cortex tokens.

Endpoints are configured via memory/api_endpoints.json.
"""

import json
import os
import time
import urllib.request
import urllib.error
from utils.ssrf_protection import is_safe_url, safe_urlopen


ENDPOINTS_FILE = "memory/api_endpoints.json"
API_LOG = "memory/api_call_log.json"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RESPONSE_SIZE = 5000  # characters


def run(data=None):
    """
    Call a pre-configured API endpoint.

    data: str with the endpoint name or action:
          - "<endpoint_name>" : Call the named endpoint
          - "list" : List all configured endpoints
          - "add:<name>:<url>:<method>" : Add a new endpoint
    """
    _ensure_config()

    if not data or data.strip().lower() == "list":
        return _list_endpoints()

    if data.strip().lower().startswith("add:"):
        return _add_endpoint(data)

    return _call_endpoint(data.strip())


def _ensure_config():
    """Create endpoints config if missing with some defaults."""
    os.makedirs(os.path.dirname(ENDPOINTS_FILE), exist_ok=True)
    if not os.path.exists(ENDPOINTS_FILE):
        default_config = {
            "endpoints": {
                "github_status": {
                    "url": "https://www.githubstatus.com/api/v2/status.json",
                    "method": "GET",
                    "description": "GitHub service status",
                },
                "openai_status": {
                    "url": "https://status.openai.com/api/v2/status.json",
                    "method": "GET",
                    "description": "OpenAI service status",
                },
                "ip_check": {
                    "url": "https://api.ipify.org?format=json",
                    "method": "GET",
                    "description": "Check external IP address",
                },
            }
        }
        with open(ENDPOINTS_FILE, "w") as f:
            json.dump(default_config, f, indent=2)


def _load_endpoints():
    """Load endpoint configurations."""
    try:
        with open(ENDPOINTS_FILE, "r") as f:
            return json.load(f).get("endpoints", {})
    except (json.JSONDecodeError, IOError):
        return {}


def _call_endpoint(name):
    """Call a named endpoint and return the result."""
    endpoints = _load_endpoints()

    if name not in endpoints:
        available = ", ".join(sorted(endpoints.keys()))
        return f"Unknown endpoint '{name}'. Available: {available}"


    endpoint = endpoints[name]
    url = endpoint["url"]

    if not is_safe_url(url):
        return f"BLOCKED: URL '{url}' is not safe (SSRF protection)"

    method = endpoint.get("method", "GET").upper()
    headers = endpoint.get("headers", {})
    body = endpoint.get("body")

    try:
        req_data = None
        if body and method in ("POST", "PUT", "PATCH"):
            req_data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = headers.get("Content-Type", "application/json")

        req = urllib.request.Request(url, data=req_data, method=method)
        for key, val in headers.items():
            req.add_header(key, val)

        start = time.time()
        resp = safe_urlopen(req, timeout=DEFAULT_TIMEOUT)
        latency = time.time() - start

        response_body = resp.read().decode("utf-8", errors="replace")

        # Truncate large responses
        if len(response_body) > MAX_RESPONSE_SIZE:
            response_body = response_body[:MAX_RESPONSE_SIZE] + "... [truncated]"

        # Try to parse JSON for cleaner output
        try:
            parsed = json.loads(response_body)
            response_body = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            pass

        _log_call(name, url, resp.status, latency)

        result = (
            f"API [{name}] ({method} {resp.status}, {latency:.2f}s):\n"
            f"{response_body}"
        )

    except urllib.error.HTTPError as e:
        _log_call(name, url, e.code, 0)
        result = f"API [{name}]: HTTP {e.code} — {e.reason}"

    except urllib.error.URLError as e:
        _log_call(name, url, 0, 0)
        result = f"API [{name}]: Connection failed — {e.reason}"

    except Exception as e:
        _log_call(name, url, 0, 0)
        result = f"API [{name}]: Error — {e}"

    print(f"[Cerebellum]: {result[:200]}")
    return result


def _add_endpoint(data):
    """
    Add a new endpoint.
    Format: "add:<name>:<url>:<method>"
    """
    parts = data.split(":")
    if len(parts) < 3:
        return "Invalid format. Use: add:<name>:<url>[:<method>]"

    name = parts[1]
    methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    method = "GET"
    url = ""

    if parts[-1].upper() in methods:
        method = parts[-1].upper()
        url = ":".join(parts[2:-1])
    else:
        url = ":".join(parts[2:])

    if not is_safe_url(url):
        result = f"BLOCKED: URL '{url}' is not safe (SSRF protection)"
        print(f"[Cerebellum]: {result}")
        return result

    endpoints = _load_endpoints()
    endpoints[name] = {
        "url": url,
        "method": method.upper(),
        "description": f"Added {time.strftime('%Y-%m-%d')}",
    }

    config = {"endpoints": endpoints}
    with open(ENDPOINTS_FILE, "w") as f:
        json.dump(config, f, indent=2)

    result = f"ADDED endpoint '{name}': {method.upper()} {url}"
    print(f"[Cerebellum]: {result}")
    return result


def _list_endpoints():
    """List all configured endpoints."""
    endpoints = _load_endpoints()
    if not endpoints:
        return "No API endpoints configured."

    lines = ["API ENDPOINTS:"]
    for name, ep in sorted(endpoints.items()):
        method = ep.get("method", "GET")
        desc = ep.get("description", "")
        lines.append(f"  • {name:20s} {method:6s} {ep['url'][:50]} — {desc}")

    result = "\n".join(lines)
    print(f"[Cerebellum]: {result}")
    return result


def _log_call(name, url, status, latency):
    """Log API call for audit trail."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint": name,
        "url": url,
        "status": status,
        "latency": round(latency, 3),
    }

    log = []
    if os.path.exists(API_LOG):
        try:
            with open(API_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = []

    log.append(entry)
    log = log[-200:]  # Keep last 200

    os.makedirs(os.path.dirname(API_LOG), exist_ok=True)
    with open(API_LOG, "w") as f:
        json.dump(log, f, indent=2)
