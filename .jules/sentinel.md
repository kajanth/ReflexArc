## 2024-03-24 - Prevent Server-Side Request Forgery
**Vulnerability:** API caller and alert notification skills make external HTTP requests using user-supplied URLs without verifying their destination. This could allow an attacker to send requests to local networks, such as `127.0.0.1` or the `169.254.169.254` AWS metadata service.
**Learning:** Security fixes must be mindful of `urllib.request` which follows redirects automatically and does not implement internal security checks.
**Prevention:** Implement an `is_safe_url` validation utility that parses URLs and uses `socket.gethostbyname` combined with `ipaddress` validation. Restrict IP addresses from belonging to `.is_private`, `.is_loopback`, `.is_link_local`, or `.is_multicast`. Reject dangerous schemes such as `ftp://` or `file://`.

## 2024-05-23 - Prevent Unhandled 500 Errors from Invalid Query Parameters
**Vulnerability:** API endpoints relying on integer type conversion (`int()`) for query parameters like `limit` lack explicit error handling, resulting in 500 Internal Server Errors or potential application restarts/crashes when non-numeric strings are provided by users or attackers.
**Learning:** Raw parsing of client inputs without type validation allows malicious inputs to trigger unhandled exceptions that propagate to the server's top level, failing securely but exposing weak error handling and potentially leading to denial of service or stack trace exposure.
**Prevention:** Always wrap integer casting (`int()`) or other type conversions of untrusted user input (e.g., query parameters, form data) in a `try...except ValueError` block to gracefully handle invalid inputs and return appropriate HTTP 400 Bad Request responses.
