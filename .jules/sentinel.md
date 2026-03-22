## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.

## 2026-03-22 - SSRF Redirect Bypass
**Vulnerability:** Initial SSRF protections via `is_safe_url` only validated the target URL but failed to handle subsequent HTTP redirects. An attacker could bypass the filter by supplying a safe URL that redirects to a restricted local IP (e.g., `127.0.0.1`).
**Learning:** Checking a URL before making a request is insufficient if the HTTP client automatically follows redirects without reapplying the same security checks to the new location.
**Prevention:** Implement a custom `HTTPRedirectHandler` that runs the `is_safe_url` checks on the `newurl` during every redirect before continuing the request, and use this handler to perform all outbound HTTP requests.
