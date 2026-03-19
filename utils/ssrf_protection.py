import ipaddress
import socket
import urllib.request
import urllib.error
from urllib.parse import urlparse


def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to make an outbound request to.
    Protects against Server-Side Request Forgery (SSRF) by validating
    that the scheme is http/https and the resolved IP address is not
    in a private, loopback, link-local, or multicast range.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve the hostname to an IP address
        try:
            ip_str = socket.gethostbyname(hostname)
        except socket.gaierror:
            # If we can't resolve the host, it's not safe to connect
            return False

        ip = ipaddress.ip_address(ip_str)

        # Check if the IP address is in a restricted range
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False

        # specifically check 0.0.0.0 (unspecified)
        if ip.is_unspecified:
            return False

        return True
    except Exception:
        # Fail securely
        return False


class SSRFProtectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    A custom redirect handler that verifies the safety of the target URL
    before allowing the redirect to proceed. This prevents SSRF attacks
    where an attacker provides a safe URL that redirects to a malicious
    internal IP address.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_url(newurl):
            raise urllib.error.URLError(f"Blocked redirect to unsafe URL (SSRF protection): {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(url, *args, **kwargs):
    """
    A wrapper around urllib.request.urlopen that uses a custom opener
    with SSRF protection for redirects.
    """
    opener = urllib.request.build_opener(SSRFProtectRedirectHandler())
    return opener.open(url, *args, **kwargs)
