import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
from urllib.parse import urlparse

def _validate_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False
        if ip.is_unspecified:
            return False
        return True
    except Exception:
        return False

class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
            if not _validate_ip(ip_str):
                raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP {ip_str} for {self.host}")
            self.sock = socket.create_connection((ip_str, self.port), self.timeout, self.source_address)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Could not resolve {self.host}")

class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        try:
            ip_str = socket.gethostbyname(self.host)
            if not _validate_ip(ip_str):
                raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP {ip_str} for {self.host}")
            sock = socket.create_connection((ip_str, self.port), self.timeout, self.source_address)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Could not resolve {self.host}")

class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)

class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        # We handle python version differences for _check_hostname gracefully.
        kwargs = {'context': self._context}
        if hasattr(self, '_check_hostname'):
            kwargs['check_hostname'] = self._check_hostname
        return self.do_open(SafeHTTPSConnection, req, **kwargs)

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # We also want to validate the scheme of the redirect
        parsed = urlparse(newurl)
        if parsed.scheme not in ('http', 'https'):
            raise urllib.error.URLError(f"SSRF Protection: Redirect to unsafe scheme blocked: {newurl}")
        # The actual IP validation will happen in SafeHTTPConnection/SafeHTTPSConnection
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def safe_urlopen(url, *args, **kwargs):
    """
    Safely opens a URL or Request object, preventing SSRF and DNS rebinding (TOCTOU).
    It ensures that the IP resolved during DNS resolution is the exact one connected to.
    """
    req_url = url.full_url if isinstance(url, urllib.request.Request) else url

    parsed = urlparse(req_url)
    if parsed.scheme not in ('http', 'https'):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL has unsafe scheme: {req_url}")

    opener = urllib.request.build_opener(
        SafeHTTPHandler(),
        SafeHTTPSHandler(),
        SafeRedirectHandler()
    )
    return opener.open(url, *args, **kwargs)

def is_safe_url(url: str) -> bool:
    """
    Kept for backwards compatibility if used elsewhere, but safe_urlopen is
    the primary defense and doesn't rely on this anymore.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        try:
            ip_str = socket.gethostbyname(hostname)
        except socket.gaierror:
            return False

        return _validate_ip(ip_str)
    except Exception:
        return False
