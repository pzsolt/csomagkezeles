#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import zipfile
import hashlib
from xml.dom.minidom import Document
from datetime import datetime
from time import sleep
import gpxpy
import gpxpy.gpx
import os
from sys import platform
from PyQt4 import QtGui, QtSql


def csomag_zip(filename, felmero, genfolder):
    """A csomag tömörítését végző függvénye"""
    with zipfile.ZipFile(genfolder + '/' + felmero + '/' + filename + '.zip', mode='w') as zf:
        zf.write(genfolder + '/' + felmero + '/' + filename + '.db', filename + '/' + filename +'.db' )
    return True

def csomag_md5(zipname):
    """A tömörített csomag md5 kódjának előállítását végző függvény"""
    with open(zipname, 'rb') as file_to_check:
        # read contents of the file
        data = file_to_check.read()
        # pipe contents of the file through
        md5_returned = hashlib.md5(data).hexdigest()
        return str(md5_returned)

def csomag_XML_elem(cs_felm, cs_azon, cs_nev, cs_pontsz, cs_gen, cs_hat, cs_tom, cs_MD5, genfolder):
    """ XML minidom-document létrehozása a csomag adataival és a csomag_log rekord kezelése"""
    doc = Document()

    # csomag elem létrehozása
    csomag = doc.createElement('csomag')
    csomag.setAttribute("azonosito", '%s' % str(cs_azon))
    csomag.setAttribute("nev", '%s' % cs_nev)
    csomag.setAttribute("pontszam", '%s' % str(cs_pontsz))
    doc.appendChild(csomag)

    # a csomag gyermek elemeinek létrehozása
    generalas = doc.createElement('generalas')
    generalas_tartalom = doc.createTextNode('%s' % cs_gen)
    generalas.appendChild(generalas_tartalom)
    csomag.appendChild(generalas)

    hatarido = doc.createElement('hatarido')
    hatarido_tartalom = doc.createTextNode('%s' % cs_hat)
    hatarido.appendChild(hatarido_tartalom)
    csomag.appendChild(hatarido)

    muvelet = doc.createElement('muvelet')
    csomag.appendChild(muvelet)

    hash = doc.createElement('hash')
    csomag.appendChild(hash)

    # a művelet gyermek elemeinek létrehozása
    tomorites = doc.createElement('tomorites')
    tomorites_tartalom = doc.createTextNode('%s' % cs_tom)
    tomorites.appendChild(tomorites_tartalom)
    muvelet.appendChild(tomorites)

    # a művelet gyermek elemeinek létrehozása
    md5szerver = doc.createElement('MD5_szerver')
    md5szerver_tartalom = doc.createTextNode('%s' % cs_MD5)
    md5szerver.appendChild(md5szerver_tartalom)
    hash.appendChild(md5szerver)

    fname = genfolder + '/' + cs_felm + '/' + cs_nev + '.xml'
    # XML kiírása
    doc.writexml(open(fname, 'w'), indent="  ", addindent="  ", newl='\n')
    doc.unlink()

    if os.path.isfile(fname):
        queryLogId = QtSql.QSqlQuery()
        siker = queryLogId.exec_('''SELECT package_id FROM csomag_log WHERE csomag_azon = %s;''' % (cs_azon))
        if siker:
            if queryLogId.size() == 1:
                queryLogId.next()
                return queryLogId.value(0), 2
            elif queryLogId.size() > 1:
                QtGui.QMessageBox.warning(None, u"Csomag-log", u"Csomag-log rekord lekérdezési hiba.")
                return 0, 0
        else:
            if queryLogId.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, u"Hiba:", u"Hiba típus: %s" % str(queryLogId.lastError().text()))
                return 0, 0

        queryLog = QtSql.QSqlQuery()
        siker = queryLog.exec_(
            '''INSERT INTO csomag_log(felmero,csomag_azon,csomag_nev,cs_pontszam,cs_generalas,cs_hatarido,m_tomorites,hash_md5_szerver) 
            VALUES('%s',%s,'%s',%s,'%s','%s','%s','%s') RETURNING package_id ;''' % (cs_felm, cs_azon, cs_nev, cs_pontsz, cs_gen, cs_hat, cs_tom, cs_MD5))
        if siker:
            if queryLog.size() == 1:
                queryLog.next()
                return queryLog.value(0), 1
            else:
                QtGui.QMessageBox.warning(None, u"Csomag-log", u"Csomag-log rekord rögzítési hiba.")
                return 0, 0

        else:
            if queryLog.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, u"Hiba:", u"Hiba típus: %s" % str(queryLog.lastError().text()))
                return 0, 0

    else:
        print "No XML - No PackMan!"
        return 0, 0

def generator(csomazon, genfolder, keszito):
    # postgresql connection
    try:
        # csomag adatok lekérdezése
        prow = []
        queryGenerate = QtSql.QSqlQuery()
        siker = queryGenerate.exec_("""SELECT csomag_azon,csomag_nev,mintater,projminter,felmero,hatarido,sorok,oszlopok,letrehozas,
                formverzio,oscsomag FROM csomag WHERE csomag_azon = %s""" % (csomazon))
        if siker:
            if queryGenerate.size() == 1:
                queryGenerate.next()
                for i in range(11):
                    prow.append(queryGenerate.value(i))
            else:
                QtGui.QMessageBox.warning(None, u"File Generálás", u"Hiányzó csomag rekord.")
                return
        else:
            if queryGenerate.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, u"Hiba:", u"Hiba típus: %s" % str(queryGenerate.lastError().text()))
                return

        print prow
        forward = True
        pontx = 0

        sql_list = []
        queryCreates = QtSql.QSqlQuery()
        crQuery = """SELECT table_sql FROM csomag_sql WHERE %s= True""" % (prow[9].strip())
        siker = queryCreates.exec_(crQuery)
        if siker:
            while queryCreates.next():
                sql_list.append(queryCreates.value(0))
        else:
            if queryCreates.lastError().type() != 0:
                QtGui.QMessageBox.warning(None, u"Hiba:", u"Hiba típus: %s" % str(queryCreates.lastError().text()))
                return
        if not len(sql_list): return

        try:
            # felhasználó könyvtárának létrehozása a megadott elérési út alatt - ha még nincs
            if not os.path.exists(genfolder + '/' + prow[4]):
                print 'Create package folder:', os.path.exists(genfolder + '/' + prow[4])
                os.makedirs(genfolder + '/' + prow[4])

            # az SQLite adatbázis létrehozása, és kapcsolódás hozzá
            sdb = sqlite3.connect(genfolder + '/' + prow[4] + '/' + prow[1] + '.db')
            # sqlite táblák létrehozásának ciklusa
            for sql_rec in sql_list:
                scur = sdb.cursor()
                scur.execute(sql_rec)
                sdb.commit()

            # csomag rekord beszúrása
            prowselect = (prow[0], prow[1], prow[3], prow[4], prow[5].toString('yyyy-MM-dd hh:mm:ss'), prow[6], prow[7], prow[9].strip())
            print prowselect
            csrec = sdb.cursor()
            csrec.execute(
                'INSERT INTO csomag(csomag_id,csom_nev,mintater,felmero,hatarido,sor,oszlop,formverzio) VALUES(?,?,?,?,?,?,?,?)',
                prowselect)
            sdb.commit()

            # gpx változó létrehozása
            gpx = gpxpy.gpx.GPX()

            # ppont rekordok lekérdezése
            pponts = []
            queryPRec = QtSql.QSqlQuery()
            siker = queryPRec.exec_("""SELECT ppont_azon,csomag_azon,epont_azon,bpont_azon,sorszam,sor,oszlop,wgs84_lat,wgs84_lon,statusz 
                    FROM ppont WHERE csomag_azon=%s""" % (prow[0]))
            if siker:
                while queryPRec.next():
                    prec = []
                    for i in range(10):
                        prec.append(queryPRec.value(i))
                    pponts.append(prec)
            pontx = len(pponts)

            for ppont in pponts:
                # insert ppont records
                print ppont
                scur = sdb.cursor()
                if ppont[9] == 0:
                    # ha uj csomagról van szó
                    scur.execute('''INSERT INTO ppont(ppont_id,csomag_id,epont_id,bpont_id,sorszam,sor,oszlop,
                    wgs84_lat,wgs84_lon,statusz) VALUES(?,?,?,?,?,?,?,?,?,1)''', (
                        ppont[0], ppont[1], ppont[2], ppont[3], ppont[4], ppont[5], ppont[6], ppont[7], ppont[8]))
                else:
                    # ha hibajavító csomagról van szó
                    scur.execute('''INSERT INTO ppont(ppont_id,csomag_id,epont_id,bpont_id,sorszam,sor,oszlop,
                    wgs84_lat,wgs84_lon,statusz) VALUES(?,?,?,?,?,?,?,?,?,?)''', ppont)

                sdb.commit()

                # GPX waypoint beszúrások a gpx változóba
                gpx_wpt = gpxpy.gpx.GPXWaypoint(ppont[7], ppont[8], name=str(ppont[4]), symbol='Navaid, Orange')
                gpx.waypoints.append(gpx_wpt)

            # gpx fájl létrehozása és lezárása
            gpxfilename = genfolder + '/' + prow[4] + '/' + prow[1] + '.gpx'
            gpxfile = open(gpxfilename, 'a')
            gpxfile.write(gpx.to_xml())
            gpxfile.close()

            # a Garmin gpi fájl létrehozása GPSBabel program segítségével
            gpifilename = genfolder + '/' + prow[4] + '/' + prow[1] + '.gpi'
            pluginfolder = os.path.dirname(os.path.abspath(__file__))
            babelparancs = ''
            if platform == "linux" or platform == "linux2" or platform == "darwin":
                # linux and OS X
                babelparancs = 'gpsbabel -w -i gpx -f ' + gpxfilename + ' -o garmin_gpi,category=' + prow[1][:6] \
                    + prow[1][8:] + ',bitmap="' + pluginfolder + '/pont.bmp",unique=1 -F ' + gpifilename

            elif platform == "win32":
                # Windows...
                babelparancs = 'gpsbabel -w -i gpx -f ' + gpxfilename + ' -o garmin_gpi,category=' + prow[1][:6] \
                    + prow[1][8:] + ',bitmap="' + pluginfolder.replace('\\','/') + '/pont.bmp",unique=1 -F ' + gpifilename
                #   + prow[1][8:] + ",bitmap=d:/dev/pycharm_projects/scriptek/pont.bmp,unique=1 -F " + gpifilename
            else:
                QtGui.QMessageBox.warning(None, u"Hiba:", u"Operációs rendszer függési hiba: %s" % platform)
            if babelparancs:
                print babelparancs
                babelproc = os.system(babelparancs)
                print babelproc
                sleep(2)

        except sqlite3.Error as e:
            QtGui.QMessageBox.warning(None, u"Hiba:", u"Adatbázis hiba: %s" % e)
            forward = False

        except Exception as e:
            QtGui.QMessageBox.warning(None, u"Hiba:", u"Adatbázis lekérdezés hiba: %s" % e)
            forward = False

        finally:
            if sdb:
                sdb.close()

        if forward:
            # ha az eddigi műveletek sikeresen lezajlottak
            fname = genfolder + '/' + prow[4] + '/' + prow[1] + '.db'
            if os.path.isfile(fname):
                # adatbázis ZIP zömörítés
                zip_ok = csomag_zip(prow[1], prow[4], genfolder)
                md5_returned = None
                if zip_ok:
                    # MD5 value generálás
                    md5_returned = csomag_md5(genfolder + '/' + prow[4] + '/' + prow[1] + '.zip')

                if md5_returned is not None:
                    tom_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # csomag XML element létrehozása, letárolása
                    # csomag_azon,csomag_nev,mintater,projminter,felmero,hatarido,sorok,oszlopok,letrehozas,formverzio,oscsomag
                    # (cs_felm,  cs_azon, cs_nev, cs_pontsz, cs_gen, cs_hat, cs_tom, cs_MD5)
                    logazon, logrend = csomag_XML_elem(prow[4], prow[0], prow[1], pontx, prow[8].toString('yyyy-MM-dd hh:mm:ss'), prow[5].toString('yyyy-MM-dd hh:mm:ss'), tom_time, md5_returned, genfolder)

                    if logazon:
                        # ha első alkalommal törénik a generálás
                        if logrend == 1:
                            # a csomag rekord állapotának megváltoztatása a Postgresql-ben
                            queryCsomStatus = QtSql.QSqlQuery()
                            siker = queryCsomStatus.exec_("""UPDATE csomag SET allapot = True WHERE csomag_azon = %s""" % (prow[0]))
                            if siker:
                                print 'Package state = True'
                            else:
                                if queryCsomStatus.lastError().type() != 0:
                                    QtGui.QMessageBox.warning(None, u"Hiba:",
                                                              u"Hiba típus: %s" % str(queryCsomStatus.lastError().text()))
                                    return

                            # a ppont rekordok státuszának megváltoztatása a Postgresql-ben
                            queryPontStatus = QtSql.QSqlQuery()
                            siker = queryPontStatus.exec_("""UPDATE ppont SET statusz = 1 WHERE csomag_azon = %s""" % (prow[0]))
                            if siker:
                                print 'Pponts state: 1'
                            else:
                                if queryPontStatus.lastError().type() != 0:
                                    QtGui.QMessageBox.warning(None, u"Hiba:",
                                                              u"Hiba típus: %s" % str(queryPontStatus.lastError().text()))
                                    return

                        # a fájlgenerálás bejegyzése a csomag_gen táblába
                        queryGenLog = QtSql.QSqlQuery()
                        siker = queryGenLog.exec_(
                            '''INSERT INTO csomag_gen(package_id,csomag_nev,file_generalas,gen_mod,gen_rend,kezdemenyezo) 
                            VALUES(%s,'%s','%s','manual',%s,'%s') RETURNING gen_id ;''' % (logazon, prow[1], tom_time, logrend, keszito))
                        if siker:
                            if queryGenLog.size() == 1:
                                queryGenLog.next()
                                print 'gen_id:', queryGenLog.value(0), 'package_id:', logazon
                            else:
                                QtGui.QMessageBox.warning(None, u"Csomag-gen", u"Csomag generálás rekord rögzítési hiba.")
                                return
                        else:
                            if queryGenLog.lastError().type() != 0:
                                QtGui.QMessageBox.warning(None, u"Hiba:", u"Hiba típus: %s" % str(queryGenLog.lastError().text()))
                                return

                    else:
                        # a fájlok törlése építhető be ide, ha sikertelen volt a csomag_log rekord kezelése
                        pass
                else:
                    QtGui.QMessageBox.warning(None, u"Hiba:", u"MD5 generálás hiba")
                    return

            QtGui.QMessageBox.warning(None, u"Csomag generálás", u"Létrehozásra kerültek a csomag fájljai")
            return

        QtGui.QMessageBox.warning(None, u"Csomag generálás hiba", u"A fájlok generálása elakadt.")
        return

    except Exception as e:
        QtGui.QMessageBox.warning(None, u"Hiba:", u"Generálás hiba: %s" % e)