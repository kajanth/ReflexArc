import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
from urllib.parse import urlparse

def _check_ip(ip_str):
    ip = ipaddress.ip_address(ip_str)
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        raise urllib.error.URLError(f"SSRF Protection: Blocked IP {ip_str}")

class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        err = None
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                ip_str = sa[0]
                _check_ip(ip_str)
            except Exception as e:
                err = e
                continue
            try:
                self.sock = socket.socket(af, socktype, proto)
                if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    self.sock.settimeout(self.timeout)
                if self.source_address:
                    self.sock.bind(self.source_address)
                self.sock.connect(sa)

                if self._tunnel_host:
                    self._tunnel()
                return
            except OSError as e:
                err = e
                if self.sock is not None:
                    self.sock.close()
                    self.sock = None

        if err is not None:
            raise urllib.error.URLError(f"Failed to connect to {self.host}: {err}")
        else:
            raise urllib.error.URLError(f"Failed to resolve {self.host}")

class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        err = None
        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                ip_str = sa[0]
                _check_ip(ip_str)
            except Exception as e:
                err = e
                continue
            try:
                sock = socket.socket(af, socktype, proto)
                if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(self.timeout)
                if self.source_address:
                    sock.bind(self.source_address)
                sock.connect(sa)

                self.sock = sock
                if self._tunnel_host:
                    self._tunnel()

                server_hostname = self.host if not self._tunnel_host else self._tunnel_host
                self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)
                return
            except OSError as e:
                err = e
                if sock is not None:
                    sock.close()

        if err is not None:
            raise urllib.error.URLError(f"Failed to connect to {self.host}: {err}")
        else:
            raise urllib.error.URLError(f"Failed to resolve {self.host}")

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

def safe_urlopen(url_or_request, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, *, cafile=None, capath=None, cadefault=False, context=None):
    """
    Safely opens a URL or Request object, preventing SSRF by checking both the initial URL
    and any subsequent HTTP redirects against internal/private IP addresses.
    It protects against DNS rebinding (TOCTOU) by resolving IP at connection time.
    """
    # Get the initial URL to check
    if isinstance(url_or_request, urllib.request.Request):
        initial_url = url_or_request.full_url
    else:
        initial_url = url_or_request

    # Check the initial URL
    if not is_safe_url(initial_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {initial_url}")

    # Build an opener that uses our custom redirect and connection handlers
    opener = urllib.request.build_opener(SafeHTTPHandler(), SafeHTTPSHandler(), SafeRedirectHandler())

    return opener.open(url_or_request, data=data, timeout=timeout)
