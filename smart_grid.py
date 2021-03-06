#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, pyqtSlot
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

import sys
import os
import psycopg2
import psycopg2.extras #To get the queried data in a dict
# Import GUI files

from smartgrid_gui import Ui_MainWindow
from login_gui import Ui_Dialog
from connect_gui import Ui_pgDialog
from sensor_gui import Ui_sDialog		

# Environment variable QGISHOME must be set to the install directory
# before running the application

QGIS_PREFIX = os.getenv('QGISHOME')
uri=QgsDataSourceURI()
conn_string = "host='localhost' dbname='sensors' user='pranay360' password='1234'"
conn = psycopg2.connect(conn_string)
sname=[]
sname.insert(0,None)

#Class to show sensor deployment form- DON'T CHANGE
class sensor(QDialog, Ui_sDialog):
    global conn,sname
    def __init__(self, parent=None):
        super(sensor, self).__init__(parent)
        self.setupUi(self)
        self.cursor=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)       
        self.cursor.execute("select id,name,range from sensors")
        self.buffer=[]
        for self.row in self.cursor: #traversing self.cursor as a dict
            self.comboBox.addItem(self.row['name'])
            self.buffer.append("ID: "+str(self.row['id'])+"\nSensor Type: "+str(self.row['name'])+"\nSensor Range: "+str(self.row['range']))
        self.comboBox.connect(self.comboBox,SIGNAL("currentIndexChanged(int)"),
					self,SLOT("onIndexChange(int)"))
        self.sinfo.setPlainText(QString(self.buffer[0]))
        self.comboBox.activated[str].connect(self.onActivated)
        self.sdeploy.clicked.connect(self.ondeployclicked)
    
    def onActivated(self, text):
    	sname.insert(0,str(text)) #Sensor Selected by user to deploy on map at sname[0]
    
    def ondeployclicked(self):
        self.close()
    
    @pyqtSlot(int)
    def onIndexChange(self, i):
        self.sinfo.setPlainText(QString(self.buffer[i])) #sensor information


#class to capture coordinateswhile hovering mouse over canvas- DON'T CHANGE
class MapCoords(object):
    def __init__(self, mainwindow):
        self.mainwindow = mainwindow
        # This one is to capture the mouse move for coordinate display
    
        QObject.connect(mainwindow.canvas, SIGNAL('xyCoordinates(const QgsPoint&)'), self.updateCoordsDisplay)
        self.latlon = QLabel("0.0 , 0.0")
        self.latlon.setFixedWidth(300)
        self.latlon.setAlignment(Qt.AlignHCenter)
        self.latlon.setFrameStyle(QFrame.StyledPanel)
        self.mainwindow.statusbar.addPermanentWidget(self.latlon)

  # Signal handeler for updating coord display
    def updateCoordsDisplay(self, point):

        capture_string = QString(str(point.x()) + " , " + str(point.y()))
        self.latlon.setText(capture_string)

#class for postgis connectivity	
class pgconnect(QDialog,Ui_pgDialog):
    global uri
    def __init__(self, parent=None):
        super(pgconnect, self).__init__(parent)
        self.setuppgUi(self)
        self.runame=False
        self.rpwd=False
        self.rdb=False
        #ADD Functionality HERE to remember fields using check box, above variables are for storing remembered parameters
        self.pgpushButton.clicked.connect(self.onclick_pglogin)
        self.hname='localhost'
        self.port='5432'
        self.dbname=None
        self.uname=None
        self.pwd=None
        self.table=None
        self.key=None
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())
     
    def onclick_pglogin(self):
        self.dbname=self.pglineEdit_3.text()
        self.uname=self.pglineEdit_4.text()
        self.pwd=self.pglineEdit_5.text()
        self.table=self.pglineEdit_6.text()
        self.key=self.pglineEdit_7.text()
        uri.setConnection(self.hname, self.port, str(self.dbname), str(self.uname), str(self.pwd))
        uri.setDataSource("public", str(self.table), "the_geom",'', str(self.key))
        self.close()
        

class SmartGrid(QMainWindow, Ui_MainWindow):
    global uri, sname
    def __init__(self, parent=None):
        super(SmartGrid, self).__init__(parent)
        self.setupUi(self)
        self.root_flag = False
        self.count=0 #a counter for no. of sensors deployed
        conn_string1 = "host='localhost' dbname='sensors' user='pranay360' password='1234'"
        conn1 = psycopg2.connect(conn_string1)
        curs= conn1.cursor()
        curs.execute("select * from information_schema.tables where table_name='range'")
        if bool(curs.rowcount) is True:
            curs.execute("drop table range")
            conn1.commit()
        curs.execute("update sensors set the_geom=NULL,deployed=0")
        conn1.commit()
        conn1.close()
        self.setWindowTitle('Smart Grid')
        self.actionImport_Rlayer.triggered.connect(self.onactionImport_Rlayer_toggled)
        self.actionImport_Vlayer.triggered.connect(self.onactionImport_Vlayer_toggled)
        self.actionImport_PGlayer.triggered.connect(self.onactionImport_PGlayer_toggled)
        self.actionPan.triggered.connect(self.click_to_pan)
        
        self.canvas = QgsMapCanvas()
        self.canvas.useImageToRender(False)
        self.map_coords = MapCoords(self)
        self.actionPlot_Sensors.triggered.connect(self.onactionPlot_Sensors_toggled)
        # Reference to root node of layer tree
        
        self.root = QgsProject.instance().layerTreeRoot()

        # Convert project into a layer tree so
        # that the layers appear on the canvas

        self.bridge = QgsLayerTreeMapCanvasBridge(self.root,
                self.canvas)

        self.canvas.show()

        # Table of Contents/Legend Model

        self.model = QgsLayerTreeModel(self.root)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)
        self.view = QgsLayerTreeView()
        self.view.setModel(self.model)

        # Dock legend to main window

        self.LegendDock = QDockWidget('Layer Tree', self)
        self.LegendDock.setObjectName('layers')
        self.LegendDock.setAllowedAreas(Qt.LeftDockWidgetArea
                | Qt.RightDockWidgetArea)
        self.LegendDock.setWidget(self.view)
        self.LegendDock.setContentsMargins(5, 5, 5, 5)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.LegendDock)

        self.layout = QVBoxLayout(self.frame)
        self.layout.addWidget(self.canvas)
        
    def onactionPlot_Sensors_toggled(self,checked=None):
        if checked is None:
            return
        if sname[0] is None:
            self.sdlg=sensor(self) #don't change
        self.sdlg.show()
        self.point= QgsMapToolEmitPoint(self.canvas)	
        self.canvas.setMapTool(self.point)
        QObject.connect(self.point, SIGNAL("canvasClicked(const QgsPoint &,Qt::MouseButton)"), self.func)
        
    def func(self, p):
        conn_string = "host='localhost' dbname='sensors' user='pranay360' password='1234'"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor() 
        cursor2 = conn.cursor()
        dcursor= conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 
        capture_string = str(p.x()) + " " +str(p.y())
        dcursor.execute("select range,deployed from sensors where name='"+sname[0]+"'")
        
        for row in dcursor:
            srange=row['range'] #ALGORITHM TO CHANGE KILOMETERS TO DEGREE AS ST_BUFFER TAKES RADIUS IN DEGREE ONLY.
            dflag=row['deployed']
        
        cursor.execute("update sensors set the_geom='SRID=4326;POINT("+capture_string+")' where name='"+sname[0]+"'")
        conn.commit()
        if self.count is 0 and dflag is 0:
            cursor2.execute("CREATE TABLE range AS SELECT id,name, ST_Buffer(the_geom,"+str(srange)+") AS the_geom FROM sensors where name='"+sname[0]+"'") 
            conn.commit()
        elif self.count > 0 and dflag is 0:
            cursor2.execute("INSERT INTO range SELECT id,name, ST_Buffer(the_geom,"+str(srange)+") AS the_geom FROM sensors where name='"+sname[0]+"'")
            conn.commit()
        elif dflag is 1:
            cursor2.execute("delete from range where name='"+sname[0]+"'")
            conn.commit()
            cursor2.execute("INSERT INTO range SELECT id,name, ST_Buffer(the_geom,"+str(srange)+") AS the_geom FROM sensors where name='"+sname[0]+"'")
            conn.commit()
        cursor2.execute("update sensors set deployed=1 where name='"+sname[0]+"'") 
        conn.commit() 
        conn.close()
        uri1=QgsDataSourceURI()
        uri1.setConnection('localhost', '5432', 'sensors', 'pranay360', '1234')
        uri1.setDataSource('public', 'range', 'the_geom','', 'id')
        
        if self.count is not 0:
            self.root.removeLayer(self.vlayer2)
        self.vlayer2 = QgsVectorLayer(uri1.uri(), "range", "postgres")
        if not self.vlayer2.isValid():
            print 'Layer failed to load!'
            return
        myRenderer = self.vlayer2.rendererV2()
        mySymbol = myRenderer.symbol()
        mySymbol.setAlpha(0.69)
        QgsMapLayerRegistry.instance().addMapLayer(self.vlayer2, False)
        if self.root_flag is False:
            rootnode = self.root.insertLayer(0, self.vlayer2)
            print 'Loaded root'
            self.root_flag = True
        else:
            self.root.insertLayer(0, self.vlayer2)
        uri1.setConnection('localhost', '5432', 'sensors', 'pranay360', '1234')
        uri1.setDataSource('public', 'sensors', 'the_geom','', 'id')
        if self.count is not 0:
            self.root.removeLayer(self.vlayer)
        self.vlayer = QgsVectorLayer(uri1.uri(), "sensors", "postgres") #loading a posgres database table as a vector layer using postgis
        #all palyr related stuff is to display label around deployed sensor
        palyr= QgsPalLayerSettings()
        self.canvas.mapRenderer().setLabelingEngine(QgsPalLabeling())
        palyr.readFromLayer(self.vlayer)
        palyr.enabled = True 
        palyr.fieldName = 'name'
        palyr.placement= QgsPalLayerSettings.Free
        palyr.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'8','')
        palyr.writeToLayer(self.vlayer)
        #normal procedure to add vector layer
        if not self.vlayer.isValid():
            print 'Layer failed to load!'
            return
        QgsMapLayerRegistry.instance().addMapLayer(self.vlayer, False)
        if self.root_flag is False:
            rootnode = self.root.insertLayer(0, self.vlayer)
            print 'Loaded root'
            self.root_flag = True
        else:
            self.root.insertLayer(0, self.vlayer)
        self.statusbar.showMessage("Selected: ")
        self.canvas.refresh()
        #setting buffer
        
        self.count=self.count+1
                             
    
    def onactionImport_Rlayer_toggled(self, checked=None):
        if checked is None:
            return
        fileName = QFileDialog.getOpenFileName(self, 'Open Layer', '.',
                'Image Files (*.tif)')
        fileInfo = QFileInfo(fileName)
        baseName = fileInfo.baseName()
        raster_layer = QgsRasterLayer(fileName, baseName)
        if not raster_layer.isValid():
            print 'Layer failed to load!'
            return

        # Add layer to the registry....
        QgsMapLayerRegistry.instance().addMapLayer(raster_layer, False)
        if self.root_flag is False:
            rootnode = self.root.insertLayer(0, raster_layer)
            print 'Loaded root'
            self.root_flag = True
        else:
            self.root.insertLayer(0, raster_layer)
        
    def onactionImport_Vlayer_toggled(self, checked=None):
        if checked is None:
            return
        fileName = QFileDialog.getOpenFileName(self, 'Open Layer', '.',
                'shp (*.shp);;dgn (*.dgn)')
        fileInfo = QFileInfo(fileName)
        vector_layer = QgsVectorLayer(fileName, fileInfo.fileName(),
                'ogr')
        if not vector_layer.isValid():
            print 'Layer failed to load!'
            return

        palyr= QgsPalLayerSettings()
        self.canvas.mapRenderer().setLabelingEngine(QgsPalLabeling())
        palyr.readFromLayer(vector_layer)
        palyr.enabled = True 
        palyr.fieldName = 'NAME'
        palyr.placement= QgsPalLayerSettings.Free
        palyr.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'8','')
        palyr.writeToLayer(vector_layer)
        QgsMapLayerRegistry.instance().addMapLayer(vector_layer, False)
        
        if self.root_flag is False:
            rootnode = self.root.insertLayer(0, vector_layer)
            print 'Loaded root'
            self.root_flag = True
        else:
            self.root.insertLayer(0, vector_layer)
    
    def onactionImport_PGlayer_toggled(self):
        self.dlg= pgconnect(self)
        self.dlg.show()
        self.dlg.exec_()
        vlayer = QgsVectorLayer(uri.uri(), "people", "postgres")
    	if not vlayer.isValid():
            print 'Layer failed to load!'
            return
        QgsMapLayerRegistry.instance().addMapLayer(vlayer, False)
        if self.root_flag is False:
            rootnode = self.root.insertLayer(0, vlayer)
            print 'Loaded root'
            self.root_flag = True
        else:
            self.root.insertLayer(0, vlayer)
	
    def click_to_pan(self):
        self.toolPan = QgsMapToolPan(self.canvas)
        self.toolPan.setAction(self.actionPan)
        self.canvas.setMapTool(self.toolPan)


    
class LoginScreen(QDialog, Ui_Dialog):

    def __init__(self, parent=None):
        super(LoginScreen, self).__init__(parent)
        self.setupUi(self)
        self.pushButton.clicked.connect(self.onclick_login)
        self.setWindowTitle('Login')

    def onclick_login(self):
        self.username = self.lineEdit.text()
        self.password = self.lineEdit_2.text()
        if self.username == '' and self.password == '':
            self.close()
            self.main_window = SmartGrid(self)
            self.main_window.showMaximized()
        else:
            QMessageBox.warning(self, 'Warning',
                                'Incorrect Username/Password')
            self.lineEdit.clear()
            self.lineEdit_2.clear()


def main(argv):

    # create Qt application

    app = QApplication(argv)

    # Initialize qgis libraries

    QgsApplication.setPrefixPath(QGIS_PREFIX, True)
    QgsApplication.initQgis()

    login_window = LoginScreen()
    login_window.move(100, 100)
    login_window.show()

    retval = app.exec_()

    QgsApplication.exitQgis()
    sys.exit(retval)


if __name__ == '__main__':
    main(sys.argv)

