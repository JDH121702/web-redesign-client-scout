"""Utility script to bundle the Streamlit app into a Windows executable.

Run this script after installing PyInstaller to produce a distributable EXE::

    python build_executable.py
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import PyInstaller.__main__  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - convenience guard
    raise SystemExit(
        "PyInstaller is required to build the executable. Install it via 'pip install pyinstaller'."
    ) from exc


def build() -> None:
    project_root = Path(__file__).parent
    css_file = project_root / "styles.css"
    if not css_file.exists():
        raise FileNotFoundError(f"Expected CSS file at {css_file!s}")

    add_data_arg = f"{css_file}{os.pathsep}."

    PyInstaller.__main__.run(
        [
            "--noconfirm",
            "--clean",
            "--onefile",
            "--noconsole",
            "--name",
            "WebRedesignClientScout",
            "--add-data",
            add_data_arg,
            "--hidden-import",
            "streamlit.web.bootstrap",
            str(project_root / "run_app.py"),
        ]
    )


if __name__ == "__main__":
    build()
