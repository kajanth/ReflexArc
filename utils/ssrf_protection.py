import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
import ssl
from urllib.parse import urlparse

def _validate_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        return True
    except ValueError:
        return False

class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
        except socket.gaierror as e:
            raise urllib.error.URLError(f"SSRF Protection: DNS resolution failed for {self.host}") from e

        if not _validate_ip(ip_str):
            raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP {ip_str} for host {self.host}")

        self.sock = socket.create_connection((ip_str, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()

class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
        except socket.gaierror as e:
            raise urllib.error.URLError(f"SSRF Protection: DNS resolution failed for {self.host}") from e

        if not _validate_ip(ip_str):
            raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP {ip_str} for host {self.host}")

        sock = socket.create_connection((ip_str, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

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

        return _validate_ip(ip_str)
    except Exception:
        # Fail securely
        return False


def safe_urlopen(url_or_request, timeout=10, *args, **kwargs):
    """
    Drop-in replacement for urllib.request.urlopen that enforces SSRF
    protections on both the initial URL and any subsequent redirects,
    as well as mitigating DNS rebinding attacks (TOCTOU) by resolving
    and connecting to the verified IP directly.
    """
    req_url = url_or_request.full_url if isinstance(url_or_request, urllib.request.Request) else url_or_request
    if not is_safe_url(req_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {req_url}")

    opener = urllib.request.build_opener(
        SafeHTTPHandler(),
        SafeHTTPSHandler(),
        SafeRedirectHandler()
    )

    # Also pass through args/kwargs to be fully compatible with urlopen signature.
    # timeout needs to be handled separately as we've defined it as a named arg.
    if 'timeout' not in kwargs:
        kwargs['timeout'] = timeout

    return opener.open(url_or_request, *args, **kwargs)
