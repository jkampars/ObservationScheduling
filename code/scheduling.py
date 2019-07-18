# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, Angle
from astropy.time import Time
from astropy.utils import iers
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from astroplan import Observer, FixedTarget, ObservingBlock
from astroplan.constraints import AltitudeConstraint
from astroplan.scheduling import Transitioner, Schedule, SequentialScheduler
from astroplan.plots import  plot_schedule_altitude, plot_altitude, plot_schedule_sky, plot_sky
from dateutil.parser import parse
from astroplan import is_always_observable, download_IERS_A
from collections import OrderedDict
from PyQt5.QtWidgets import QApplication, QWidget, QFormLayout, QGridLayout, QGroupBox, QLineEdit, QLabel, QPushButton, QComboBox, QMessageBox, QListWidget, QListWidgetItem, QCheckBox, QVBoxLayout, QHBoxLayout, QRadioButton
from PyQt5.QtCore import Qt
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from observation import Observation
from plannedObs import PlannedObs
from googlecalendar import get_next_week_events, get_all_events
from plot_qt5 import Plot

import re
import os
import json
import configparser
import datetime
import csv
import faulthandler
faulthandler.enable(all_threads=True)


def main():
    app = QApplication([])
    gui = GUI()
    gui.show()
    app.exec_()



def insert (source_str, insert_str, pos):
    return source_str[:pos]+insert_str+source_str[pos:]

class GUI(QWidget):
    def __init__(self):
        super().__init__()

        try:
            urlopen('http://maia.usno.navy.mil/ser7/finals2000A.all')
        except HTTPError as e:
            print("Main IERS link not working, using mirror")
            iers.conf.iers_auto_url = 'http://toshi.nofs.navy.mil/ser7/finals2000A.all'
        except URLError as e:
            print("Main IERS link not working, using mirror")
            iers.conf.iers_auto_url = 'http://toshi.nofs.navy.mil/ser7/finals2000A.all'

        #download_IERS_A()

        plt.style.use(astropy_mpl_style)

        irbeneLocation = EarthLocation(lat=57.5535171694 * u.deg, lon=21.8545525000 * u.deg, height=87.30 * u.m)
        self.irbene = Observer(location=irbeneLocation, name="Irbene", timezone="Europe/Riga")

        observe_time = Time(['2019-02-05 15:30:00'])

        self.targets = []
        self.targetsDict = {}
        with open("config/config.csv", "r") as csvfile:
            next(csvfile)
            reader = csv.reader(csvfile, delimiter=",", quotechar="|")
            for row in reader:
                sourceName = row[0]

                raText = row[1]
                raText = insert(raText, 'h', 2)
                raText = insert(raText, 'm', 5)
                raText = insert(raText, 's', len(raText))

                decText = row[2]
                if (decText[0] != "-"):
                    decText = insert(decText, 'd', 2)
                    decText = insert(decText, 'm', 5)
                    decText = insert(decText, 's', len(decText))
                else:
                    decText = insert(decText, 'd', 3)
                    decText = insert(decText, 'm', 6)
                    decText = insert(decText, 's', len(decText))

                ra = Angle(raText)
                dec = Angle(decText)

                targetCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                target = FixedTarget(coord=targetCoord, name=sourceName)
                plannedObs = PlannedObs(target, int(row[4]), int(row[3]), int(row[5]))
                self.targets.append(plannedObs)  # target / obs per_week / priority / scans per obs
                coords = {"ra": ra, "dec": dec}
                self.targetsDict[sourceName] = coords

        self.targets = sorted(self.targets, key=lambda x: x.priority)  # sort targets by priority
        self.calibrators = []
        self.calibratorsDict = {}
        with open("config/calibrators.csv", "r") as csvfile:
            next(csvfile)
            reader = csv.reader(csvfile, delimiter=";", quotechar="|")
            for row in reader:
                sourceName = row[0]

                raText = str(row[1]).replace(" ", "")
                raText = insert(raText, 'h', 2)
                raText = insert(raText, 'm', 5)
                raText = insert(raText, 's', len(raText))

                decText = str(row[2]).replace(" ", "")
                if (decText[0] != "-"):
                    decText = insert(decText, 'd', 3)
                    decText = insert(decText, 'm', 6)
                    decText = insert(decText, 's', len(decText))
                else:
                    decText = insert(decText, 'd', 3)
                    decText = insert(decText, 'm', 6)
                    decText = insert(decText, 's', len(decText))

                ra = Angle(raText)
                dec = Angle(decText)

                coords = {"ra": ra, "dec": dec}
                self.calibratorsDict[sourceName] = coords
                calibratorCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                calibrator = FixedTarget(coord=calibratorCoord, name=sourceName)
                self.calibrators.append(calibrator)

        startArray, endArray, summaryArray = get_all_events()
        self.dateList = QListWidget()

        tempCheck = True
        for i in range(len(startArray)):
            dayStart = parse(startArray[i])
            dayEnd = parse(endArray[i])
            daySummary = summaryArray[i]
            daySummary = daySummary + " " + str(dayStart.date()) + " " + str(dayStart.time()) + "-" + str(dayEnd.time())
            item = QListWidgetItem(daySummary, self.dateList)
            item.setData(Qt.UserRole, [dayStart, dayEnd])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            if tempCheck and "maser" in daySummary:
                item.setCheckState(Qt.Checked)
                tempCheck = False
            self.dateList.addItem(item)

        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.config = config._sections['Default']
        self.config['calibration'] = config['Default'].getboolean('calibration')
        #print(config['Default']['obsSplitLength'])

        self.layout = QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        self.resize(1000, 600)



        self.dateBoxList = []
        self.targetTimesCount = 0
        self.load_ui()

    def load_ui(self):
        self.observationList = QListWidget()
        self.plannedTargets = []
        for target in self.targets[:10]:
            item = QListWidgetItem(str(target), self.observationList)
            item.setData(Qt.UserRole, target)
            self.observationList.addItem(item)
            self.plannedTargets.append(target.name)

        self.layout.addWidget(self.observationList, 0, 0, 10, 2)

        self.observationList.itemSelectionChanged.connect(self.obsChanged)

        for index in range(self.observationList.count()):
            item = self.observationList.item(index)

        self.targetLayout = QVBoxLayout()
        targetBox = QGroupBox()
        targetBox.setMaximumSize(350, 250)

        line = QHBoxLayout()
        nameLabel = QLabel("Target:")
        self.nameBox = QLineEdit()
        self.nameBox.setEnabled(False)
        nameLabel.setParent(targetBox)
        self.nameBox.setParent(targetBox)
        line.addWidget(nameLabel)
        line.addWidget(self.nameBox)
        self.targetLayout.addLayout(line)

        line = QHBoxLayout()
        priorityLabel = QLabel("Priority:")
        self.priorityBox = QLineEdit()
        priorityLabel.setParent(targetBox)
        self.priorityBox.setParent(targetBox)
        line.addWidget(priorityLabel)
        line.addWidget(self.priorityBox)
        self.targetLayout.addLayout(line)

        line = QHBoxLayout()
        obsLabel = QLabel("Obs per week:")
        self.obsBox = QLineEdit()
        obsLabel.setParent(targetBox)
        self.obsBox.setParent(targetBox)
        line.addWidget(obsLabel)
        line.addWidget(self.obsBox)
        self.targetLayout.addLayout(line)

        line = QHBoxLayout()
        scanLabel = QLabel("Scans per obs:")
        self.scanBox = QLineEdit()
        scanLabel.setParent(targetBox)
        self.scanBox.setParent(targetBox)
        line.addWidget(scanLabel)
        line.addWidget(self.scanBox)
        self.targetLayout.addLayout(line)


        line = QHBoxLayout()
        specificLabel = QLabel("Specific times:")
        addTime = QPushButton("Add specific time")
        addTime.clicked.connect(self.add_time)
        line.addWidget(specificLabel)
        line.addWidget(addTime)
        self.targetLayout.addLayout(line)


        saveButton = QPushButton("Save changes")
        saveButton.clicked.connect(self.save_obs_changes)
        self.targetLayout.addWidget(saveButton)

        removeButton = QPushButton("Remove target")
        removeButton.clicked.connect(self.remove_obs)
        self.targetLayout.addWidget(removeButton)

        targetBox.setLayout(self.targetLayout)
        self.layout.addWidget(targetBox, 0, 2, 2, 1)

        self.targetComboBox = QComboBox()
        for key in self.targetsDict:
            if key not in self.plannedTargets:
                self.targetComboBox.addItem(key)
        self.layout.addWidget(self.targetComboBox, 2, 2)

        addButton = QPushButton("Add observation")
        addButton.clicked.connect(self.add_obs)
        self.layout.addWidget(addButton, 3, 2)

        nextButton = QPushButton("Schedule")
        nextButton.clicked.connect(self.prepare_schedule)
        self.layout.addWidget(nextButton, 0, 3)
        datesButton = QPushButton("Dates")
        datesButton.clicked.connect(self.edit_dates)
        self.layout.addWidget(datesButton, 1, 3)
        targetsButton = QPushButton("Targets")
        targetsButton.clicked.connect(self.edit_targets)
        self.layout.addWidget(targetsButton, 2, 3)
        calibratorsButton = QPushButton("Calibrators")
        calibratorsButton.clicked.connect(self.edit_calibrators)
        self.layout.addWidget(calibratorsButton, 3, 3)
        settingsButton = QPushButton("Settings")
        settingsButton.clicked.connect(self.load_settings)
        self.layout.addWidget(settingsButton, 4, 3)

    def add_time(self):
        datesChecked = 0
        for index in range(self.dateList.count()):
            if self.dateList.item(index).checkState() == Qt.Checked:
                datesChecked = datesChecked + 1
        if datesChecked > self.targetTimesCount:
            line = QHBoxLayout()
            dateBox = QComboBox()
            for index in range(self.dateList.count()):
                if self.dateList.item(index).checkState() == Qt.Checked:
                    dateBox.addItem(self.dateList.item(index).text(), self.dateList.item(index).data(Qt.UserRole))
            dateBox.addItem("Remove")
            dateBox.currentTextChanged.connect(self.timeChanged)
            self.targetTimesCount+= 1
            dateBox.sizePolicy().setHorizontalStretch(1)
            timeBox = QLineEdit()
            timeBox.sizePolicy().setHorizontalStretch(3)
            line.addWidget(dateBox)
            line.addWidget(timeBox)
            self.dateBoxList.append(line)
            self.targetLayout.insertLayout(self.targetLayout.count()-2, line)
        else:
            self.show_error("Date error", "Can't select more times than selected dates")

    def timeChanged(self, item):
        if item == "Remove":
            for line in self.dateBoxList:
                if line is not None:
                    item = line.itemAt(0)
                    widget = item.widget()
                    if type(widget) == type(QComboBox()):
                        if widget.currentText() == "Remove":
                            break
            self.targetTimesCount -= 1
            widget.disconnect()
            self.deleteItemsOfLayout(line)
            self.targetLayout.removeItem(line)
            self.dateBoxList.remove(line)


    def obsChanged(self):
        if len(self.observationList.selectedItems()) > 0:
            item = self.observationList.currentItem()
            plannedObs = item.data(Qt.UserRole)
            self.nameBox.setText(plannedObs.name)
            self.priorityBox.setText(str(plannedObs.priority))
            self.obsBox.setText(str(plannedObs.obs_per_week))
            self.scanBox.setText(str(plannedObs.scans_per_obs))
            i = 0
            maxi = self.targetLayout.count()
            while(i < maxi):
                layout_item = self.targetLayout.itemAt(i)
                if layout_item in self.dateBoxList:
                    self.deleteItemsOfLayout(layout_item.layout())
                    self.targetLayout.removeItem(layout_item)
                    self.dateBoxList.remove(layout_item)
                    maxi = self.targetLayout.count()
                    i = i -1
                i=i+1
            self.targetTimesCount = 0
            if plannedObs.times:
                checkedDates = []
                for index in range(self.dateList.count()):
                    if self.dateList.item(index).checkState() == Qt.Checked:
                        checkedDates.append(self.dateList.item(index).text())
                for time in list(plannedObs.times):
                    if time not in checkedDates:
                        self.show_error("Date mismatch", "Date "+time+" is not checked, removing it")
                        #plannedObs.times.remove(time)
                for time in list(plannedObs.times):
                    line = QHBoxLayout()
                    dateBox = QComboBox()
                    for index in range(self.dateList.count()):
                        if self.dateList.item(index).checkState() == Qt.Checked:
                            dateBox.addItem(self.dateList.item(index).text(), self.dateList.item(index).data(Qt.UserRole))
                    dateBox.addItem("Remove")
                    dateBox.currentTextChanged.connect(self.timeChanged)
                    self.targetTimesCount += 1
                    dateBox.sizePolicy().setHorizontalStretch(1)
                    timeBox = QLineEdit(plannedObs.times[time])
                    timeBox.sizePolicy().setHorizontalStretch(3)
                    line.addWidget(dateBox)
                    line.addWidget(timeBox)
                    self.dateBoxList.append(line)
                    self.targetLayout.insertLayout(self.targetLayout.count() - 2, line)
                    dateBox.setCurrentIndex(dateBox.findText(time))

        else:
            self.nameBox.setText("")
            self.priorityBox.setText("")
            self.obsBox.setText("")
            self.scanBox.setText("")
            self.targetTimesCount = 0

    def remove_obs(self):
        if len(self.observationList.selectedItems()) > 0:
            self.plannedTargets.remove(self.observationList.currentItem().data(Qt.UserRole).name)
            self.targetComboBox.addItem(self.observationList.currentItem().data(Qt.UserRole).name)
            self.observationList.takeItem(self.observationList.currentRow())
        else:
            self.show_error("Observation error","Select an observation to remove it")


    def save_obs_changes(self):
        if not self.priorityBox.text().isdigit():
            self.show_error("Priority error", "Priority must be from 1 to 4")
        elif int(self.priorityBox.text()) > 4 or int(self.priorityBox.text()) < 0:
            self.show_error("Priority error", "Priority must be from 1 to 4")
        elif not self.obsBox.text().isdigit():
            self.show_error("Obs error", "Obs must be from 1 to 7")
        elif int(self.obsBox.text()) > 7 or int(self.obsBox.text()) < 0:
            self.show_error("Obs error", "Obs must be from 1 to 7")
        elif not self.scanBox.text().isdigit():
            self.show_error("Scan error", "Scan must be from 1 to 120")
        elif int(self.scanBox.text()) > 120 or int(self.scanBox.text()) < 0:
            self.show_error("Scan error", "Scan must be from 1 to 120")
        elif len(self.dateBoxList) != len(set(self.dateBoxList)):
            self.show_error("Date error", "Make sure specified times don't use same dates")
        else:
            self.observationList.currentItem().data(Qt.UserRole).priority = int(self.priorityBox.text())
            self.observationList.currentItem().data(Qt.UserRole).obs_per_week = int(self.obsBox.text())
            self.observationList.currentItem().data(Qt.UserRole).scans_per_obs = int(self.scanBox.text())
            self.observationList.currentItem().setText(str(self.observationList.currentItem().data(Qt.UserRole)))
            times = {}
            for line in self.dateBoxList:
                item = line.itemAt(0)
                widget = item.widget()
                date = widget.currentText()

                times[date] = line.itemAt(1).widget().text()

            self.observationList.currentItem().data(Qt.UserRole).times = times

    def add_obs(self):
        if self.targetComboBox.count() > 0:
            targetName = self.targetComboBox.currentText()
            ra = self.targetsDict[targetName]["ra"]
            dec = self.targetsDict[targetName]["dec"]
            coord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
            target = FixedTarget(coord=coord, name=targetName)
            data = PlannedObs(target, 1, 1, 1)
            item = QListWidgetItem(str(data), self.observationList)
            item.setData(Qt.UserRole, data)
            self.observationList.addItem(item)
            self.plannedTargets.append(data.name)
            self.targetComboBox.removeItem(self.targetComboBox.currentIndex())

    def edit_dates(self):
        self.clear_window()
        self.layout.addWidget(self.dateList, 0, 0, 5, 2)
        backButton = QPushButton("Back to planner")
        self.layout.addWidget(backButton, 1, 2)
        backButton.clicked.connect(self.to_start)

    def edit_targets(self):
        self.clear_window()

        self.targetList = QListWidget()
        for key in self.targetsDict:
            self.targetList.addItem(key)
        self.targetList.itemClicked.connect(self.targetChanged)
        self.layout.addWidget(self.targetList, 0, 0, 3, 1)

        targetLayout = QGridLayout()
        targetLayout.addWidget(QLabel("Ra:"), 0, 0)
        self.raBox = QLineEdit()
        targetLayout.addWidget(self.raBox, 0, 1)
        targetLayout.addWidget(QLabel("Dec:"), 1, 0)
        self.decBox = QLineEdit()
        targetLayout.addWidget(self.decBox, 1, 1)
        self.saveButton = QPushButton("Save changes")
        self.saveButton.clicked.connect(self.save_target_changes)
        targetLayout.addWidget(self.saveButton, 2, 0, 1, 2)
        targetBox = QGroupBox()
        targetBox.setLayout(targetLayout)
        self.layout.addWidget(targetBox, 0, 1)
        self.saveButton.setEnabled(False)

        addTargetLayout = QGridLayout()
        addTargetLayout.addWidget(QLabel("Name:"), 0, 0)
        self.addNameBox = QLineEdit()
        addTargetLayout.addWidget(self.addNameBox, 0, 1)

        addTargetLayout.addWidget(QLabel("Ra:"), 1, 0)
        self.addRaBox = QLineEdit()
        addTargetLayout.addWidget(self.addRaBox, 1, 1)

        addTargetLayout.addWidget(QLabel("Dec:"), 2, 0)
        self.addDecBox = QLineEdit()
        addTargetLayout.addWidget(self.addDecBox, 2, 1)

        self.addSaveButton = QPushButton("Save changes")
        self.addSaveButton.clicked.connect(self.add_target)
        addTargetLayout.addWidget(self.addSaveButton, 3, 0, 1, 2)

        addTargetBox = QGroupBox()
        addTargetBox.setLayout(addTargetLayout)
        self.layout.addWidget(addTargetBox, 1, 1)

        backButton = QPushButton("Back to planner")
        self.layout.addWidget(backButton, 0, 3)
        backButton.clicked.connect(self.to_start)

    def targetChanged(self, item):
        if not self.saveButton.isEnabled():
            self.saveButton.setEnabled(True)
        targetName = item.text()
        target = self.targetsDict[targetName]
        self.raBox.setText(target["ra"].to_string())
        self.decBox.setText(target["dec"].to_string(unit=u.degree))

    def save_target_changes(self):
        if len(self.targetList.selectedItems()) != 1:
            self.show_error("Target error", "Make sure you have selected only 1 target")
        else:
            targetName = self.targetList.selectedItems()[0].text()
            raPattern = re.compile("[0-9]{1,2}h[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,3})?s")
            decPattern = re.compile("-?[0-9]{1,2}d[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,3})?s")
            ra = self.raBox.text()
            dec = self.decBox.text()
            if not raPattern.match(ra):
                self.show_error("Ra error", "Ra coordinates don't match pattern 00h00m00.00s")
            elif not decPattern.match(dec):
                self.show_error("Dec error", "Dec coordinates don't match pattern 00d00m00.00s")
            else:
                self.targetsDict[targetName]["ra"] = Angle(ra)
                self.targetsDict[targetName]["dec"] = Angle(dec)

    def add_target(self):
        raPattern = re.compile("[0-9]{1,2}h[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,3})?s")
        decPattern = re.compile("-?[0-9]{1,2}d[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,3})?s")
        ra = self.addRaBox.text()
        dec = self.addDecBox.text()
        name = self.addNameBox.text()
        print(self.targetsDict.keys())
        if ra == "" or dec == "" or name == "":
            self.show_error("Empty box", "Please fill all boxes")
        elif name in self.targetsDict.keys():
            self.show_error("Existing target", "Target already exists, please edit it")
        elif not raPattern.match(ra):
            self.show_error("Ra error", "Ra coordinates don't match pattern 00h00m00.00s")
        elif not decPattern.match(dec):
            self.show_error("Dec error", "Dec coordinates don't match pattern 00d00m00.00s")
        else:
            self.targetsDict[name] = {}
            self.targetsDict[name]["ra"] = Angle(ra)
            self.targetsDict[name]["dec"] = Angle(dec)
            self.edit_targets()

    def edit_calibrators(self):
        self.clear_window()

        self.calibratorList = QListWidget()
        for key in self.calibratorsDict:
            self.calibratorList.addItem(key)
        self.calibratorList.itemClicked.connect(self.calibratorChanged)
        self.layout.addWidget(self.calibratorList, 0, 0, 3, 1)

        calibratorLayout = QGridLayout()
        calibratorLayout.addWidget(QLabel("Ra:"), 0, 0)
        self.raBox = QLineEdit()
        calibratorLayout.addWidget(self.raBox, 0, 1)
        calibratorLayout.addWidget(QLabel("Dec:"), 1, 0)
        self.decBox = QLineEdit()
        calibratorLayout.addWidget(self.decBox, 1, 1)
        self.saveButton = QPushButton("Save changes")
        self.saveButton.clicked.connect(self.save_calibrator_changes)
        calibratorLayout.addWidget(self.saveButton, 2, 0, 1, 2)
        calibratorBox = QGroupBox()
        calibratorBox.setLayout(calibratorLayout)
        self.layout.addWidget(calibratorBox, 0, 1)
        self.saveButton.setEnabled(False)

        addcalibratorLayout = QGridLayout()
        addcalibratorLayout.addWidget(QLabel("Name:"), 0, 0)
        self.addNameBox = QLineEdit()
        addcalibratorLayout.addWidget(self.addNameBox, 0, 1)

        addcalibratorLayout.addWidget(QLabel("Ra:"), 1, 0)
        self.addRaBox = QLineEdit()
        addcalibratorLayout.addWidget(self.addRaBox, 1, 1)

        addcalibratorLayout.addWidget(QLabel("Dec:"), 2, 0)
        self.addDecBox = QLineEdit()
        addcalibratorLayout.addWidget(self.addDecBox, 2, 1)

        self.addSaveButton = QPushButton("Save changes")
        self.addSaveButton.clicked.connect(self.add_calibrator)
        addcalibratorLayout.addWidget(self.addSaveButton, 3, 0, 1, 2)

        addcalibratorBox = QGroupBox()
        addcalibratorBox.setLayout(addcalibratorLayout)
        self.layout.addWidget(addcalibratorBox, 1, 1)

        backButton = QPushButton("Back to planner")
        self.layout.addWidget(backButton, 0, 3)
        backButton.clicked.connect(self.to_start)

    def calibratorChanged(self, item):
        if not self.saveButton.isEnabled():
            self.saveButton.setEnabled(True)
        calibratorName = item.text()
        calibrator = self.calibratorsDict[calibratorName]
        self.raBox.setText(calibrator["ra"].to_string())
        self.decBox.setText(calibrator["dec"].to_string(unit=u.degree))

    def save_calibrator_changes(self):
        if len(self.calibratorList.selectedItems()) != 1:
            self.show_error("calibrator error", "Make sure you have selected only 1 calibrator")
        else:
            calibratorName = self.calibratorList.selectedItems()[0].text()
            raPattern = re.compile("[0-9]{1,2}h[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,5})?s")
            decPattern = re.compile("-?[0-9]{1,2}d[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,5})?s")
            ra = self.raBox.text()
            dec = self.decBox.text()
            if not raPattern.match(ra):
                self.show_error("Ra error", "Ra coordinates don't match pattern 00h00m00.00s")
            elif not decPattern.match(dec):
                self.show_error("Dec error", "Dec coordinates don't match pattern 00d00m00.00s")
            else:
                self.calibratorsDict[calibratorName]["ra"] = Angle(ra)
                self.calibratorsDict[calibratorName]["dec"] = Angle(dec)

    def add_calibrator(self):
        raPattern = re.compile("[0-9]{1,2}h[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,5})?s")
        decPattern = re.compile("-?[0-9]{1,2}d[0-9]{1,2}m[0-9]{1,2}(\.[0-9]{1,5})?s")
        ra = self.addRaBox.text()
        dec = self.addDecBox.text()
        name = self.addNameBox.text()
        print(self.calibratorsDict.keys())
        if ra == "" or dec == "" or name == "":
            self.show_error("Empty box", "Please fill all boxes")
        elif name in self.calibratorsDict.keys():
            self.show_error("Existing calibrator", "calibrator already exists, please edit it")
        elif not raPattern.match(ra):
            self.show_error("Ra error", "Ra coordinates don't match pattern 00h00m00.00s")
        elif not decPattern.match(dec):
            self.show_error("Dec error", "Dec coordinates don't match pattern 00d00m00.00s")
        else:
            self.calibratorsDict[name] = {}
            self.calibratorsDict[name]["ra"] = Angle(ra)
            self.calibratorsDict[name]["dec"] = Angle(dec)
            self.edit_calibrators()


    def load_settings(self):
        self.clear_window()
        targetLayout = QFormLayout()
        targetBox = QGroupBox()
        targetBox.setMaximumSize(350, 250)

        calibLabel = QLabel("Calib every X min:")
        self.calibBox = QLineEdit()
        calibLabel.setParent(targetBox)
        self.calibBox.setParent(targetBox)
        self.calibBox.setText(self.config['maxtimewithoutcalibration'])
        targetLayout.addRow(calibLabel, self.calibBox)

        calibDurLabel = QLabel("Calib duration:")
        self.calibDurBox = QLineEdit()
        calibDurLabel.setParent(targetBox)
        self.calibDurBox.setParent(targetBox)
        self.calibDurBox.setText(self.config['calibrationlength'])
        targetLayout.addRow(calibDurLabel, self.calibDurBox)

        minAltLabel = QLabel("Min alt:")
        self.minAltBox = QLineEdit()
        minAltLabel.setParent(targetBox)
        self.minAltBox.setParent(targetBox)
        self.minAltBox.setText(self.config['minaltitude'])
        targetLayout.addRow(minAltLabel, self.minAltBox)

        maxAltLabel = QLabel("Max alt:")
        self.maxAltBox = QLineEdit()
        maxAltLabel.setParent(targetBox)
        self.maxAltBox.setParent(targetBox)
        self.maxAltBox.setText(self.config['maxaltitude'])
        targetLayout.addRow(maxAltLabel, self.maxAltBox)

        calibToggleLabel = QLabel("Calibration on/off")
        self.calibCheckBox = QCheckBox()
        calibToggleLabel.setParent(targetBox)
        self.calibCheckBox.setParent(targetBox)
        if (self.config['calibration']):
            self.calibCheckBox.setChecked(True)
        else:
            self.calibCheckBox.setChecked(False)
        targetLayout.addRow(calibToggleLabel, self.calibCheckBox)

        saveButton = QPushButton("Save settings")
        saveButton.clicked.connect(self.save_settings)
        targetLayout.addRow(saveButton)

        targetBox.setLayout(targetLayout)
        self.layout.addWidget(targetBox, 0, 2, 2, 1)

    def save_settings(self):
        if not (self.calibBox.text().isdigit() and int(self.calibBox.text()) > 0):
            self.show_error("Input error","Max time without calib must be positive number")
        elif not (self.calibDurBox.text().isdigit() and int(self.calibDurBox.text()) > 0):
            self.show_error("Input error","Calib duration must be positive number")
        elif not (self.minAltBox.text().isdigit() and int(self.minAltBox.text()) > 0):
            self.show_error("Input error","Min alt must be positive number")
        elif not (self.maxAltBox.text().isdigit() and int(self.maxAltBox.text()) > 0):
            self.show_error("Input error","Max alt must be positive number")
        else:
            self.config['maxtimewithoutcalibration'] = self.calibBox.text()
            self.config['calibrationlength'] = self.calibDurBox.text()
            self.config['minaltitude'] = self.minAltBox.text()
            self.config['maxaltitude'] = self.maxAltBox.text()
            self.config['calibration'] = self.calibCheckBox.isChecked()
            self.to_start()

    def prepare_schedule(self):
        hasDate = False
        for index in range(self.dateList.count()):
            if self.dateList.item(index).checkState() == Qt.Checked:
                hasDate = True
                break
        if not hasDate:
            self.show_error("Date error", "No dates selected for schedule")
        else:
            self.start_schedule()

    def start_schedule(self):
        items = (self.layout.itemAt(i).widget() for i in range(self.layout.count()))
        self.targets = []

        for index in range(self.observationList.count()):
            item = self.observationList.item(index)
            target = item.data(Qt.UserRole)
            self.targets.append(target)

        targ_to_color = {}
        color_idx = np.linspace(0, 1, len(self.targets))
        # lighter, bluer colors indicate higher
        for target, ci in zip(set(self.targets), color_idx):
            if "split" not in target.name:
                if target.name not in targ_to_color:
                    targ_to_color[target.name] = plt.cm.jet(ci)

        calib_to_color = {}
        color_idx = np.linspace(0, 1, len(self.calibrators))
        # lighter, bluer colors indicate higher
        for calibrator, ci in zip(set(self.calibrators), color_idx):
            if "split" not in calibrator.name:
                if calibrator.name not in calib_to_color:
                    calib_to_color[calibrator.name] = plt.cm.brg(ci)

        self.plots_idx = 0
        self.plots = []

        week = {}

        for index in range(self.dateList.count()):
            if self.dateList.item(index).checkState() == Qt.Checked:
                week[self.dateList.item(index).text()]=[self.dateList.item(index).data(Qt.UserRole)[0], self.dateList.item(index).data(Qt.UserRole)[1]]


        for daySummary, day in week.items():


            dayStart = Time(day[0])  # convert from datetime to astropy.time
            dayEnd = Time(day[1])

            timeDict = {}
            #timeDict[target.name] = target.time

            for target in self.targets:
                if daySummary in target.times:
                    timeDict[target.name] = target.times[daySummary]

            minalt = self.config['minaltitude']
            maxalt = self.config['maxaltitude']

            constraints = [AltitudeConstraint(minalt * u.deg, maxalt * u.deg)]

            read_out = 1 * u.second
            target_exp = 60 * u.second
            blocks = []

            for target in self.targets:
                #if target.name == "g60p57":
                    #print(target)
                    #print(target.target)
                n = target.scans_per_obs
                priority = target.priority
                if (target.obs_per_week != 0):
                    b = ObservingBlock.from_exposures(target.target, priority, target_exp, n, read_out)
                    blocks.append(b)
            #for calibrator in self.calibrators:
                #if calibrator.name == "3C48":



            slew_rate = 2 * u.deg / u.second
            transitioner = Transitioner(slew_rate, {'filter': {'default': 5 * u.second}})

            if (self.config['calibration']):
                prior_scheduler = SequentialScheduler(constraints=constraints, observer=self.irbene, transitioner=transitioner,
                                                      calibrators=self.calibrators, config=self.config, timeDict=timeDict)

                priority_schedule = Schedule(dayStart, dayEnd, targColor=targ_to_color, calibColor=calib_to_color, minalt=minalt, maxalt=maxalt)
            else:
                prior_scheduler = SequentialScheduler(constraints=constraints, observer=self.irbene,
                                                      transitioner=transitioner,
                                                      config=self.config, timeDict=timeDict)

                priority_schedule = Schedule(dayStart, dayEnd, targColor=targ_to_color, minalt=minalt, maxalt=maxalt)

            prior_scheduler(blocks, priority_schedule)

            observations = []
            for block in priority_schedule.scheduled_blocks:
                if hasattr(block, 'target'):
                    observation = Observation(block.target.name, block.start_time.datetime,
                                              (block.start_time + block.duration).datetime)
                    observations.append(observation)

            dict_array = []
            for observation in observations:
                for target in self.targets:
                    if target.name == observation.name:
                        print(target.name, " has been observed once")
                        target.obs_per_week -= 1
                dict_array.append({
                    "obs_name": observation.name,
                    "start_time": observation.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": observation.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                })

            json_dict = dict()
            json_dict["observations"] = dict_array
            if not os.path.isdir("observations"):
                os.mkdir("observations")
            if not os.path.isdir("observations/"):
                os.mkdir("observations")
            with open("observations/" + day[0].strftime("%Y-%m-%d-%H-%M") + ".json", 'w') as outfile:
                json.dump(json_dict, outfile, indent=4)


            sky = Plot()
            skyCheck = sky.plot_sky_schedule(priority_schedule)
            alt = Plot(width=6)
            alt.plot_altitude_schedule(priority_schedule)

            if skyCheck is not False:
                self.plots.append([sky, alt])
            else:
                self.show_error("Empty schedule", "Schedule "+daySummary+"removing it")

        timeLeft = 0
        for target in self.targets:
            timeLeft += target.obs_per_week * target.scans_per_obs
            print(target.name, ' observations left ', target.obs_per_week, ' scan size ', target.scans_per_obs, ' priority ', target.priority)
        print('Total time left to observe ', timeLeft)

        self.showSky = False
        self.showAlt = False
        self.showBoth = True

        self.show_schedule()

    def show_schedule(self):
        self.clear_window()

        sky, alt = self.plots[self.plots_idx]

        if self.showSky:
            self.layout.addWidget(sky, 0, 0, 2, 6)

        elif self.showAlt:
            self.layout.addWidget(alt, 0, 0, 2, 6)

        elif self.showBoth:
            self.layout.addWidget(sky, 0, 0, 1, 6)
            self.layout.addWidget(alt, 1, 0, 1, 6)

        self.toolbar = NavigationToolbar(alt, alt.parent)
        self.layout.addWidget(self.toolbar, 2, 0, 1, 3)

        self.radioSky = QRadioButton("Show skychart")
        self.radioAlt = QRadioButton("Show altitude")
        self.radioBoth = QRadioButton("Show both")

        self.radioSky.clicked.connect(self.changeScheduleView)
        self.radioAlt.clicked.connect(self.changeScheduleView)
        self.radioBoth.clicked.connect(self.changeScheduleView)


        self.layout.addWidget(self.radioSky, 2, 3)
        self.layout.addWidget(self.radioAlt, 2, 4)
        self.layout.addWidget(self.radioBoth, 2, 5)

        nextButton = QPushButton("Next")
        nextButton.clicked.connect(self.next_schedule)
        backButton = QPushButton("Back")
        backButton.clicked.connect(self.back_schedule)
        self.layout.addWidget(backButton, 3, 0, 1, 3)
        self.layout.addWidget(nextButton, 3, 3, 1, 3)

        startButton = QPushButton("To start")
        startButton.clicked.connect(self.to_start)
        self.layout.addWidget(startButton, 4, 0, 1, 3)

        if self.plots_idx == 0:
            backButton.hide()
        if self.plots_idx == (len(self.plots) - 1):
            nextButton.hide()

    def next_schedule(self):
        self.plots_idx += 1
        self.show_schedule()

    def changeScheduleView(self):
        radioText = self.sender().text()
        if "sky" in radioText:
            self.showSky = True
            self.showAlt = False
            self.showBoth = False
            self.show_schedule()
        elif "alt" in radioText:
            self.showSky = False
            self.showAlt = True
            self.showBoth = False
            self.show_schedule()
        elif "both" in radioText:
            self.showSky = False
            self.showAlt = False
            self.showBoth = True
            self.show_schedule()

    def back_schedule(self):
        self.plots_idx -= 1
        self.show_schedule()

    def show_error(self, title, error_message):
        error_dialog = QMessageBox.critical(self, title, error_message)

    def to_start(self):
        self.clear_window()
        self.load_ui()

    def clear_window(self):
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

    def is_time_format(self, string):
        p = re.compile('^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$')
        res = p.match(string)
        print(res)
        return res

    def deleteItemsOfLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.deleteItemsOfLayout(item.layout())

if __name__=="__main__":
    main()