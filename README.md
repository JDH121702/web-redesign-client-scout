# Web Redesign Client Scout

Web Redesign Client Scout is now distributed as a native console application
written in C with a Python analysis engine. The frontend presents a focused
command-line experience while the Python module handles live website heuristics
and scoring.

## Architecture

- **`frontend.c`** – menu-driven C application that embeds the CPython runtime
  and renders the analysis results.
- **`analysis_engine.py`** – pure Python module that performs the
  network request, HTML parsing, and scoring heuristics.
- **`analysis_cli.py`** – optional helper that exposes the analysis from the
  command line and powers automation or scripting workflows.

The legacy Streamlit interface is still available in
`web_redesign_client_scout.py` for reference but is no longer used when
building the standalone application.

## Prerequisites

- Python 3.11 or newer with the development headers installed
- `python3-config` available on the PATH (ships with CPython)
- A C compiler such as `gcc` or `clang`

The Python dependencies used by the analysis engine are listed in
`requirements.txt`.

## Building the C frontend

A `Makefile` is included for convenience:

```bash
make scout_frontend
```

The Makefile automatically queries `python3-config` for the correct compiler
flags. On platforms where `python3-config --embed` is not available, it falls
back to the standard linker flags.

To clean the build artifacts:

```bash
make clean
```

If you prefer invoking the compiler manually, the command typically looks like:

```bash
gcc frontend.c -o scout_frontend $(python3-config --embed --cflags --ldflags)
```

On some distributions the `--embed` flag is not present; omit it in that case.

## Running the application

After building, launch the CLI frontend:

```bash
./scout_frontend
```

The menu will prompt for a URL, execute the Python analysis, and print the
metrics, narrative summary, and supporting talking points directly to the
terminal. Errors from the analysis module are surfaced in a friendly format.

## Using the Python analysis directly

You can call the analysis engine without compiling the C frontend via the
helper CLI:

```bash
python analysis_cli.py https://example.com
```

Add `--json` to receive machine-readable output suitable for piping into other
tools.

## Development tips

- `analysis_engine.py` contains the heuristics and can be extended with new
  scoring rules without touching the C code.
- The C frontend embeds Python once and reuses the interpreter across analyses,
  so repeated scans are fast.
- When modifying the analysis logic, unit tests can target the Python module
directly. The CLI and frontend simply display the returned structure.

## License

MIT
