# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CsomagkezelesDockWidget
                                 A QGIS plugin
 Erdőfelmérés csomagkezelés
                             -------------------
        begin                : 2018-02-14
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Tájinformatika
        email                : pzs.vac@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from PyQt4 import QtCore, QtGui, QtSql, uic
from PyQt4.QtCore import pyqtSignal, pyqtSlot
from PyQt4.QtCore import pyqtSignature
from qgis._core import *
import qgis.utils

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'csomagkezeles_dockwidget_base.ui'))
LOGIN_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'login_dialog_base.ui'))
db = QtSql.QSqlDatabase.addDatabase("QPSQL")

class CsomagkezelesDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(CsomagkezelesDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.eLayer = None
        self.csLayer = None
        self.mintater = None
        self.mintahalo = None
        self.felmero = None
        self.formverzio = None
        self.elist = []
        self.epontlist = ''
        self.keszito = None
        self.selCsomagNev = None
        self.selCsomagAzon = None

        self.setButtonEnabling()
        self.setDefaultChecks()
        self.clearFieldCombos()
        self.clearTxtWidgets()
        self.setFrameEnabling()

        self.canvas = qgis.utils.iface.mapCanvas()
        self.canvas.selectionChanged.connect(self.onSelectionChanged)
        self.linePontok.textChanged[str].connect(self.onSelectedPontokChanged)
        self.checkTorles.stateChanged.connect(self.stateTorlesChanged)
        self.canvas.layersChanged.connect(self.epontLayer)

    def setButtonEnabling(self):
        self.pushBejelentkezes.setEnabled(False)
        self.pushPontszures.setEnabled(False)
        self.pushCsomagkeszites.setEnabled(False)
        self.pushCsomagtorles.setEnabled(False)

    def setDefaultChecks(self):
        self.radio70.setChecked(True)
        self.checkTeszt.setChecked(False)
        self.checkTorles.setEnabled(False)

    def clearFieldCombos(self):
        self.comboMintater.clear()
        self.comboFelmero.clear()
        self.comboFormverzio.clear()

    def clearTxtWidgets(self):
        self.lineTask.setText('')
        self.linePontok.setText('')

    def setFrameEnabling(self):
        self.frameSzures.setEnabled(False)
        self.frameCreate.setEnabled(False)
        self.frameDelete.setEnabled(False)

    def selectedMintavetel(self):
        if self.radio50.isChecked():
            return 50
        elif self.radio70.isChecked():
            return 70
        elif self.radio100.isChecked():
            return 100

    def epontLayer(self, lrs = None):
        if lrs is None:
            layers = qgis.utils.iface.legendInterface().layers()
        else:
            layers = lrs
        eLyr = None
        csLyr = None
        for layer in layers:
            epontOK = 0
            csomOK = 0
            layerType = layer.type()
            if layerType == QgsMapLayer.VectorLayer:
                #print layerType, layer.geometryType(), layer.name()
                if layer.geometryType() == 0 and layer.name() == 'epont':
                    fields = layer.pendingFields()
                    for field in fields:
                        if field.name()[:5] == 'epont' and field.name()[6:]=='azon' and field.typeName() == 'int4':
                            epontOK += 1
                        if field.name() in ['net70', 'net100'] and field.typeName() == 'bool':
                            epontOK += 1

                elif layer.geometryType() == 2 and layer.name() == 'csomag':
                    fields = layer.pendingFields()
                    for field in fields:
                        if field.name()[:6] == 'csomag' and field.name()[7:]=='nev' and field.typeName() == 'character':
                            csomOK += 1

            if layer.geometryType() == 0:
                #print layer.geometryType(), layer.name(),'epontOK: ' + str(epontOK)
                if epontOK == 3:
                    eLyr = layer
                    qgis.utils.iface.setActiveLayer(layer)
            elif layer.geometryType() == 2:
                #print layer.geometryType(), layer.name(),'csomOK: ' + str(csomOK)
                if csomOK == 1:
                    csLyr = layer

        #print 'E layer: ',self.eLayer
        #print 'CS layer: ', self.csLayer
        if not self.eLayer is None and eLyr is None:
            self.eLayer = None
            self.setDefaultChecks()
            self.clearTxtWidgets()
            self.clearFieldCombos()
            self.frameSzures.setEnabled(False)
            self.frameCreate.setEnabled(False)
            self.pushCsomagkeszites.setEnabled(False)
            self.pushBejelentkezes.setEnabled(False)
        elif self.eLayer is None and not eLyr is None:
            self.eLayer = eLyr
            self.pushBejelentkezes.setEnabled(True)
            if not self.keszito is None:
                self.frameSzures.setEnabled(True)
        elif not self.eLayer is None and not eLyr is None:
            self.eLayer = eLyr
            self.pushBejelentkezes.setEnabled(True)
            if not self.keszito is None:
                self.frameSzures.setEnabled(True)

        if not self.csLayer is None and csLyr is None:
            self.csLayer = None
            self.lineSelCsomag.clear()
            self.checkTorles.setChecked(False)
            self.frameDelete.setEnabled(False)
            self.pushCsomagtorles.setEnabled(False)
        elif self.csLayer is None and not csLyr is None:
            self.csLayer = csLyr
            self.pushBejelentkezes.setEnabled(True)
            if not self.keszito is None:
                self.frameDelete.setEnabled(True)
        elif not self.csLayer is None and not csLyr is None:
            self.csLayer = csLyr
            self.pushBejelentkezes.setEnabled(True)
            if not self.keszito is None:
                self.frameDelete.setEnabled(True)

    @pyqtSignature("")
    def on_pushBejelentkezes_clicked(self):
        self.LoginForm = LoginDialog()
        self.setDefaultChecks()
        self.clearFieldCombos()
        self.clearTxtWidgets()
        if self.LoginForm.exec_():
            if not self.LoginForm.csomagkeszito is None:
                self.keszito = self.LoginForm.csomagkeszito
                self.pushBejelentkezes.setText(u'Csomagkészítő: %s' % self.keszito)
                self.epontLayer()
                # Ez van akkor, ha accept()-tel záródik a bejelentkezés
                if len(self.LoginForm.mintateruletek) > 0:

                    for m in self.LoginForm.mintateruletek:
                        self.comboMintater.addItem(m)
                    self.pushPontszures.setEnabled(True)
                else:
                    self.pushPontszures.setEnabled(True)

        else:
            print 'Hmmm... nem indul a Login ablak!'
            # Ez van akkor ha 'Elvet' gombbal záródik a bejelentkezés

    @pyqtSignature("")
    def on_pushPontszures_clicked(self):
        self.mintahalo = self.selectedMintavetel()
        self.mintater = self.comboMintater.currentText()
        self.eLayer.setSubsetString('"projminter"=\'%s\' and "net%s"=True' % (self.mintater,str(self.mintahalo)))
        self.newExtent()

        self.checkTeszt.setChecked(False)
        self.comboFelmero.clear()
        self.comboFormverzio.clear()
        self.lineTask.setText('')
        self.linePontok.setText('')

        queryFelmeroOpciok = QtSql.QSqlQuery()
        siker = queryFelmeroOpciok.exec_("""SELECT szemely FROM
            (SELECT szemely, szerep FROM szereposztas WHERE projminter = '%s' and aktiv is True) foo1 INNER JOIN
            (SELECT szerep FROM szerep WHERE csomagkapo is True) foo2
            ON foo1.szerep = foo2.szerep;""" % self.mintater)
        if siker:
            if queryFelmeroOpciok.size() > 0:
                while queryFelmeroOpciok.next():
                    self.comboFelmero.addItem(queryFelmeroOpciok.value(0))
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Nincs felmérő rendelve a mintaterülethez.")
                return
        else:
            if queryFelmeroOpciok.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryFelmeroOpciok.lastError().text()))
                return

        queryFormOpciok = QtSql.QSqlQuery()
        siker = queryFormOpciok.exec_("""SELECT formverzio FROM formosztas
             WHERE projminter = '%s' and hasznalat is True;""" % self.mintater)
        if siker:
            if queryFormOpciok.size() > 0:
                while queryFormOpciok.next():
                    self.comboFormverzio.addItem(queryFormOpciok.value(0))
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Nincs form rendelve a mintaterülethez.")
                return
        else:
            if queryFormOpciok.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryFormOpciok.lastError().text()))
                return

        self.frameCreate.setEnabled(True)

    def newExtent(self):
        currExt = self.eLayer.extent()
        xMin = currExt.xMinimum() - 50
        xMax = currExt.xMaximum() + 50
        yMin = currExt.yMinimum() - 50
        yMax = currExt.yMaximum() + 50
        newRect = QgsRectangle(xMin, yMin, xMax, yMax)
        qgis.utils.iface.mapCanvas().setExtent(newRect)
        qgis.utils.iface.mapCanvas().refresh()

    @pyqtSignature("")
    def onSelectionChanged(self, layer, sign = False):
        if layer:
            # a kiválasztás megfelelőségének ellenőrzése
            # a vektor réteg a típus enumeráció nulladik eleme
            if layer.type() == 0 and layer.name() == 'epont':
                self.linePontok.setText(str(len(layer.selectedFeatures())))
                if len(layer.selectedFeatures()) > 0:
                    eazonx = layer.fieldNameIndex('epont_azon')
                    if eazonx != -1:
                        for e in layer.selectedFeatures():
                            self.elist.append(e.attributes()[eazonx])
                        self.elist.sort()
                        print 'elist: ',self.elist
                        eliststr = ''
                        for e in self.elist:
                            if len(eliststr) > 0:
                                eliststr = eliststr + ','
                            eliststr = eliststr + str(e)
                        self.epontlist = eliststr
                else:
                    self.epontlist = ''
                print 'epontlist: ', self.epontlist

            elif layer.type() == 0 and layer.name() == 'csomag':
                if len(layer.selectedFeatures()) == 1:
                    fidx = layer.fieldNameIndex('csomag_nev')
                    azix = layer.fieldNameIndex('csomag_azon')
                    if fidx != -1 and azix != -1:
                        f = layer.selectedFeatures()[0]
                        self.selCsomagNev = f.attributes()[fidx]
                        self.selCsomagAzon = f.attributes()[azix]
                        print self.selCsomagNev, self.selCsomagAzon
                        self.lineSelCsomag.setText(u'%s - %s' % (self.selCsomagNev, str(self.selCsomagAzon)))
                        self.checkTorles.setEnabled(True)

                elif len(layer.selectedFeatures()) > 1:
                    QtGui.QMessageBox.warning(None, u"Csomagtörlés", u"Egyszerre csak egy csomag választható ki törlésre.")
                    self.checkTorles.setEnabled(False)
                    return
                else:
                    self.lineSelCsomag.setText('')
                    self.checkTorles.setEnabled(False)

    def onSelectedPontokChanged(self, numtext):
        if numtext <> '' and not numtext is None:
            if int(numtext) > 0:
                self.pushCsomagkeszites.setEnabled(True)
            else:
                self.pushCsomagkeszites.setEnabled(False)
        else:
            self.pushCsomagkeszites.setEnabled(False)

    @pyqtSignature("")
    def on_pushCsomagkeszites_clicked(self):
        self.felmero = self.comboFelmero.currentText()
        self.formverzio = self.comboFormverzio.currentText()
        ppontlist = []

        csomgeom = self.createCsomagGeom(self.mintahalo, self.epontlist, self.mintater)
        soroszlop = self.createSorOszlop(self.epontlist, self.mintater)
        #soroszlop = [smin,smax,omin,omax]
        if not soroszlop is None:
            sor = int(soroszlop[1] - soroszlop[0] + 1)
            oszlop = int(soroszlop[3] - soroszlop[2] + 1)
            mintaterkod = self.mintater[-2:]
            pontszam = len(self.elist)
            teszt = self.checkTeszt.isChecked()
            task = self.lineTask.text()[:50]

            csomvalues = self.createCsomag(mintaterkod, self.mintater, self.felmero, csomgeom, pontszam, sor, oszlop,
                        self.keszito, teszt, self.mintahalo, self.formverzio, task)
            csomazon = csomvalues[0]
            csomagnev = csomvalues[1]
            if not csomazon is None:
                x = 1
                for i in self.elist:
                    epontdata = self.selectEpont(i, self.mintater)
                    print 'epontdata: ', epontdata
                    #epontdata = [bpont_azon,sor,oszlop,lon_wgs,lat_wgs]
                    pGeomText = 'Point(' + str(epontdata[3]) + ' ' + str(epontdata[4]) + ')'
                    ppontazon = self.createPpont(csomazon, i, epontdata[0], x,
                            int(soroszlop[1] - epontdata[1]),int(epontdata[2] - soroszlop[2]),
                            epontdata[3], epontdata[4], pGeomText, self.mintater)
                    ppontlist.append(ppontazon)
                    x += 1
                if len(ppontlist) == len(self.elist):
                    self.eLayer.removeSelection()
                    self.elist = []
                    self.epontlist = ''
                    QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Sikeres csomagkiosztás: %s" % csomagnev)
                    self.refresh_layers()
                else:
                    QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Az P-pontok száma eltér a kijelölt ponto számától.")

    def createCsomagGeom(self, ponttavolsag, epontlist, mintaterulet):
        halostr = ''
        if ponttavolsag > 50:
            halostr = str(ponttavolsag)

        queryGeomCreate = QtSql.QSqlQuery()
        siker = queryGeomCreate.exec_("""SELECT ST_AsText(ST_Multi(ST_Union(geom))) as csomgeom 
            FROM ekvad%s WHERE bpont_azon in (SELECT bpont_azon FROM epont WHERE epont_azon in (%s) 
            AND projminter = '%s');""" % (halostr, epontlist, mintaterulet))
        if siker:
            if queryGeomCreate.size() > 0:
                while queryGeomCreate.next():
                    return queryGeomCreate.value(0)
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"A csomag nem kapott geometriát.")
                return
        else:
            if queryGeomCreate.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryGeomCreate.lastError().text()))
                return


    def createSorOszlop(self, epontlist, mintaterulet):
        querySorOszlop = QtSql.QSqlQuery()
        siker = querySorOszlop.exec_("""SELECT MIN(sor) smin, MAX(sor) smax, MIN(oszlop) omin, MAX(oszlop) omax 
            FROM epont WHERE epont_azon in (%s) and projminter = '%s'""" % (epontlist, mintaterulet))
        if siker:
            if querySorOszlop.size() > 0:
                while querySorOszlop.next():
                    return [querySorOszlop.value(0),querySorOszlop.value(1),querySorOszlop.value(2),querySorOszlop.value(3)]
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"A csomag nem kapott sor-oszlop értékeket.")
                return
        else:
            if querySorOszlop.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(querySorOszlop.lastError().text()))
                return

    def createCsomag(self, mintaterkod, mintaterulet, felmero, csomgeom, pontszam, sor, oszlop, keszito, teszt, ponttavolsag,formverzio, taskstr):
        queryCsomag = QtSql.QSqlQuery()
        siker = queryCsomag.exec_("""INSERT INTO csomag (mintater,projminter,felmero,geom,cs_pontszam,sorok,oszlopok,keszito,letrehozas,hatarido,teszt,halo,formverzio,task) 
    		VALUES ('%s','%s','%s',ST_Multi(ST_GeomFromText('%s',23700)),%s,%s,%s,'%s',CURRENT_TIMESTAMP(0),CURRENT_TIMESTAMP(0)+'2 month',%s,%s,'%s','%s') RETURNING csomag_azon, csomag_nev;"""
            % (mintaterkod, mintaterulet, felmero, csomgeom, str(pontszam), str(sor), str(oszlop), keszito, teszt, str(ponttavolsag), formverzio, taskstr))
        if siker:
            if queryCsomag.size() > 0:
                while queryCsomag.next():
                    return [queryCsomag.value(0),queryCsomag.value(1)]
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"A csomag készítés nem adott vissza azonosítót.")
                return
        else:
            if queryCsomag.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryCsomag.lastError().text()))
                return

    def selectEpont(self, epontazon, mintaterulet):
        queryEpontData = QtSql.QSqlQuery()
        siker = queryEpontData.exec_("""SELECT bpont_azon,sor,oszlop,lon_wgs,lat_wgs FROM epont WHERE epont_azon in (%s) and projminter = '%s';""" % (str(epontazon), mintaterulet))
        if siker:
            if queryEpontData.size() > 0:
                while queryEpontData.next():
                    return [queryEpontData.value(0),queryEpontData.value(1),queryEpontData.value(2),queryEpontData.value(3),queryEpontData.value(4)]
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Az e-pont lekérdezés sikertelen.")
                return
        else:
            if queryEpontData.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryEpontData.lastError().text()))
                return

    def createPpont(self, csomazon, epontazon, bpontazon, x, psor, poszlop, wgslon, wgslat, geomtext, mintaterulet):
        queryPpont = QtSql.QSqlQuery()
        siker = queryPpont.exec_("""INSERT INTO ppont (csomag_azon,epont_azon,bpont_azon,sorszam,sor,oszlop,wgs84_lon,wgs84_lat,geom,projminter)\
    		VALUES (%s,%s,%s,%s,%s,%s,%s,%s,ST_GeomFromText('%s',4326),'%s') RETURNING ppont_azon"""
            % (str(csomazon),str(epontazon),str(bpontazon),str(x),str(psor),str(poszlop),str(wgslon),str(wgslat),geomtext,mintaterulet))
        if siker:
            if queryPpont.size() > 0:
                while queryPpont.next():
                    return queryPpont.value(0)
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"A ppont készítés nem adott vissza azonosítót.")
                return
        else:
            if queryPpont.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryPpont.lastError().text()))
                return

    def refresh_layers(self):
        for layer in self.canvas.layers():
            layer.triggerRepaint()
        self.canvas.refresh()

    def stateTorlesChanged(self):
        checker = self.checkTorles
        if self.checkTorles.isChecked():
            self.pushCsomagtorles.setEnabled(True)
        else:
            self.pushCsomagtorles.setEnabled(False)

    @pyqtSignature("")
    def on_pushCsomagtorles_clicked(self):
        ppont_deleted = 0

        if not self.keszito is None:

            qDeletePponts = QtSql.QSqlQuery()
            siker = qDeletePponts.exec_(
                """DELETE FROM ppont WHERE csomag_azon = 
                (SELECT csomag_azon FROM csomag WHERE csomag_azon = %s AND allapot = False AND keszito = '%s') RETURNING ppont_azon;"""
                % (str(self.selCsomagAzon), self.keszito))
            if siker:
                if qDeletePponts.size() > 0:
                    ppont_deleted = qDeletePponts.size()
                else:
                    QtGui.QMessageBox.warning(None, u"Csomagtörlés", u"Nem törölhető a csomaghoz kapcsolódó P-pont.")
                    return
            else:
                if qDeletePponts.lastError().type() != 0:
                    QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(qDeletePponts.lastError().text()))
                    return

            qDeleteCsomag = QtSql.QSqlQuery()
            siker = qDeleteCsomag.exec_(
                """DELETE FROM csomag WHERE csomag_azon = %s AND allapot = False  AND keszito = '%s' RETURNING csomag_nev;""" % (str(self.selCsomagAzon), self.keszito))
            if siker:
                if qDeleteCsomag.size() == 1:
                    qDeleteCsomag.next()
                    QtGui.QMessageBox.warning(None, u"Csomagtörlés", u"Sikeres csomagtörlés: %s. Törölt pontok száma: %s" % (qDeleteCsomag.value(0), str(ppont_deleted)))
                    self.selCsomagNev = None
                    self.selCsomagAzon = None
                    self.lineSelCsomag.setText('')
                    self.checkTorles.setChecked(False)
                    ppont_deleted = 0
                    self.refresh_layers()
                    return
                else:
                    QtGui.QMessageBox.warning(None, u"Csomagtörlés", u"Nem történt csomagtörlés. Törölt pontok száma: %s" % str(ppont_deleted))
                    return
            else:
                if qDeleteCsomag.lastError().type() != 0:
                    QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(qDeleteCsomag.lastError().text()))
                    return
        else:
            QtGui.QMessageBox.warning(None, u"Csomagtörlés", u"Nincs bejelentkezett Csomagkészítő!")

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

class LoginDialog(QtGui.QDialog, LOGIN_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(LoginDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        """Adatbázis elérési adatok"""
        self.lblFeladat.setText(u"Csomagkészítő bejelentkezés")
        self.comboKiszolgalo.addItem("157.181.228.182")
        self.comboKiszolgalo.addItem("217.65.117.190")
        self.comboKiszolgalo.addItem("localhost")
        self.comboPort.addItem("5432")
        self.comboPort.addItem("5433")
        self.comboDB.addItem(u"shteszt")
        self.comboDB.addItem(u"csomagkezeles")
        self.uiFelhasznalo.setText("")
        self.uiJelszo.setText("")
        self.csomagkeszito = None
        self.mintateruletek = []

    @pyqtSignature("")
    def on_buttonOk_clicked(self):

        global csomadmin
        csomadmin = unicode(self.uiFelhasznalo.text())

        db.setUserName(unicode(self.uiFelhasznalo.text()))
        db.setPassword(unicode(self.uiJelszo.text()))
        db.setHostName(unicode(self.comboKiszolgalo.currentText()))
        db.setPort(int(self.comboPort.currentText()))
        db.setDatabaseName(unicode(self.comboDB.currentText()))

        self.csomagkeszito = None

        if not db.open():
            QtGui.QMessageBox.warning(None, u"Bejelentkezés","DatabaseError: %s" % db.lastError().text())
        else:
            ervenyesseg = self.checkEllenor()
            if ervenyesseg:
                self.csomagkeszito = self.uiFelhasznalo.text()
                self.accept()
            else:
                QtGui.QMessageBox.warning(None, u"Csomagkiosztás", u"Nincs mintaterület rendelve a szerepkörhöz.")

    def checkEllenor(self):

        queryEllenor = QtSql.QSqlQuery()
        siker = queryEllenor.exec_("""SELECT projminter FROM szereposztas 
                        WHERE szerep in (SELECT szerep FROM szerep WHERE csomagoszto = True)
                        AND aktiv = True AND szemely = '%s';""" % csomadmin)
        if siker:
            if  queryEllenor.size() == 0:
                return False
            elif queryEllenor.size() > 0:
                while queryEllenor.next():
                    ujMinta = [queryEllenor.value(0)]
                    self.mintateruletek.extend(ujMinta)
                return True
        else:
            if queryEllenor.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, "Hiba:", "Hiba típus: %s" % str(queryEllenor.lastError().text()))
                return

    def on_buttonElvet_clicked(self):
        self.close()