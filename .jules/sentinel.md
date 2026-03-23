## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.

## 2024-03-24 - SSRF Bypass via HTTP Redirects
**Vulnerability:** Initial SSRF protections were bypassed because `urllib.request.urlopen` automatically follows HTTP redirects without validating the target URL of the redirect. An attacker could provide a safe URL that redirects to a restricted internal IP.
**Learning:** Standard URL validation prior to the request is insufficient when the HTTP client auto-follows redirects.
**Prevention:** Implement a custom `urllib.request.HTTPRedirectHandler` to intercept and validate the `newurl` against internal IP restrictions on every redirect before following it. Always use `safe_urlopen` which uses this custom handler instead of directly using `urllib.request.urlopen`.
