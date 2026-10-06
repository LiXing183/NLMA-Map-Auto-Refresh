# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Xing Li
import json
import time
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from qgis.PyQt.QtCore import QTimer, QUrl
from qgis.PyQt.QtGui import QImage, QIcon
from pathlib import Path
from qgis.PyQt.QtNetwork import QNetworkRequest
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsRasterLayer, QgsDataSourceUri, QgsMessageLog, Qgis
from qgis.core import QgsNetworkAccessManager, QgsMapLayerStyle
from .token_parser import extract_token
from .uri_tools import read_uri, is_target_url, service_key, service_base, SERVICES, zoom_range

HOME = 'https://nsp.nlma.gov.tw/ngis/'
TITLE = 'NLMA都市計畫/國家公園使用分區圖連線'
PARK = 'NATIONAL_PARK_LANDUSE_ZONE_3857'
URBAN = 'URBAN_LANDUSE_ZONE_3857'
DEFAULT_NAMES = {
    URBAN: 'NLMA_都市計畫使用分區',
    PARK: 'NLMA_國家公園使用分區',
}


class Plugin:
    def __init__(self, iface):
        self.iface = iface
        self.active = True
        self.busy = False
        self.reply = None
        self.last_refresh = 0
        self.epoch = 0
        self.timer = QTimer(iface.mainWindow())
        self.timer.setInterval(5 * 60 * 1000)
        self.timer.timeout.connect(self.check)

    def initGui(self):
        icon = QIcon(str(Path(__file__).with_name("logoico.png")))
        self.action = QAction(icon, '立即更新支援圖層連線', self.iface.mainWindow())
        self.action.triggered.connect(self.manual)
        self.iface.addPluginToMenu(TITLE, self.action)
        self.urban_action = QAction(icon, '加入都市計畫使用分區', self.iface.mainWindow())
        self.urban_action.triggered.connect(self.add_urban)
        self.iface.addPluginToMenu(TITLE, self.urban_action)
        self.park_action = QAction(icon, '加入國家公園使用分區', self.iface.mainWindow())
        self.park_action.triggered.connect(self.add_park)
        self.iface.addPluginToMenu(TITLE, self.park_action)
        QgsProject.instance().readProject.connect(self.project_read)
        QgsProject.instance().cleared.connect(self.project_cleared)
        self.timer.start()
        self.check(force=True)

    def unload(self):
        self.active = False
        self.timer.stop()
        self.timer.deleteLater()
        QgsProject.instance().readProject.disconnect(self.project_read)
        QgsProject.instance().cleared.disconnect(self.project_cleared)
        if self.reply:
            self.reply.abort()
        self.iface.removePluginMenu(TITLE, self.action)
        self.action.deleteLater()
        self.iface.removePluginMenu(TITLE, self.urban_action)
        self.urban_action.deleteLater()
        self.iface.removePluginMenu(TITLE, self.park_action)
        self.park_action.deleteLater()

    def layers(self, key=None):
        result = []
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsRasterLayer) or layer.providerType() != 'wms':
                continue
            uri = read_uri(layer.source())
            url = uri.param('url')
            if uri.param('type').lower() == 'xyz' and is_target_url(url) and (key is None or service_key(url) == key):
                result.append(layer)
        return result

    def manual(self, *args):
        if not self.layers():
            rasters = [layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsRasterLayer)]
            xyz = sum(layer.providerType() == 'wms' and read_uri(layer.source()).param('type').lower() == 'xyz' for layer in rasters)
            self.log('v1.2.2 未辨識到目標：目前 %d 個影像圖層、%d 個 XYZ 圖層。可從選單加入都市計畫或國家公園使用分區。' % (len(rasters), xyz), True)
        else:
            self.log('v1.2.2 已辨識 %d 個支援圖層，開始檢查連線。' % len(self.layers()))
            self.check(force=True)

    def project_read(self, *args):
        self.project_cleared()
        # Cancel callbacks belonging to the previous project before refreshing.
        self.check(force=True)

    def project_cleared(self, *args):
        self.epoch += 1
        self.busy = False
        self.last_refresh = 0
        if self.reply:
            self.reply.abort()

    def add_park(self, *args):
        self.add_service(PARK)

    def add_urban(self, *args):
        self.add_service(URBAN)

    def add_service(self, key):
        if self.busy:
            self.iface.messageBar().pushMessage(TITLE, '連線檢查進行中，請稍候再按加入。', duration=8)
            return
        self.check(force=True, create=key)

    def log(self, message, warning=False):
        QgsMessageLog.logMessage(message, TITLE, Qgis.MessageLevel.Warning if warning else Qgis.MessageLevel.Info)
        if warning:
            self.iface.messageBar().pushWarning(TITLE, message)

    def fail(self, message):
        self.busy = False
        self.log(message + ' 保留原圖層，5 分鐘後再檢查。', True)

    def get(self, url, callback, failure=None, refresh_on_auth_error=False):
        failure = failure or self.fail
        epoch = self.epoch
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b'Referer', b'https://nsp.nlma.gov.tw/')
        req.setRawHeader(b'Origin', b'https://nsp.nlma.gov.tw')
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = QgsNetworkAccessManager.instance().get(req)
        self.reply = reply
        timer = QTimer(reply)
        timer.setSingleShot(True)
        expired = [False]
        def timeout():
            expired[0] = True
            reply.abort()
        def done():
            timer.stop()
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            data = bytes(reply.readAll())
            if self.reply is reply:
                self.reply = None
            reply.deleteLater()
            if not self.active or epoch != self.epoch:
                return
            if not expired[0] and refresh_on_auth_error and status in (401, 403, 498, 499):
                self.refresh()
                return
            if expired[0] or status != 200:
                failure('請求逾時。' if expired[0] else 'HTTP 狀態：%s。' % status)
                return
            try:
                callback(data)
            except Exception:
                # Never expose response bodies, URLs or credential-bearing exceptions.
                failure('回應解析或更新失敗，請查看官方圖台是否需要驗證。')
        timer.timeout.connect(timeout)
        reply.finished.connect(done)
        timer.start(30000)

    def check(self, force=False, create=None):
        if not self.active or self.busy:
            return
        layers = self.layers()
        if not layers and not create:
            return
        self.busy = True
        self.targets = {layer.id(): layer.source() for layer in layers}
        self.create = create
        self.keys = list(dict.fromkeys(service_key(read_uri(layer.source()).param('url')) for layer in layers))
        if create and create not in self.keys:
            self.keys.append(create)
        if force or time.monotonic() - self.last_refresh >= 1800:
            self.refresh()
            return
        self.health(list(self.targets))

    def health(self, pending):
        if not pending:
            self.busy = False
            return
        layer = QgsProject.instance().mapLayer(pending.pop(0))
        if layer is None or layer.source() != self.targets.get(layer.id()):
            self.health(pending)
            return
        uri = read_uri(layer.source())
        key = service_key(uri.param('url'))
        if not key:
            self.health(pending)
            return
        query = dict(parse_qsl(urlsplit(uri.param('url')).query))
        query['f'] = 'json'
        def checked(data):
            info = json.loads(data)
            if info.get('error', {}).get('code') in (498, 499):
                self.refresh()
            elif 'tileInfo' in info:
                self.health(pending)
            else:
                self.fail('服務未回傳有效圖磚設定。')
        self.get(service_base(key) + '?' + urlencode(query), checked, refresh_on_auth_error=True)

    def refresh(self):
        def home_loaded(data):
            try:
                token = extract_token(data.decode('utf-8-sig'))
            except ValueError:
                self.fail('主頁未提供有效 token；請開啟官方圖台確認是否需要驗證。')
                return
            self.batch_failed = False
            self.refresh_next(token, list(self.keys))
        self.get(HOME, home_loaded)

    def refresh_next(self, token, pending):
        if not pending:
            if not self.batch_failed:
                self.last_refresh = time.monotonic()
            self.busy = False
            return
        key = pending.pop(0)
        def failed(message):
            self.batch_failed = True
            self.log(SERVICES[key][0] + '：' + message + ' 未加入或已保留原連線。', True)
            self.refresh_next(token, pending)
        def verified(data):
            info = json.loads(data)
            if 'error' in info or 'tileInfo' not in info:
                failed('新 token 未通過服務驗證。')
                return
            try:
                levels = zoom_range(info)
            except (ValueError, TypeError, KeyError):
                failed('圖磚座標或縮放設定不符合標準 XYZ。')
                return
            def image_loaded(pixels):
                self.apply(key, token, pixels, levels)
                self.refresh_next(token, pending)
            self.get(service_base(key) + '/tile/' + SERVICES[key][1] + '?' + urlencode({'token': token}), image_loaded, failed)
        self.get(service_base(key) + '?' + urlencode({'f': 'json', 'token': token}), verified, failed)

    def apply(self, key, token, pixels, levels):
        image = QImage.fromData(pixels)
        if image.isNull() or image.width() != 256 or image.height() != 256:
            raise ValueError('Invalid tile')
        count = 0
        existing = self.layers(key)
        for layer in existing:
            old = self.targets.get(layer.id())
            if old != layer.source():
                continue
            uri = read_uri(old)
            parts = urlsplit(uri.param('url'))
            query = dict(parse_qsl(parts.query))
            query['token'] = token
            uri.removeParam('url')
            uri.setParam('url', urlunsplit(parts._replace(query=urlencode(query))))
            for header, val in [('http-header:referer', 'https://nsp.nlma.gov.tw/'), ('http-header:Origin', 'https://nsp.nlma.gov.tw')]:
                uri.removeParam(header)
                uri.setParam(header, val)
            new = bytes(uri.encodedUri()).decode('utf-8')
            if new != old:
                style = QgsMapLayerStyle()
                style.readFromLayer(layer)
                layer.setDataSource(new, layer.name(), 'wms')
                if not layer.isValid():
                    layer.setDataSource(old, layer.name(), 'wms')
                    style.writeToLayer(layer)
                    raise ValueError('Invalid replacement')
                style.writeToLayer(layer)
                layer.triggerRepaint()
            count += 1
        if self.create == key and not existing:
            uri = QgsDataSourceUri()
            for param, value in {
                'type': 'xyz', 'url': service_base(key) + '/tile/{z}/{y}/{x}?' + urlencode({'token': token}),
                'zmin': str(levels[0]), 'zmax': str(levels[1]),
                'http-header:referer': 'https://nsp.nlma.gov.tw/',
                'http-header:Origin': 'https://nsp.nlma.gov.tw',
            }.items():
                uri.setParam(param, value)
            layer = QgsRasterLayer(bytes(uri.encodedUri()).decode('utf-8'), DEFAULT_NAMES[key], 'wms')
            if not layer.isValid():
                raise ValueError('Invalid new layer')
            QgsProject.instance().addMapLayer(layer)
            count += 1
            area = '國家公園' if key == PARK else '都市計畫區'
            self.iface.messageBar().pushMessage(TITLE, DEFAULT_NAMES[key] + ' 已加入，請移至' + area + '範圍查看。', duration=12)
        self.log(SERVICES[key][0] + '：連線驗證成功，已加入／更新／確認 %d 個圖層；未輸出 token。' % count)
