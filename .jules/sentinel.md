## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.

## 2026-03-22 - SSRF Redirect Bypass
**Vulnerability:** Initial SSRF protections via `is_safe_url` only validated the target URL but failed to handle subsequent HTTP redirects. An attacker could bypass the filter by supplying a safe URL that redirects to a restricted local IP (e.g., `127.0.0.1`).
**Learning:** Checking a URL before making a request is insufficient if the HTTP client automatically follows redirects without reapplying the same security checks to the new location.
**Prevention:** Implement a custom `HTTPRedirectHandler` that runs the `is_safe_url` checks on the `newurl` during every redirect before continuing the request, and use this handler to perform all outbound HTTP requests.
## 2024-03-24 - SSRF Bypass via HTTP Redirects
**Vulnerability:** Initial SSRF protections were bypassed because `urllib.request.urlopen` automatically follows HTTP redirects without validating the target URL of the redirect. An attacker could provide a safe URL that redirects to a restricted internal IP.
**Learning:** Standard URL validation prior to the request is insufficient when the HTTP client auto-follows redirects.
**Prevention:** Implement a custom `urllib.request.HTTPRedirectHandler` to intercept and validate the `newurl` against internal IP restrictions on every redirect before following it. Always use `safe_urlopen` which uses this custom handler instead of directly using `urllib.request.urlopen`.

## 2024-10-25 - macOS Firewall Rule Flush via Ephemeral File
**Vulnerability:** In `skills/firewall_block.py`, macOS firewall rules were appended to an ephemeral file (`/tmp/nsa_pf_rules.conf`) and then applied using `pfctl -f`. Because `pfctl -f` completely flushes and replaces the active ruleset, using an ephemeral or easily tampered-with file in `/tmp` poses a critical risk of unintentionally wiping out other essential firewall rules or allowing malicious rule injection.
**Learning:** `pfctl -f` replaces the entire ruleset. It must be paired with a secure, persistent configuration file containing all necessary rules, not a temporary scratchpad.
**Prevention:** When modifying macOS firewall rules via `pfctl -f`, rules must be appended to a persistent configuration file within the application's secure memory directory (e.g., `memory/nsa_pf_rules.conf`), and path resolving should use an absolute path relative to the script file (e.g., `os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'memory', 'nsa_pf_rules.conf'))`).
