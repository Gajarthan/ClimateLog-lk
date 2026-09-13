"""Manual compatibility entry point; PDF regression tests live in integration/."""

if __name__ == "__main__":
    from weather_lk.cli import main
    raise SystemExit(main(["ingest", "--file", "tests/data/20240223.pdf"]))
