"""Executable entry point for the Web Redesign Client Scout application.

This module bootstraps Streamlit directly so it can be bundled into a
stand-alone executable via PyInstaller without relying on the ``streamlit``
command being available on the target machine.
"""

from pathlib import Path
from streamlit.web import bootstrap


def main() -> None:
    script_path = Path(__file__).with_name("web_redesign_client_scout.py")
    if not script_path.exists():
        raise FileNotFoundError(f"Unable to locate Streamlit app at {script_path!s}")

    flag_options = {"server.headless": False}
    bootstrap.run(str(script_path), "", [], flag_options)


if __name__ == "__main__":
    main()
