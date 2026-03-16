## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.
## 2024-03-24 - Insecure Temporary File Creation
**Vulnerability:** Temporary files containing sensitive operations (like firewall rules) were created using the default `open(..., "a")`, which relies on the process's default `umask` and could allow local attackers to view or modify rules before they are executed.
**Learning:** Default Python file operations do not automatically apply restrictive permissions on newly created files, opening up symlink or local privilege escalation risks in `/tmp`.
**Prevention:** When creating or appending to security-sensitive files (like firewall rules or configuration), always use `os.open` with the desired flags (`os.O_WRONLY | os.O_CREAT | os.O_APPEND`) and an explicit restrictive mode like `0o600`. Then, wrap it with `os.fdopen()`.
