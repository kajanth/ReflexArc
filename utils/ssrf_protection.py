import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
import ssl
from urllib.parse import urlparse


def is_safe_ip(ip_str: str) -> bool:
    """Check if an IP string is safe (not private/loopback/etc)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        return True
    except ValueError:
        return False


class SafeHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that mitigates DNS rebinding (TOCTOU)."""
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Host resolution failed for {self.host}")

        if not is_safe_ip(ip_str):
            raise urllib.error.URLError(f"SSRF Protection: Unsafe IP address {ip_str} for host {self.host}")

        self.sock = socket.create_connection((ip_str, self.port), self.timeout)

class SafeHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that mitigates DNS rebinding (TOCTOU)."""
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Host resolution failed for {self.host}")

        if not is_safe_ip(ip_str):
            raise urllib.error.URLError(f"SSRF Protection: Unsafe IP address {ip_str} for host {self.host}")

        sock = socket.create_connection((ip_str, self.port), self.timeout)

        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        # Add SSL context handling similar to standard HTTPSConnection
        server_hostname = self.host if ssl.HAS_SNI else None
        self.sock = self._context.wrap_socket(sock, server_hostname=server_hostname)

class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)

class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(SafeHTTPSConnection, req, context=self._context)

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Custom HTTPRedirectHandler that validates the target URL of any HTTP redirect
    against our SSRF protections before following it.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate the new URL before following the redirect
        if not is_safe_url(newurl):
            raise urllib.error.URLError(f"SSRF Protection: Redirect to unsafe URL blocked: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(url_or_request, timeout=10):
    """
    Safely opens a URL or Request object, preventing SSRF by mitigating
    DNS rebinding via custom connection handlers, and checking subsequent HTTP
    redirects against internal/private IP addresses.
    """
    # Get the initial URL to check
    if isinstance(url_or_request, urllib.request.Request):
        initial_url = url_or_request.full_url
    else:
        initial_url = url_or_request

    # Check the initial URL
    if not is_safe_url(initial_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {initial_url}")

    # Build an opener that uses our custom connection and redirect handlers
    opener = urllib.request.build_opener(
        SafeHTTPHandler(),
        SafeHTTPSHandler(),
        SafeRedirectHandler()
    )
    return opener.open(url_or_request, timeout=timeout)


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

        return is_safe_ip(ip_str)
    except Exception:
        # Fail securely
        return False
