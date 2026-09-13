import csv
import importlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path


class LocalUtilsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            importlib.util.find_spec('weather_utils'),
            'The project needs its own utility module',
        )
        self.utils = importlib.import_module('weather_utils')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_json_round_trip(self):
        data = {'place': 'යාපනය', 'rain': 0, 'min_temp': None}
        path = self.root / 'weather.json'
        self.utils.JSONFile(path).write(data)
        self.assertEqual(json.loads(path.read_text()), data)
        self.assertEqual(self.utils.JSONFile(path).read(), data)

    def test_tsv_quoting_and_missing_measurements(self):
        path = self.root / 'weather.tsv'
        self.utils.TSVFile(path).write([
            {'place': 'A\tB', 'rain': 0, 'temperature': None},
            {'place': 'Colombo', 'rain': 1.5, 'temperature': 30},
        ])
        with path.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual(rows[0], {'place': 'A\tB', 'rain': '0', 'temperature': ''})
        self.assertEqual(rows[1]['rain'], '1.5')

    def test_markdown_lines(self):
        path = self.root / 'report.md'
        self.utils.File(path).write_lines(['# Report', '', 'Colombo'])
        self.assertEqual(path.read_text().splitlines(), ['# Report', '', 'Colombo'])

    def test_numeric_parser_preserves_report_conventions(self):
        for value, expected in [('1,234.5', 1234.5), ('-', 0), (' 0 ', 0),
                                ('', None), ('N/A', None), ('TR', None)]:
            with self.subTest(value=value):
                self.assertEqual(self.utils.String(value).float, expected)

    def test_dates_use_sri_lanka_midnight(self):
        day = self.utils.TimeFormat('%Y.%m.%d').parse('2024.02.23')
        expected = datetime(2024, 2, 23, tzinfo=timezone(timedelta(hours=5.5)))
        self.assertEqual(day.ut, expected.timestamp())
        self.assertEqual(self.utils.TimeFormat.DATE.stringify(day), '2024-02-23')
        self.assertEqual(self.utils.TimeFormat.DATE_ID.format(day), '20240223')
        prior = self.utils.Time(day.ut - self.utils.TimeUnit.SECONDS_IN.DAY)
        self.assertEqual(self.utils.TimeFormat.DATE.stringify(prior), '2024-02-22')

    def test_current_time_and_epoch(self):
        self.assertEqual(self.utils.Time(0).ut, 0)
        self.assertLess(abs(self.utils.Time.now().ut - datetime.now().timestamp()), 2)
        datetime.strptime(self.utils.TimeFormat.TIME.formatNow, '%Y-%m-%d %H:%M:%S')

    def test_invalid_date_raises(self):
        with self.assertRaises(ValueError):
            self.utils.TimeFormat.DATE.parse('2024-02-31')

    def test_hash_compatibility(self):
        self.assertEqual(self.utils.Hash.md5('abc'), '900150983cd24fb0d6963f7d28e17f72')

    def test_binary_download(self):
        source = self.root / 'source.pdf'
        target = self.root / 'download.pdf'
        source.write_bytes(b'%PDF-1.7\n\xff\x00\x80')
        self.utils.WWW(source.as_uri()).download_binary(target)
        self.assertEqual(source.read_bytes(), target.read_bytes())

    def test_logging(self):
        with self.assertLogs('local-utils-test', level='WARNING') as captured:
            self.utils.Log('local-utils-test').warning('Missing observation')
        self.assertIn('Missing observation', captured.output[0])

    def test_report_links_default_to_relative_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.utils.public_data_url('charts', 'country_rainfall.png'),
                './charts/country_rainfall.png',
            )

    def test_report_links_accept_configured_public_location(self):
        with patch.dict(os.environ, {'WEATHER_PUBLIC_DATA_URL': 'https://example.invalid/weather/'}):
            self.assertEqual(
                self.utils.public_data_url('flat.json'),
                'https://example.invalid/weather/flat.json',
            )

    def test_report_links_accept_root_relative_location(self):
        with patch.dict(os.environ, {'WEATHER_PUBLIC_DATA_URL': '/'}):
            self.assertEqual(self.utils.public_data_url('flat.json'), '/flat.json')

    def test_clone_and_checkout_in_requested_directory(self):
        source = self.root / 'source'
        destination = self.root / 'destination with spaces'
        def git(*args):
            return subprocess.run(['git', *args], check=True, capture_output=True, text=True)
        git('init', '-b', 'main', str(source))
        (source / 'record.json').write_text('{}')
        git('-C', str(source), 'add', 'record.json')
        git('-C', str(source), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'Fixture')
        git('-C', str(source), 'branch', 'data')
        client = self.utils.Git(str(source))
        client.clone(destination, 'data')
        self.assertEqual(git('-C', str(destination), 'branch', '--show-current').stdout.strip(), 'data')
        client.checkout('main')
        self.assertEqual(git('-C', str(destination), 'branch', '--show-current').stdout.strip(), 'main')
        self.assertTrue((destination / 'record.json').exists())


if __name__ == '__main__':
    unittest.main()
