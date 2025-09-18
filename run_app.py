"""Executable entry point for the Web Redesign Client Scout application.

This module bootstraps Streamlit directly so it can be bundled into a
stand-alone executable via PyInstaller without relying on the ``streamlit``
command being available on the target machine.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import importlib.metadata as importlib_metadata


def _ensure_streamlit_metadata() -> None:
    """Provide minimal metadata for Streamlit when bundled.

    PyInstaller does not automatically include the ``dist-info`` metadata that
    :mod:`streamlit` expects during import. When the metadata is missing the
    application would otherwise crash at startup. To make the bundled
    executable resilient we lazily patch :func:`importlib.metadata.version` and
    :func:`importlib.metadata.distribution` to return a synthetic distribution
    containing just the information Streamlit needs.
    """

    try:
        importlib_metadata.version("streamlit")
    except importlib_metadata.PackageNotFoundError:
        fallback_version = os.environ.get("STREAMLIT_VERSION_OVERRIDE", "0.0+bundle")
        original_version: Callable[[str], str] = importlib_metadata.version
        original_distribution = importlib_metadata.distribution

        import importlib.util

        streamlit_spec = importlib.util.find_spec("streamlit")
        if streamlit_spec is not None and streamlit_spec.origin is not None:
            streamlit_package_root = Path(streamlit_spec.origin).resolve().parent
        else:
            streamlit_package_root = Path(__file__).resolve().parent

        class _StreamlitDistribution(importlib_metadata.Distribution):
            """Minimal distribution object used as a fallback."""

            def __init__(self, version: str, base_path: Path) -> None:
                self._version = version
                self._base_path = base_path

            def read_text(self, filename: str):  # type: ignore[override]
                if filename in {"METADATA", "PKG-INFO", ""}:
                    return f"Name: streamlit\nVersion: {self._version}\n"
                return None

            def locate_file(self, path):  # type: ignore[override]
                from os import fspath

                resolved_path = Path(fspath(path))
                if resolved_path.is_absolute():
                    return resolved_path
                return self._base_path / resolved_path

        def _patched_version(name: str) -> str:
            if name == "streamlit":
                return fallback_version
            return original_version(name)

        def _patched_distribution(name: str):
            if name == "streamlit":
                return _StreamlitDistribution(fallback_version, streamlit_package_root)
            return original_distribution(name)

        importlib_metadata.version = _patched_version  # type: ignore[assignment]
        importlib_metadata.distribution = _patched_distribution  # type: ignore[assignment]


_ensure_streamlit_metadata()
from streamlit.web import bootstrap


def main() -> None:
    script_path = Path(__file__).with_name("web_redesign_client_scout.py")
    if not script_path.exists():
        raise FileNotFoundError(f"Unable to locate Streamlit app at {script_path!s}")

    flag_options = {
        "server.headless": False,
        "global.developmentMode": False,
        "server.port": 3000,
        "server.address": "127.0.0.1",
    }
    bootstrap.run(str(script_path), "", [], flag_options)


if __name__ == "__main__":
    main()
