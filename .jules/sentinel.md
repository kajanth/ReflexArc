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

## 2026-03-22 - SSRF Bypass via DNS Rebinding (TOCTOU)
**Vulnerability:** Even when an initial URL's IP address was resolved and checked against internal network blocks, an attacker could bypass the filter using DNS rebinding. By providing a URL that resolves to a safe IP during validation but quickly rebinds to an internal IP (like `127.0.0.1`) right before the actual HTTP request is made, the SSRF protections could be evaded.
**Learning:** Checking a resolved IP string separately from the socket connection creates a Time-Of-Check to Time-Of-Use (TOCTOU) vulnerability because the hostname might resolve to different IPs between the check and the actual use.
**Prevention:** Subclass `http.client.HTTPConnection` and `http.client.HTTPSConnection` to override their `connect` methods. Within the overridden methods, perform `socket.getaddrinfo`, validate the exact IP address, and then establish the connection (`socket.create_connection`) specifically to that validated IP using `sockaddr`. This enforces that the IP validated is the exact IP used for the connection.
