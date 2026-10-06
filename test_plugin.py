import math
import unittest
from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsDataSourceUri
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice
from qgis.PyQt.QtGui import QImage
from nlma_token_refresh.plugin import Plugin, URBAN, TITLE
from nlma_token_refresh.uri_tools import zoom_range, service_base, service_key, read_uri
from nlma_token_refresh.token_parser import extract_token

app = QgsApplication([], False)
app.initQgis()

class Iface:
    def __init__(self):
        self.window = QMainWindow()
        self.actions = []
    def mainWindow(self): return self.window
    def addPluginToMenu(self, title, action): self.actions.append(action)
    def removePluginMenu(self, title, action): self.actions.remove(action)
    def messageBar(self): return self
    def pushMessage(self, *a, **kw): pass
    def pushWarning(self, *a, **kw): pass

class Tests(unittest.TestCase):
    def setUp(self):
        QgsProject.instance().clear()
        self.iface = Iface()
        self.plugin = Plugin(self.iface)
        self.plugin.initGui()
    def tearDown(self):
        self.plugin.unload()
        QgsProject.instance().clear()
    def tile(self):
        im = QImage(256,256,QImage.Format_ARGB32); im.fill(0xff006934)
        buf = QBuffer(); buf.open(QIODevice.WriteOnly); im.save(buf,'PNG')
        return bytes(buf.data())
    def info(self):
        return {'tileInfo':{'rows':256,'cols':256,'origin':{'x':-20037508.342789244,'y':20037508.342789244},'spatialReference':{'wkid':3857},'lods':[{'level':z,'resolution':156543.03392804097/2**z} for z in range(5,8)]}}
    def test_menu_icon_and_lifecycle(self):
        self.assertEqual(len(self.iface.actions),3)
        self.assertFalse(self.plugin.action.icon().pixmap(24,24).isNull())
        self.assertEqual(TITLE,'NLMA都市計畫/國家公園使用分區圖連線')
        self.assertTrue(self.plugin.timer.isActive())
    def test_real_xyz_creation_and_update(self):
        p=self.plugin; p.targets={}; p.create=URBAN
        p.apply(URBAN,'old_token',self.tile(),(5,7))
        layer=p.layers()[0]; self.assertTrue(layer.isValid())
        layer.setOpacity(.4); layer.setName('自訂名稱')
        p.targets={layer.id():layer.source()}; p.create=None
        p.apply(URBAN,'new_token',self.tile(),(5,7))
        self.assertIn('new_token',read_uri(layer.source()).param('url'))
        self.assertEqual(layer.name(),'自訂名稱'); self.assertAlmostEqual(layer.opacity(),.4)
        self.assertEqual(len(p.layers()),1)
    def test_bad_tile_preserves_layer(self):
        p=self.plugin; p.targets={}; p.create=URBAN
        with self.assertRaises(ValueError): p.apply(URBAN,'token',b'not an image',(5,7))
        self.assertFalse(p.layers())
    def test_project_read_invalidates_old_callbacks(self):
        epoch=self.plugin.epoch; self.plugin.busy=True
        self.plugin.project_read()
        self.assertGreater(self.plugin.epoch,epoch); self.assertFalse(self.plugin.busy)
    def test_zoom_validation(self):
        self.assertEqual(zoom_range(self.info()),(5,7))
        for value in (math.nan,math.inf,0):
            info=self.info(); info['tileInfo']['origin']['x']=value
            with self.assertRaises(ValueError): zoom_range(info)
        info=self.info(); info['tileInfo']['lods'][0]['level']=5.5
        with self.assertRaises(ValueError): zoom_range(info)
    def test_service_scope(self):
        url=service_base(URBAN)+'/tile/{z}/{y}/{x}?token=test'
        self.assertEqual(service_key(url),URBAN)
        self.assertIsNone(service_key(url.replace('giss.nlma.gov.tw','evil.example')))
    def test_token_parser(self):
        token='abcdefghijklmnop1234'
        self.assertEqual(extract_token('<script>// var layerToken="wrongwrongwrongwrong";\nconst layerToken="'+token+'";</script>'),token)
        with self.assertRaises(ValueError): extract_token('<script src="x">var layerToken="'+token+'";</script>')
        with self.assertRaises(ValueError): extract_token('<script>var layerToken="'+token+'"; let layerToken="differentdifferent";</script>')

if __name__=='__main__': unittest.main()
