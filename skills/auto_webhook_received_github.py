"""
Skill: GitHub Webhook Handler
Category: integration
Trigger: Webhook receptor sensor — GitHub event received

Real implementation: parses the GitHub webhook payload, routes events
by type (push, pull_request, issues, workflow_run, ping), logs structured
data, writes a summary to the changes log, and takes event-specific actions
such as logging a code change entry when a push is received.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)


def _log_change(event_type: str, repo: str, description: str, author: str = "github") -> None:
    """Append a structured entry to the changes log."""
    try:
        from utils.changes_logger import log_change
        log_change(
            change_type="github_event",
            file=f"github/{repo}",
            description=description,
            author=author,
            extra={"event_type": event_type, "repo": repo},
        )
    except Exception as e:
        logger.warning("changes_log_write_failed", error=str(e))


def _handle_push(payload: dict) -> str:
    repo    = payload.get("repository", {}).get("full_name", "unknown/repo")
    ref     = payload.get("ref", "refs/heads/unknown")
    branch  = ref.split("/")[-1]
    commits = payload.get("commits", [])
    pusher  = payload.get("pusher", {}).get("name", "unknown")
    head_commit = payload.get("head_commit") or (commits[-1] if commits else {})
    msg = head_commit.get("message", "no message")[:120] if head_commit else "no commits"

    summary = f"Push to {repo}:{branch} by {pusher} — {len(commits)} commit(s) — \"{msg}\""
    logger.info("github_push", repo=repo, branch=branch, pusher=pusher,
                commit_count=len(commits), head_message=msg)
    _log_change("push", repo, summary, author=pusher)
    return summary


def _handle_pull_request(payload: dict) -> str:
    action = payload.get("action", "unknown")
    pr     = payload.get("pull_request", {})
    repo   = payload.get("repository", {}).get("full_name", "unknown")
    num    = pr.get("number", "?")
    title  = pr.get("title", "no title")[:80]
    user   = pr.get("user", {}).get("login", "unknown")
    base   = pr.get("base", {}).get("ref", "?")
    head   = pr.get("head", {}).get("ref", "?")
    summary = f"PR #{num} [{action}] \"{title}\" by {user} — {head} → {base} in {repo}"
    logger.info("github_pull_request", action=action, repo=repo, pr=num, title=title, user=user)
    _log_change("pull_request", repo, summary, author=user)
    return summary


def _handle_workflow_run(payload: dict) -> str:
    run    = payload.get("workflow_run", {})
    repo   = payload.get("repository", {}).get("full_name", "unknown")
    name   = run.get("name", "unknown workflow")
    status = run.get("status", "unknown")
    conclusion = run.get("conclusion") or "in_progress"
    branch = run.get("head_branch", "?")
    icon   = "✅" if conclusion == "success" else ("❌" if conclusion == "failure" else "⏳")
    summary = f"{icon} Workflow '{name}' [{conclusion}] on {repo}:{branch}"
    level = "error" if conclusion == "failure" else "info"
    getattr(logger, level)("github_workflow_run",
                           workflow=name, status=status, conclusion=conclusion,
                           repo=repo, branch=branch)
    return summary


def _handle_issues(payload: dict) -> str:
    action = payload.get("action", "unknown")
    issue  = payload.get("issue", {})
    repo   = payload.get("repository", {}).get("full_name", "unknown")
    num    = issue.get("number", "?")
    title  = issue.get("title", "no title")[:80]
    user   = issue.get("user", {}).get("login", "unknown")
    summary = f"Issue #{num} [{action}] \"{title}\" by {user} in {repo}"
    logger.info("github_issue", action=action, repo=repo, issue=num, title=title)
    return summary


def _handle_ping(payload: dict) -> str:
    zen  = payload.get("zen", "")
    hook = payload.get("hook", {}).get("type", "webhook")
    logger.info("github_ping", hook_type=hook, zen=zen)
    return f"GitHub ping received ({hook}) — Zen: {zen}"


EVENT_HANDLERS = {
    "push":         _handle_push,
    "pull_request": _handle_pull_request,
    "workflow_run": _handle_workflow_run,
    "issues":       _handle_issues,
    "ping":         _handle_ping,
}


def run(data=None):
    """
    Handle a GitHub webhook event.

    Args:
        data: dict payload (with 'event_type' and 'payload' keys from the receptor,
              or a raw GitHub payload dict), or a JSON string

    Returns:
        Status message describing what was processed
    """
    # Unpack from the webhook receptor envelope if present
    event_type = "unknown"
    payload = {}

    if isinstance(data, dict):
        event_type = (
            data.get("event_type")  # from webhook receptor
            or data.get("X-GitHub-Event")
            or ("push" if "commits" in data else
                "pull_request" if "pull_request" in data else
                "workflow_run" if "workflow_run" in data else
                "issues" if "issue" in data else
                "ping" if "zen" in data else "unknown")
        )
        payload = data.get("payload", data)
    elif isinstance(data, str):
        try:
            payload = json.loads(data)
            event_type = (
                "push" if "commits" in payload else
                "pull_request" if "pull_request" in payload else
                "ping" if "zen" in payload else "unknown"
            )
        except json.JSONDecodeError:
            logger.warning("github_webhook_invalid_json", raw=data[:200])
            return f"GitHub webhook received but payload is not valid JSON: {data[:80]}"

    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        try:
            result = handler(payload)
        except Exception as e:
            logger.error("github_webhook_handler_error", event_type=event_type, error=str(e))
            result = f"Handler error for {event_type}: {e}"
    else:
        logger.info("github_webhook_unhandled_event", event_type=event_type)
        result = f"GitHub '{event_type}' event received and logged (no specific handler)"

    return result
