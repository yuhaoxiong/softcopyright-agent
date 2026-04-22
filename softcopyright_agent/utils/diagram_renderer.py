"""Diagram rendering utilities."""

from __future__ import annotations

import urllib.request
import urllib.error
import os
import time


_TRUTHY = {"1", "true", "yes", "on"}


def remote_diagram_rendering_enabled() -> bool:
    """Return whether Mermaid rendering may call the external Kroki service."""

    return os.getenv("SOFTCOPYRIGHT_ENABLE_REMOTE_DIAGRAMS", "").strip().lower() in _TRUTHY


def render_mermaid_to_png(
    mermaid_text: str,
    timeout_seconds: int = 15,
    *,
    allow_remote: bool | None = None,
) -> bytes:
    """Render a mermaid text block to a PNG image using the Kroki API.

    Args:
        mermaid_text: The source text of the Mermaid diagram.
        timeout_seconds: Request timeout.

    Returns:
        The binary content of the generated PNG image.
    
    Raises:
        RuntimeError: If rendering fails.
    """
    enabled = remote_diagram_rendering_enabled() if allow_remote is None else allow_remote
    if not enabled:
        raise RuntimeError(
            "Remote Mermaid rendering is disabled. "
            "Set SOFTCOPYRIGHT_ENABLE_REMOTE_DIAGRAMS=1 to allow calling Kroki."
        )

    url = "https://kroki.io/mermaid/png"
    data = mermaid_text.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "text/plain")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                return response.read()
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Failed to generate diagram via Kroki after {max_retries} attempts: {exc}") from exc
    raise RuntimeError("Failed to generate diagram via Kroki.")
