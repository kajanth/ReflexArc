import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
from urllib.parse import urlparse

def is_safe_ip(ip_str: str) -> bool:
    """
    Check if an IP address is safe to connect to.
    Protects against Server-Side Request Forgery (SSRF) by validating
    that the resolved IP address is not in a private, loopback, link-local,
    multicast, or unspecified range.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        return True
    except Exception:
        # Fail securely
        return False

class SafeHTTPConnection(http.client.HTTPConnection):
    """
    Custom HTTPConnection that resolves the host using getaddrinfo,
    validates the IP, and connects specifically to the validated IP to prevent TOCTOU.
    """
    def connect(self):
        self.sock = None
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            ip = sa[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP: {ip}")

            try:
                self.sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
                break
            except socket.error:
                continue
        if not self.sock:
            raise socket.error("getaddrinfo returns an empty list")

class SafeHTTPSConnection(http.client.HTTPSConnection):
    """
    Custom HTTPSConnection that resolves the host using getaddrinfo,
    validates the IP, connects specifically to the validated IP, and wraps it in SSL.
    """
    def connect(self):
        self.sock = None
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            ip = sa[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Blocked unsafe IP: {ip}")

            try:
                self.sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
                break
            except socket.error:
                continue
        if not self.sock:
            raise socket.error("getaddrinfo returns an empty list")

        server_hostname = self._tunnel_host or self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)

class SafeHTTPHandler(urllib.request.HTTPHandler):
    """Custom HTTPHandler that uses SafeHTTPConnection."""
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)

class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    """Custom HTTPSHandler that uses SafeHTTPSConnection."""
    def https_open(self, req):
        return self.do_open(SafeHTTPSConnection, req, context=self._context)

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Custom HTTPRedirectHandler that validates the target URL of any HTTP redirect
    against our SSRF protections before following it.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate the new URL scheme before following the redirect
        parsed = urlparse(newurl)
        if parsed.scheme not in ('http', 'https'):
            raise urllib.error.URLError(f"SSRF Protection: Redirect to unsafe scheme blocked: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def safe_urlopen(url_or_request, timeout=10):
    """
    Safely opens a URL or Request object, preventing SSRF by checking both the initial URL
    and any subsequent HTTP redirects against internal/private IP addresses, and preventing
    TOCTOU / DNS Rebinding attacks by enforcing IP validation at the socket connection level.
    """
    # Get the initial URL to check
    if isinstance(url_or_request, urllib.request.Request):
        initial_url = url_or_request.full_url
    else:
        initial_url = url_or_request

    parsed = urlparse(initial_url)
    if parsed.scheme not in ('http', 'https'):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL has unsafe scheme: {initial_url}")

    # Build an opener that uses our custom handlers
    opener = urllib.request.build_opener(SafeHTTPHandler(), SafeHTTPSHandler(), SafeRedirectHandler())
    return opener.open(url_or_request, timeout=timeout)

def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to make an outbound request to.
    Protects against Server-Side Request Forgery (SSRF) by validating
    that the scheme is http/https and the resolved IP address is not
    in a private, loopback, link-local, or multicast range.
    Note: For complete protection, safe_urlopen should be used, which handles TOCTOU.
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
