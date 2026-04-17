import ipaddress
import socket
import urllib.request
import urllib.error
from urllib.parse import urlparse
import http.client
import ssl


def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        return True
    except Exception:
        return False


class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        addrinfo = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        for family, type, proto, canonname, sockaddr in addrinfo:
            ip = sockaddr[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Resolved IP {ip} is not safe.")
            try:
                self.sock = socket.create_connection(sockaddr, self.timeout, self.source_address)
                break
            except socket.error:
                continue
        else:
            raise urllib.error.URLError(f"SSRF Protection: Could not connect to any safe IPs for {self.host}")


class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        addrinfo = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        for family, type, proto, canonname, sockaddr in addrinfo:
            ip = sockaddr[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Resolved IP {ip} is not safe.")
            try:
                self.sock = socket.create_connection(sockaddr, self.timeout, self.source_address)
                break
            except socket.error:
                continue
        else:
            raise urllib.error.URLError(f"SSRF Protection: Could not connect to any safe IPs for {self.host}")

        if self._tunnel_host:
            self.sock = self.sock
            self._tunnel()

        server_hostname = self._tunnel_host or self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)


class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)


class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(SafeHTTPSConnection, req, context=self._context, check_hostname=self._check_hostname)


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
    Safely opens a URL or Request object, preventing SSRF by checking both the initial URL
    and any subsequent HTTP redirects against internal/private IP addresses.
    It also mitigates DNS rebinding attacks by verifying the actual IP used to connect.
    """
    # Get the initial URL to check
    if isinstance(url_or_request, urllib.request.Request):
        initial_url = url_or_request.full_url
    else:
        initial_url = url_or_request

    # Check the initial URL
    if not is_safe_url(initial_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {initial_url}")

    # Build an opener that uses our custom connection handlers and redirect handler
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
