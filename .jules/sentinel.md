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

## 2026-03-24 - Secure macOS Firewall Rule Management
**Vulnerability:** The firewall blocking skill wrote pf rules to an ephemeral `/tmp/nsa_pf_rules.conf` file with default permissions before calling `pfctl -f`. This exposed the system to symlink attacks in the shared `/tmp` directory and caused the active firewall ruleset to be completely flushed and replaced by the single new rule.
**Learning:** Using `pfctl -f` completely replaces active rules, meaning ephemeral temporary files are dangerous because the rest of the system's rules are lost. Furthermore, predictable paths in `/tmp` allow attackers to manipulate the target file or read sensitive network configurations.
**Prevention:** Firewall rules should be managed in a persistent configuration file within a restricted directory (e.g., `memory/nsa_pf_rules.conf`). File creation must use `os.open` with restrictive permissions (`0o600`) and `os.fdopen`, and absolute paths must be used rather than assuming the current working directory.
