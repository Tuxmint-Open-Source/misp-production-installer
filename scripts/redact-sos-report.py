#!/usr/bin/env python3
"""Public-safe redaction helper for MISP Docker Lifecycle Manager SOS reports."""
from __future__ import annotations

import re
import sys
from urllib.parse import urlsplit, urlunsplit


def redact_text(text: str, install_dir: str = "") -> str:
    """Redact deployment-sensitive values from public SOS report text.

    This helper intentionally over-redacts. A less detailed public report is
    preferable to leaking deployment identifiers or credentials.
    """

    secret_key = re.compile(
        r"(?i)\b([A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY|AUTH|CREDENTIAL)[A-Z0-9_]*)\s*[:=]\s*([^\s,;]+)"
    )
    text = secret_key.sub(lambda m: f"{m.group(1)}=[REDACTED_SECRET]", text)

    def repl_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            parts = urlsplit(raw)
        except Exception:
            return "[REDACTED_URL]"
        if not parts.scheme:
            return "[REDACTED_URL]"
        return urlunsplit((parts.scheme, "[REDACTED_HOST]", "", "", ""))

    text = re.sub(r"https?://[^\s)\]>\"']+", repl_url, text)
    text = re.sub(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[REDACTED_EMAIL]",
        text,
    )
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]", text)
    text = re.sub(r"\b(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F]{0,4}\b", "[REDACTED_IP]", text)

    def repl_host(match: re.Match[str]) -> str:
        host = match.group(0)
        if host.endswith(".example.com") or host == "example.com":
            return host
        return "[REDACTED_HOST]"

    text = re.sub(
        r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:local|internal|lan|home|corp|com|net|org|io|dev|ch|de|li)\b",
        repl_host,
        text,
    )
    text = re.sub(r"/(?:home|Users)/[^\s/]+(?:/[^\s]*)?", "[REDACTED_PATH]", text)
    text = re.sub(r"/root(?:/[^\s]*)?", "[REDACTED_PATH]", text)
    if install_dir and install_dir != "/opt/misp-docker":
        text = text.replace(install_dir, "[REDACTED_PATH]")
    text = re.sub(r"\b[0-9a-fA-F]{32,}\b", "[REDACTED_ID]", text)
    return text


def main() -> int:
    install_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.stdout.write(redact_text(sys.stdin.read(), install_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
