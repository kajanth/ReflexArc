## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.
## 2024-05-24 - Insecure macOS Firewall Rule Generation
**Vulnerability:** The `skills/firewall_block.py` reflex created ephemeral temporary files at the predictable path `/tmp/nsa_pf_rules.conf` with default permissions. Also, `pfctl -f` completely flushes and replaces the active ruleset.
**Learning:** `pfctl -f` replaces the whole active ruleset; passing it a temporary rule file with a single rule erases all other rules. Also, predictable files in `/tmp` are susceptible to symlink attacks.
**Prevention:** Firewall rules must be appended to a persistent configuration file like `memory/nsa_pf_rules.conf`. Also, we must always enforce restricted access permissions using `os.open` with `0o600` mode and `os.fdopen`.
