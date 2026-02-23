"""
🛡️ Immune System Skill: Forensic Snapshot
Category: Defense & Security
Trigger: Amygdala (Threat Detection) sensor

Captures a full system state snapshot — running processes, open ports,
active connections, recent file changes — and writes it to memory/forensics/.
A "crime scene photo" for post-incident analysis.
"""

import psutil
import os
import json
import time
from datetime import datetime


FORENSICS_DIR = "memory/forensics"


def run(data=None):
    """
    Capture a forensic snapshot of the current system state.

    data: str describing the trigger event (optional context).
    """
    os.makedirs(FORENSICS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = os.path.join(FORENSICS_DIR, f"snapshot_{timestamp}.json")

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "trigger": data or "Manual snapshot",
        "processes": _capture_processes(),
        "network_connections": _capture_connections(),
        "listening_ports": _capture_listeners(),
        "system_info": _capture_system_info(),
        "recent_logins": _capture_logins(),
    }

    with open(snapshot_file, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    proc_count = len(snapshot["processes"])
    conn_count = len(snapshot["network_connections"])
    port_count = len(snapshot["listening_ports"])

    result = (
        f"FORENSIC SNAPSHOT saved: {snapshot_file} "
        f"({proc_count} processes, {conn_count} connections, "
        f"{port_count} listening ports)"
    )
    print(f"[Cerebellum]: {result}")
    return result


def _capture_processes():
    """Capture all running processes with key attributes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent',
                                      'memory_percent', 'create_time', 'cmdline']):
        try:
            info = proc.info
            info['create_time_str'] = datetime.fromtimestamp(
                info.get('create_time', 0)
            ).isoformat()
            # Truncate cmdline for storage
            if info.get('cmdline'):
                info['cmdline'] = ' '.join(info['cmdline'])[:200]
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes


def _capture_connections():
    """Capture all active network connections."""
    connections = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            connections.append({
                "fd": conn.fd,
                "family": str(conn.family),
                "type": str(conn.type),
                "local": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                "status": conn.status,
                "pid": conn.pid,
            })
    except (psutil.AccessDenied, PermissionError):
        connections.append({"error": "Access denied — run as root for full data"})
    return connections


def _capture_listeners():
    """Capture all listening ports."""
    listeners = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                listeners.append({
                    "port": conn.laddr.port,
                    "address": conn.laddr.ip,
                    "pid": conn.pid,
                })
    except (psutil.AccessDenied, PermissionError):
        pass
    return listeners


def _capture_system_info():
    """Capture current system resource state."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "used_percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "used_percent": psutil.disk_usage('/').percent,
        },
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }


def _capture_logins():
    """Capture currently logged-in users."""
    users = []
    try:
        for user in psutil.users():
            users.append({
                "name": user.name,
                "terminal": user.terminal,
                "host": user.host,
                "started": datetime.fromtimestamp(user.started).isoformat(),
            })
    except Exception:
        pass
    return users
