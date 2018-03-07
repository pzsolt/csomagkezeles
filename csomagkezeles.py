# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Csomagkezeles
                                 A QGIS plugin
 Erdőfelmérések terepi munkáinak kiosztása
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from csomagkezeles_dockwidget import CsomagkezelesDockWidget
import os.path


class Csomagkezeles:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):

        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir,'i18n','Csomagkezeles_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = u'&Csomagkezelés'
        self.toolbar = self.iface.addToolBar(u'Csomagkezeles')
        self.toolbar.setObjectName(u'Csomagkezeles')

        self.pluginIsActive = False

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=False,
        status_tip=None,
        whats_this=None,
        parent=None):

        self.dockwidget = CsomagkezelesDockWidget()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Csomagkezeles/icon.png'
        self.add_action(
            icon_path,
            text=u'Csomagkezelés',
            callback=self.run,
            parent=self.iface.mainWindow())
        self.iface.mapCanvas().layersChanged.connect(self.epontLayer)
        self.iface.mapCanvas().selectionChanged.connect(self.onSelectionChanged)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(u'&Csomagkezeles', action)


    def run(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget == None:
                self.dockwidget = CsomagkezelesDockWidget()

            self.dockwidget.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            self.dockwidget.epontLayer()

    def onSelectionChanged(self, layer):
        if self.pluginIsActive and self.dockwidget != None:
            self.dockwidget.onSelectionChanged(layer)

    def epontLayer(self):
        if self.pluginIsActive and self.dockwidget != None:
            layers = self.iface.legendInterface().layers()
            self.dockwidget.epontLayer(layers)