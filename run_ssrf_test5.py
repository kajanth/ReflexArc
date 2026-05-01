import urllib.request
import urllib.error

# This tries to fetch a local resource to demonstrate TOCTOU in SSRF
# We would need a custom opener to override the connection behavior to test full mitigation.

# To be clear, is_safe_url prevents a URL that resolves to a local IP at the time of the check.
# But `urllib.request.urlopen` will do its OWN DNS resolution when actually connecting.
# This opens the door to DNS Rebinding attacks.
