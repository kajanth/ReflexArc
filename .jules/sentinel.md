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
## 2026-05-09 - SSRF TOCTOU / DNS Rebinding Vulnerability
**Vulnerability:** Even with `is_safe_url` and redirect checking, the application was vulnerable to DNS Rebinding attacks (Time-of-Check to Time-of-Use). An attacker could configure a DNS server to return a safe IP during the `is_safe_url` check, and then return a restricted IP (e.g. `127.0.0.1`) microseconds later when `urllib` actually connects.
**Learning:** URL validation based on DNS resolution is fundamentally flawed unless the exact resolved IP used for validation is also used for the connection. Standard HTTP libraries often resolve DNS again when opening the socket.
**Prevention:** Subclass `http.client.HTTPConnection` and `HTTPSConnection` to override `connect()`. Resolve DNS via `socket.getaddrinfo`, validate the specific IP, and immediately connect to that IP (`socket.create_connection((ip, port))`) to eliminate the TOCTOU race condition. Use `SafeHTTPHandler` and `SafeHTTPSHandler` in `urllib.request` to inject these connection subclasses.
