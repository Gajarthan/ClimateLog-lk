"""Local standard-library helpers for the weather pipeline."""

import csv
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen


def public_data_url(*parts):
    base = os.environ.get('WEATHER_PUBLIC_DATA_URL', '.').strip() or '.'
    return '/'.join([base.rstrip('/'), *(part.strip('/') for part in parts)])


def Log(name):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
    return logging.getLogger(name)


class File:
    def __init__(self, path):
        self.path = Path(path)

    def write_lines(self, lines):
        self.path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


class JSONFile(File):
    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def write(self, data):
        self.path.write_text(json.dumps(data, indent=2), encoding='utf-8')


class TSVFile(File):
    def write(self, rows):
        with self.path.open('w', encoding='utf-8', newline='') as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter='\t')
                writer.writeheader()
                writer.writerows(rows)


class String:
    def __init__(self, value):
        self.value = value

    @property
    def float(self):
        # Preserve the existing report parser's comma and dash conventions.
        number = self.value.replace(',', '').replace('-', '0')
        try:
            return float(number)
        except ValueError:
            return None


class Time:
    def __init__(self, ut=None):
        self.ut = time.time() if ut is None else ut

    @staticmethod
    def now():
        return Time()


class TimeFormat:
    LOCAL_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

    def __init__(self, format_str):
        self.format_str = format_str

    def parse(self, value):
        local = datetime.strptime(value, self.format_str).replace(tzinfo=self.LOCAL_TIMEZONE)
        return Time(local.timestamp())

    def stringify(self, value):
        return datetime.fromtimestamp(value.ut, self.LOCAL_TIMEZONE).strftime(self.format_str)

    def format(self, value):
        return self.stringify(value)

    @property
    def formatNow(self):
        return self.format(Time.now())


TimeFormat.DATE = TimeFormat('%Y-%m-%d')
TimeFormat.TIME = TimeFormat('%Y-%m-%d %H:%M:%S')
TimeFormat.DATE_ID = TimeFormat('%Y%m%d')


class TimeUnit:
    class SECONDS_IN:
        DAY = 86400


class Hash:
    @staticmethod
    def md5(value):
        return hashlib.md5(value.encode('utf-8')).hexdigest()


class WWW:
    def __init__(self, url):
        self.url = url

    def download_binary(self, path):
        with urlopen(self.url, timeout=120) as response:
            with open(path, 'wb') as output:
                shutil.copyfileobj(response, output)


class Git:
    def __init__(self, url):
        self.url = url
        self.directory = None

    def clone(self, directory, branch):
        destination = str(Path(directory).resolve())
        subprocess.run(
            ['git', 'clone', '--branch', branch, '--', self.url, destination],
            check=True,
        )
        self.directory = destination

    def checkout(self, branch):
        if self.directory is None:
            raise RuntimeError('Clone the data directory before checking out a branch')
        subprocess.run(['git', '-C', self.directory, 'checkout', branch], check=True)
