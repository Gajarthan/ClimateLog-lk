"""Legacy chart-preview switch; explicit opt-in on every operating system."""

import os

TEST_MODE = os.environ.get("WEATHER_TEST_MODE", "0") == "1"
