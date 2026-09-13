"""Compatibility entry point for the weather pipeline CLI."""

from weather_lk.cli import main

if __name__ == "__main__":
    raise SystemExit(main(['export']))
