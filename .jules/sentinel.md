## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.

## 2024-03-24 - Prevent Local Privilege Escalation via Predictable Temporary Files
**Vulnerability:** The firewall_block skill writes rules to a globally writable, highly predictable location (`/tmp/nsa_pf_rules.conf`). A malicious local user could pre-create this file as a symlink to a sensitive system file (like `/etc/passwd`), causing the process to blindly append rules to it when executed (likely as root via `pfctl`).
**Learning:** Security scripts running as root or modifying system state must never trust predictable files in shared directories like `/tmp`.
**Prevention:** Always write security-sensitive state to application-controlled directories (like `memory/`), and enforce strict file permissions (e.g., `0o600`) upon creation using `os.open` combined with `os.O_CREAT | os.O_WRONLY | os.O_APPEND`.
