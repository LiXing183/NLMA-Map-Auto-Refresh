# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Xing Li
from urllib.parse import urlsplit, unquote
import math

ROOT = 'https://giss.nlma.gov.tw/tcdmap/rest/services/TCDPDA/'
SERVICES = {
    'URBAN_LANDUSE_ZONE_3857': ('都市計畫土地使用分區', '15/14025/27442'),
    'NATIONAL_PARK_LANDUSE_ZONE_3857': ('國家公園使用分區', '17/56058/109795'),
}


def service_base(key):
    if key not in SERVICES:
        raise ValueError('Unknown service')
    return ROOT + key + '/MapServer'


def read_uri(source):
    from qgis.core import QgsDataSourceUri
    uri = QgsDataSourceUri()
    # XYZ uses an encoded query URI, not the database connection-string syntax.
    uri.setEncodedUri(source)
    return uri


def is_target_url(url):
    return service_key(url) is not None


def service_key(url):
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() != 'https' or parts.netloc.lower() != 'giss.nlma.gov.tw':
            return None
        for key in SERVICES:
            if unquote(parts.path).rstrip('/') == urlsplit(service_base(key)).path + '/tile/{z}/{y}/{x}':
                return key
    except ValueError:
        pass
    return None


def zoom_range(info):
    tile = info.get('tileInfo', {})
    sr = tile.get('spatialReference', {})
    origin = tile.get('origin', {})
    if (sr.get('latestWkid', sr.get('wkid')) not in (3857, 102100, 102113)
            or tile.get('rows') != 256 or tile.get('cols') != 256
            or not math.isclose(float(origin.get('x', 0)), -20037508.342789244, rel_tol=0, abs_tol=1)
            or not math.isclose(float(origin.get('y', 0)), 20037508.342789244, rel_tol=0, abs_tol=1)):
        raise ValueError('非標準 Web Mercator XYZ 圖磚設定')
    levels = []
    for lod in tile.get('lods', []):
        raw_level = lod['level']
        level = int(raw_level)
        if isinstance(raw_level, bool) or float(raw_level) != level:
            raise ValueError('縮放級別必須是整數')
        if not 0 <= level <= 30 or not math.isclose(float(lod['resolution']), 156543.03392804097 / (2 ** level), rel_tol=1e-6):
            raise ValueError('非標準縮放級別')
        levels.append(level)
    if not levels or sorted(levels) != list(range(min(levels), max(levels)+1)):
        raise ValueError('縮放級別不連續或為空')
    return min(levels), max(levels)
