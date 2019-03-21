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
from PyQt5.QtWidgets import QApplication, QWidget, QFormLayout, QGridLayout, QGroupBox, QLineEdit, QLabel, QPushButton, QComboBox, QMessageBox, QListWidget, QListWidgetItem
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
import datetime
import csv
import pickle
import io


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
        # download_IERS_A()

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

                calibratorCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                calibrator = FixedTarget(coord=calibratorCoord, name=sourceName)
                self.calibrators.append(calibrator)

        startArray, endArray, summaryArray = get_next_week_events()
        self.dateList = QListWidget()

        for i in range(len(startArray)):
            dayStart = parse(startArray[i])
            dayEnd = parse(endArray[i])
            daySummary = summaryArray[i]
            daySummary = daySummary + " " + str(dayStart.date()) + " " + str(dayStart.time()) + "-" + str(dayEnd.time())
            item = QListWidgetItem(daySummary, self.dateList)
            item.setData(Qt.UserRole, [dayStart, dayEnd])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.dateList.addItem(item)

        self.layout = QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        self.resize(1000, 600)

        self.load_ui()

    def load_ui(self):
        self.observationList = QListWidget()
        self.plannedTargets = []
        for target in self.targets[:20]:
            item = QListWidgetItem(str(target), self.observationList)
            item.setData(Qt.UserRole, target)
            self.observationList.addItem(item)
            self.plannedTargets.append(target.name)

        self.layout.addWidget(self.observationList, 0, 0, 10, 2)

        self.observationList.itemSelectionChanged.connect(self.obsChanged)

        for index in range(self.observationList.count()):
            item = self.observationList.item(index)
            print(item.data(Qt.UserRole))

        targetLayout = QFormLayout()
        targetBox = QGroupBox()
        targetBox.setMaximumSize(350, 250)

        nameLabel = QLabel("Target:")
        self.nameBox = QLineEdit()
        self.nameBox.setEnabled(False)
        nameLabel.setParent(targetBox)
        self.nameBox.setParent(targetBox)
        targetLayout.addRow(nameLabel, self.nameBox)

        priorityLabel = QLabel("Priority:")
        self.priorityBox = QLineEdit()
        priorityLabel.setParent(targetBox)
        self.priorityBox.setParent(targetBox)
        targetLayout.addRow(priorityLabel, self.priorityBox)

        obsLabel = QLabel("Obs per week:")
        self.obsBox = QLineEdit()
        obsLabel.setParent(targetBox)
        self.obsBox.setParent(targetBox)
        targetLayout.addRow(obsLabel, self.obsBox)

        scanLabel = QLabel("Scans per obs:")
        self.scanBox = QLineEdit()
        scanLabel.setParent(targetBox)
        self.scanBox.setParent(targetBox)
        targetLayout.addRow(scanLabel, self.scanBox)

        saveButton = QPushButton("Save changes")
        saveButton.clicked.connect(self.save_obs_changes)
        targetLayout.addRow(saveButton)

        removeButton = QPushButton("Remove target")
        removeButton.clicked.connect(self.remove_obs)
        targetLayout.addRow(removeButton)

        targetBox.setLayout(targetLayout)
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

    def obsChanged(self):
        if len(self.observationList.selectedItems()) > 0:
            item = self.observationList.currentItem()
            plannedObs = item.data(Qt.UserRole)
            self.nameBox.setText(plannedObs.name)
            self.priorityBox.setText(str(plannedObs.priority))
            self.obsBox.setText(str(plannedObs.obs_per_week))
            self.scanBox.setText(str(plannedObs.scans_per_obs))
        else:
            self.nameBox.setText("")
            self.priorityBox.setText("")
            self.obsBox.setText("")
            self.scanBox.setText("")

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
        else:
            self.observationList.currentItem().data(Qt.UserRole).priority = int(self.priorityBox.text())
            self.observationList.currentItem().data(Qt.UserRole).obs_per_week = int(self.obsBox.text())
            self.observationList.currentItem().data(Qt.UserRole).scans_per_obs = int(self.scanBox.text())
            self.observationList.currentItem().setText(str(self.observationList.currentItem().data(Qt.UserRole)))

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
        self.layout.addWidget(self.targetList, 0, 0, 3, 1)
        targetLayout = QGridLayout()
        targetLayout.addWidget(QLabel("Ra:"), 0, 0)
        self.raBox = QLineEdit()
        targetLayout.addWidget(self.raBox, 0, 1)
        targetLayout.addWidget(QLabel("Dec:"), 1, 0)
        self.decBox = QLineEdit()
        targetLayout.addWidget(self.decBox, 1, 1)

        for key in self.targetsDict:
            self.targetList.addItem(key)

        self.targetList.itemClicked.connect(self.targetChanged)

        self.saveButton = QPushButton("Save changes")
        self.saveButton.clicked.connect(self.save_changes)
        targetLayout.addWidget(self.saveButton, 2, 0, 1, 2)
        targetBox = QGroupBox()
        targetBox.setLayout(targetLayout)
        self.layout.addWidget(targetBox, 0, 1)
        self.saveButton.setEnabled(False)
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

    def save_changes(self):
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

        week = []

        for index in range(self.dateList.count()):
            if self.dateList.item(index).checkState() == Qt.Checked:
                week.append([self.dateList.item(index).data(Qt.UserRole)[0], self.dateList.item(index).data(Qt.UserRole)[1]])

        for day in week:
            dayStart = Time(day[0])  # convert from datetime to astropy.time
            dayEnd = Time(day[1])

            min_Altitude = 20
            max_Altitude = 85
            constraints = [AltitudeConstraint(min_Altitude * u.deg, max_Altitude * u.deg)]

            read_out = 1 * u.second
            target_exp = 60 * u.second
            blocks = []

            for target in self.targets:
                if (not is_always_observable(constraints, self.irbene, target.target, times=[dayStart, dayEnd])):
                    print(target.name, " is not observable")
                n = target.scans_per_obs
                priority = target.priority
                if (target.obs_per_week != 0):
                    b = ObservingBlock.from_exposures(target.target, priority, target_exp, n, read_out)
                    blocks.append(b)

            slew_rate = 2 * u.deg / u.second
            transitioner = Transitioner(slew_rate, {'filter': {'default': 5 * u.second}})
            print("Starting scheduler")
            prior_scheduler = SequentialScheduler(constraints=constraints, observer=self.irbene, transitioner=transitioner,
                                                  calibrators=self.calibrators, firstSchedule=True)

            priority_schedule = Schedule(dayStart, dayEnd, targColor=targ_to_color, calibColor=calib_to_color)
            prior_scheduler(blocks, priority_schedule)

            observations = []
            for block in priority_schedule.scheduled_blocks:
                if hasattr(block, 'target'):
                    print(block.target.name)
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
            sky.plot_sky_schedule(priority_schedule)
            alt = Plot(width=6)
            alt.plot_altitude_schedule(priority_schedule)
            self.plots.append([sky, alt])

        timeLeft = 0
        for target in self.targets:
            timeLeft += target.obs_per_week * target.scans_per_obs
            print(target.name, ' observations left ', target.obs_per_week, ' scan size ', target.scans_per_obs, ' priority ', target.priority)
        print('Total time left to observe ', timeLeft)

        self.show_schedule()

    def show_schedule(self):
        self.clear_window()
        sky, alt = self.plots[self.plots_idx]
        self.layout.addWidget(sky, 0, 0, 1, 2)
        self.layout.addWidget(alt, 1, 0, 1, 2)

        self.toolbar = NavigationToolbar(alt, alt.parent)
        self.layout.addWidget(self.toolbar, 2, 0, 1, 2)

        nextButton = QPushButton("Next")
        nextButton.clicked.connect(self.next_schedule)
        backButton = QPushButton("Back")
        backButton.clicked.connect(self.back_schedule)
        self.layout.addWidget(backButton, 3, 0)
        self.layout.addWidget(nextButton, 3, 1)

        startButton = QPushButton("To start")
        startButton.clicked.connect(self.to_start)
        self.layout.addWidget(startButton, 4, 0)
        if self.plots_idx == 0:
            backButton.hide()
        if self.plots_idx == (len(self.plots) - 1):
            nextButton.hide()

    def next_schedule(self):
        self.plots_idx += 1
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

if __name__=="__main__":
    main()
