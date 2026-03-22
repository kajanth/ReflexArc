import ipaddress
import socket
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

import urllib.request
import urllib.error

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_url(newurl):
            raise urllib.error.URLError(f"Blocked unsafe redirect to {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def safe_urlopen(url, *args, **kwargs):
    """
    Drop-in replacement for urllib.request.urlopen that enforces SSRF
    protections on both the initial URL and any subsequent redirects.
    """
    req_url = url.full_url if isinstance(url, urllib.request.Request) else url
    if not is_safe_url(req_url):
        raise urllib.error.URLError(f"Blocked unsafe URL: {req_url}")

    opener = urllib.request.build_opener(SafeRedirectHandler())
    return opener.open(url, *args, **kwargs)
