import os
import subprocess
import sys
from pathlib import Path


def test_package_import_does_not_load_optional_dependencies(tmp_path):
    source = str(Path(__file__).resolve().parents[2] / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import weather_lk; assert not any(x in sys.modules for x in ('camelot', 'selenium', 'matplotlib', 'googlemaps')); print(weather_lk.__version__)",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": source, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())
