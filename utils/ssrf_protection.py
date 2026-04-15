import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
import ssl
from urllib.parse import urlparse

class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        try:
            # use getaddrinfo to support ipv4 and ipv6
            addrinfo = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Cannot resolve host: {self.host}")

        err = None
        for res in addrinfo:
            af, socktype, proto, canonname, sa = res
            ip_str = sa[0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                raise urllib.error.URLError(f"SSRF Protection: DNS Rebinding to unsafe IP blocked: {ip_str}")

            try:
                self.sock = socket.create_connection(sa, self.timeout, self.source_address)
                break
            except OSError as _:
                err = _
                if self.sock is not None:
                    self.sock.close()
                    self.sock = None
                continue

        if self.sock is None:
            if err is not None:
                raise err
            else:
                raise urllib.error.URLError("getaddrinfo returns an empty list")

class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        try:
            addrinfo = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        except socket.gaierror:
            raise urllib.error.URLError(f"SSRF Protection: Cannot resolve host: {self.host}")

        err = None
        for res in addrinfo:
            af, socktype, proto, canonname, sa = res
            ip_str = sa[0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                raise urllib.error.URLError(f"SSRF Protection: DNS Rebinding to unsafe IP blocked: {ip_str}")

            try:
                self.sock = socket.create_connection(sa, self.timeout, self.source_address)
                break
            except OSError as _:
                err = _
                if self.sock is not None:
                    self.sock.close()
                    self.sock = None
                continue

        if self.sock is None:
            if err is not None:
                raise err
            else:
                raise urllib.error.URLError("getaddrinfo returns an empty list")

        if self._tunnel_host:
            self._tunnel()

        server_hostname = self._tunnel_host or self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)

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
    Safely opens a URL or Request object, preventing SSRF by checking both the initial URL
    and any subsequent HTTP redirects against internal/private IP addresses.
    """
    # Get the initial URL to check
    if isinstance(url_or_request, urllib.request.Request):
        initial_url = url_or_request.full_url
    else:
        initial_url = url_or_request

    # Check the initial URL
    if not is_safe_url(initial_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {initial_url}")

    # Build an opener that uses our custom handlers for DNS rebinding & redirects
    opener = urllib.request.build_opener(SafeHTTPHandler(), SafeHTTPSHandler(), SafeRedirectHandler())
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

