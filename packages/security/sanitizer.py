from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Prompt injection signatures to detect and neutralize
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|unrestricted)", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*(override|reset|leak)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|admin|eval|exec|override)\s*>", re.IGNORECASE),
    re.compile(r"\[\s*(system|instruction|developer|jailbreak)\s*\]", re.IGNORECASE),
]

# Control character pattern (strip non-printable characters except \n, \r, \t)
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def sanitize_prompt_input(text: str, max_length: int = 4000) -> str:
    """Sanitize user-provided text for LLM prompts to mitigate prompt injection.

    - Truncates to max_length
    - Removes non-printable control characters and null bytes
    - Detects and neutralizes prompt override / jailbreak patterns
    """
    if not text:
        return ""

    if len(text) > max_length:
        text = text[:max_length]

    # Remove dangerous control chars
    clean_text = CONTROL_CHAR_PATTERN.sub("", text)

    # Check for prompt injection patterns and neutralize if found
    for pattern in INJECTION_PATTERNS:
        if pattern.search(clean_text):
            logger.warning("Prompt injection pattern detected and neutralized: %s", pattern.pattern)
            clean_text = pattern.sub("[REDACTED_PROMPT_INJECTION_PATTERN]", clean_text)

    return clean_text.strip()


def validate_safe_url(url: str, allow_private: bool = False) -> str:
    """Validate that a URL is safe to fetch and does not target internal or private networks (SSRF prevention).

    - Enforces http/https schemes
    - Blocks loopback, link-local, private IP ranges (RFC 1918, RFC 4193)
    - Blocks cloud metadata endpoints (169.254.169.254)
    - Validates DNS resolution
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme: '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    # Explicit blocked hostnames
    lowered_host = hostname.lower()
    if lowered_host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"):
        raise ValueError(f"Access to host '{hostname}' is prohibited (SSRF prevention).")

    if lowered_host.endswith((".local", ".internal", ".localhost", ".corp")):
        raise ValueError(f"Access to private internal domain '{hostname}' is prohibited.")

    if not allow_private:
        # Check if hostname is directly an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(
                    f"Access to private or local IP '{hostname}' is prohibited (SSRF prevention)."
                )
        except ValueError as err:
            # If not a literal IP, resolve through DNS
            if "prohibited" in str(err):
                raise
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for addr in addr_info:
                    ip_str = addr[4][0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    if (
                        resolved_ip.is_private
                        or resolved_ip.is_loopback
                        or resolved_ip.is_link_local
                        or resolved_ip.is_reserved
                    ):
                        raise ValueError(
                            f"Hostname '{hostname}' resolves to prohibited IP address '{resolved_ip}' (SSRF prevention)."
                        )
            except socket.gaierror:
                # If DNS resolution fails, allow if not private hostname; network call will fail gracefully later
                pass

    return url.strip()
