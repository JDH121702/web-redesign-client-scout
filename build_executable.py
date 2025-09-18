"""Utility script to bundle the Streamlit app into a Windows executable.

Run this script after installing PyInstaller to produce a distributable EXE::

    python build_executable.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from importlib.metadata import PackageNotFoundError, version as _importlib_version
except ModuleNotFoundError:  # pragma: no cover - Python < 3.8 fallback
    from pkg_resources import DistributionNotFound as PackageNotFoundError  # type: ignore
    from pkg_resources import get_distribution  # type: ignore

    def _get_distribution_version(distribution: str) -> str:
        return get_distribution(distribution).version
else:
    def _get_distribution_version(distribution: str) -> str:
        return _importlib_version(distribution)


try:
    import PyInstaller.__main__  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - convenience guard
    raise SystemExit(
        "PyInstaller is required to build the executable. Install it via 'pip install pyinstaller'."
    ) from exc


def _supports_modern_collection(pyinstaller_version: str) -> bool:
    """Return ``True`` when the installed PyInstaller supports collection flags."""

    match = re.match(r"(\d+)", pyinstaller_version)
    if not match:
        return False
    return int(match.group(1)) >= 5


def build(pyinstaller_version_override: str | None = None) -> None:
    project_root = Path(__file__).parent
    asset_files = {
        "styles.css": project_root / "styles.css",
        "web_redesign_client_scout.py": project_root / "web_redesign_client_scout.py",
    }

    missing_assets = [name for name, path in asset_files.items() if not path.exists()]
    if missing_assets:
        missing_assets_str = ", ".join(missing_assets)
        raise FileNotFoundError(f"Expected asset file(s) missing: {missing_assets_str}")

    if pyinstaller_version_override is not None:
        pyinstaller_version = pyinstaller_version_override
    else:
        try:
            pyinstaller_version = _get_distribution_version("pyinstaller")
        except PackageNotFoundError as exc:  # pragma: no cover - should not happen after import
            raise SystemExit(
                "Unable to determine the installed PyInstaller version. "
                "Reinstall the package and try again."
            ) from exc

    use_modern_collection = _supports_modern_collection(pyinstaller_version)

    dist_dir = project_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    output_path = dist_dir / "WebRedesignClientScout.exe"
    if output_path.exists():
        try:
            output_path.unlink()
        except PermissionError as exc:
            raise SystemExit(
                "Unable to overwrite the existing executable at "
                f"{output_path.resolve()}.\n"
                "Close any running instances of WebRedesignClientScout.exe "
                "and run the build again."
            ) from exc

    pyinstaller_args = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name",
        "WebRedesignClientScout",
        "--hidden-import",
        "streamlit.web.bootstrap",
    ]

    for asset_path in asset_files.values():
        pyinstaller_args.extend(["--add-data", f"{asset_path}{os.pathsep}."])

    if use_modern_collection:
        pyinstaller_args.extend(
            [
                "--copy-metadata",
                "streamlit",
                "--collect-data",
                "streamlit",
            ]
        )
    else:
        from PyInstaller.utils import hooks as pyinstaller_hooks  # type: ignore

        streamlit_data_files = list(pyinstaller_hooks.collect_data_files("streamlit"))

        copy_metadata = getattr(pyinstaller_hooks, "copy_metadata", None)
        if callable(copy_metadata):
            streamlit_data_files.extend(copy_metadata("streamlit"))

        for src, dest in streamlit_data_files:
            pyinstaller_args.extend(["--add-data", f"{src}{os.pathsep}{dest}"])

    pyinstaller_args.append(str(project_root / "run_app.py"))

    PyInstaller.__main__.run(pyinstaller_args)


if __name__ == "__main__":
    build()
