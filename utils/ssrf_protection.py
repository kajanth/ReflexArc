import ipaddress
import socket
import urllib.request
import urllib.error
import http.client
import ssl
from urllib.parse import urlparse


def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        return True
    except ValueError:
        return False


class SafeHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            ip = sa[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Resolved IP {ip} is not safe")
            try:
                self.sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
                break
            except socket.error:
                continue
        else:
            raise socket.error("getaddrinfo returns an empty list or failed to connect")


class SafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            ip = sa[0]
            if not is_safe_ip(ip):
                raise urllib.error.URLError(f"SSRF Protection: Resolved IP {ip} is not safe")
            try:
                self.sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)
                server_hostname = getattr(self, '_tunnel_host', None) or self.host
                self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)
                break
            except socket.error:
                continue
        else:
            raise socket.error("getaddrinfo returns an empty list or failed to connect")


class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)


class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        context = getattr(self, '_context', None)
        if context is None:
            context = ssl.create_default_context()
        return self.do_open(SafeHTTPSConnection, req, context=context)


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


def safe_urlopen(url, *args, **kwargs):
    """
    Drop-in replacement for urllib.request.urlopen that enforces SSRF
    protections on both the initial URL and any subsequent redirects.
    """
    req_url = url.full_url if isinstance(url, urllib.request.Request) else url
    if not is_safe_url(req_url):
        raise urllib.error.URLError(f"SSRF Protection: Initial URL is unsafe: {req_url}")

    # Build an opener that uses our custom handlers
    opener = urllib.request.build_opener(
        SafeHTTPHandler(),
        SafeHTTPSHandler(),
        SafeRedirectHandler()
    )
    return opener.open(url, *args, **kwargs)


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

        # Resolve the hostname to IP addresses
        try:
            for res in socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM):
                ip_str = res[4][0]
                if not is_safe_ip(ip_str):
                    return False
        except socket.gaierror:
            # If we can't resolve the host, it's not safe to connect
            return False

        return True
    except Exception:
        # Fail securely
        return False
