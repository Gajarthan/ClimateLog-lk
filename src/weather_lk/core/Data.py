"""Compatibility read facade over the transactional observation store.

New application code should receive Settings and ObservationStore explicitly.
"""

from functools import cached_property

from weather_lk.config import Settings
from weather_lk.exports.json_tsv import build_legacy_data
from weather_lk.storage.database import Database
from weather_lk.storage.observations import ObservationStore


class Data:
    DIR_REPO = str(Settings.from_env().data_dir)
    DIR_DATA_CHARTS = str(Settings.from_env().data_dir / 'charts')
    DIR_DATA_BY_PLACE = str(Settings.from_env().data_dir / 'data_by_place')
    DIR_DATA_CHARTS_MIN_MAX_PLOT = str(Settings.from_env().data_dir / 'charts' / 'min_max_plot')
    DIR_DATA_CHARTS_RAINFALL = str(Settings.from_env().data_dir / 'charts' / 'rainfall')
    DIR_DATA_CHARTS_TEMPERATURE = str(Settings.from_env().data_dir / 'charts' / 'temperature')
    DIR_REPO_PDF_ARCHIVE_ORG = str(Settings.from_env().data_dir / 'pdf_archive_org')
    DIR_REPO_PDF_METEO_GOV_LK = str(Settings.from_env().data_dir / 'pdf_meteo_gov_lk')
    DIR_REPO_PDF_GOOGLE_SEARCH = str(Settings.from_env().data_dir / 'pdf_google_search')
    DIR_REPO_PDF_PARSED = str(Settings.from_env().data_dir / 'pdf_parsed')
    DIR_REPO_JSON_PARSED = str(Settings.from_env().data_dir / 'json_parsed')
    DIR_REPO_JSON_PLACEHOLDER = str(Settings.from_env().data_dir / 'json_placeholder')

    @staticmethod
    def init():
        return Database(Settings.from_env().database_path)

    @staticmethod
    def _exports():
        rows = ObservationStore(Data.init()).current()
        return build_legacy_data(rows)

    @staticmethod
    def list_all():
        return Data._exports()['list_all']

    list_all_raw = list_all

    @staticmethod
    def clean(data):
        return data

    @staticmethod
    def max():
        reports = Data.list_all()
        if not reports:
            raise ValueError('No observations available; ingest reports or import a legacy archive first')
        return reports[-1]

    @staticmethod
    def idx_by_date():
        return Data._exports()['idx_by_date']

    @staticmethod
    def idx_by_place():
        return Data._exports()['idx_by_place']

    @cached_property
    def place_list(self):
        return sorted(Data.idx_by_place())

    @cached_property
    def raw_place_list(self):
        return self.place_list
