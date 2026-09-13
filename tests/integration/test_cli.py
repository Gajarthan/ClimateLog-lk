import json
import os
import subprocess
import sys
from pathlib import Path


def invoke(tmp_path, *arguments):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "weather_lk",
            "--data-dir",
            str(tmp_path / "data"),
            *arguments,
        ],
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        },
        capture_output=True,
        text=True,
    )


def test_status_does_not_initialize_storage(tmp_path):
    result = invoke(tmp_path, "status")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["initialized"] is False
    assert not (tmp_path / "data").exists()


def test_initialize_and_export_empty_data(tmp_path):
    result = invoke(tmp_path, "init")
    assert result.returncode == 0, result.stderr
    exported = invoke(tmp_path, "export", "--no-charts")
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)["records"] == 0


def test_invalid_configuration_has_nonzero_exit(tmp_path):
    result = invoke(tmp_path, "ingest", "--source", "invalid")
    assert result.returncode != 0
