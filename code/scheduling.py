# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, Angle
from astropy.time import Time
from astropy.utils import iers
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from astroplan import Observer, FixedTarget, ObservingBlock, TransitionBlock
from astroplan.constraints import AltitudeConstraint
from astroplan.scheduling import Transitioner, PriorityScheduler, Schedule, SequentialScheduler
from astroplan.plots import  plot_schedule_altitude, plot_altitude, plot_schedule_sky, plot_sky
from dateutil.parser import parse
from astroplan import is_always_observable, download_IERS_A
from collections import OrderedDict
from PyQt5.QtWidgets import QApplication, QWidget, QFormLayout, QGridLayout, QGroupBox, QLineEdit, QLabel, QPushButton, QComboBox, QErrorMessage
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from observation import Observation
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
                self.targets.append([target, int(row[3]), int(row[4]), int(row[5])])  # target / obs per_week / priority / scans per obs
                coords = {"ra": ra, "dec": dec}
                self.targetsDict[sourceName] = coords
        self.targets = sorted(self.targets, key=lambda x: x[2])  # sort targets by priority
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
                    decText = insert(decText, '°', 3)
                    decText = insert(decText, '′', 6)
                    decText = insert(decText, '″', len(decText))
                else:
                    decText = insert(decText, '°', 3)
                    decText = insert(decText, '′', 6)
                    decText = insert(decText, '″', len(decText))

                ra = Angle(raText)
                dec = Angle(decText)

                calibratorCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                calibrator = FixedTarget(coord=calibratorCoord, name=sourceName)
                self.calibrators.append(calibrator)

        self.week = []
        startArray, endArray, summaryArray = get_next_week_events()
        for i in range(len(startArray)):
            if (summaryArray[i] == "RT-16 maser"):
                dayStart = parse(startArray[i])
                dayEnd = parse(endArray[i])
                self.week.append([dayStart, dayEnd])


        self.layout = QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)

        self.load_ui()

    def load_ui(self):
        row = 0
        column = 0



        for count, target in enumerate(self.targets[:20]):
            targetLayout = QFormLayout()
            targetBox = QGroupBox()
            targetBox.setMaximumSize(250,150)

            nameLabel = QLabel("Target:")
            nameBox = QComboBox()
            for key in self.targetsDict:
                nameBox.addItem(key)
            nameBox.setCurrentIndex(list(self.targetsDict.keys()).index(target[0].name))
            nameLabel.setParent(targetBox)
            nameBox.setParent(targetBox)
            targetLayout.addRow(nameLabel, nameBox)

            priorityLabel = QLabel("Priority:")
            priorityBox = QLineEdit(str(target[2]))
            priorityLabel.setParent(targetBox)
            priorityBox.setParent(targetBox)
            targetLayout.addRow(priorityLabel, priorityBox)

            obsLabel = QLabel("Obs per week:")
            obsBox = QLineEdit(str(target[1]))
            obsLabel.setParent(targetBox)
            obsBox.setParent(targetBox)
            targetLayout.addRow(obsLabel, obsBox)

            scanLabel = QLabel("Scans per obs:")
            scanBox = QLineEdit(str(target[3]))
            scanLabel.setParent(targetBox)
            scanBox.setParent(targetBox)
            targetLayout.addRow(scanLabel, scanBox)

            targetBox.setLayout(targetLayout)
            self.layout.addWidget(targetBox, row, column)
            column+=1

            if column == 7:
                row+=1
                column = 0

        nextButton = QPushButton("Schedule")
        nextButton.clicked.connect(self.start_schedule)
        self.layout.addWidget(nextButton, 0, 8)
        targetsButton = QPushButton("Targets")
        targetsButton.clicked.connect(self.edit_targets)
        self.layout.addWidget(targetsButton, 1, 8)
        self.setLayout(self.layout)



    def start_schedule(self):
        items = (self.layout.itemAt(i).widget() for i in range(self.layout.count()))
        self.targets = []
        for item in items:
            if type(item) is QGroupBox:
                textboxes = []
                for child in item.children():
                    if type(child) is QComboBox:
                        sourceName = child.currentText()
                    if type(child) is QLineEdit:
                        textboxes.append(child.text())
                ra = self.targetsDict[sourceName]["ra"]
                dec = self.targetsDict[sourceName]["dec"]
                targetCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                target = FixedTarget(coord=targetCoord, name=sourceName)
                self.targets.append([target, int(textboxes[1]), int(textboxes[0]),
                                     int(textboxes[2])])  # target / obs per_week / priority / scans per obs
        self.plots_idx = 0
        self.plots = []
        for day in self.week[:1]:
            dayStart = Time(day[0])  # convert from datetime to astropy.time
            dayEnd = Time(day[1])

            min_Altitude = 20
            max_Altitude = 85
            constraints = [AltitudeConstraint(min_Altitude * u.deg, max_Altitude * u.deg)]

            read_out = 1 * u.second
            target_exp = 60 * u.second
            blocks = []

            for target in self.targets:
                if (not is_always_observable(constraints, self.irbene, target[0], times=[dayStart, dayEnd])):
                    print(target[0].name, " is not observable")
                n = target[3]
                priority = target[2]
                if (target[1] != 0):
                    b = ObservingBlock.from_exposures(target[0], priority, target_exp, n, read_out)
                    blocks.append(b)

            slew_rate = 2 * u.deg / u.second
            transitioner = Transitioner(slew_rate, {'filter': {'default': 5 * u.second}})
            print("Starting scheduler")
            prior_scheduler = SequentialScheduler(constraints=constraints, observer=self.irbene, transitioner=transitioner,
                                                  calibrators=self.calibrators, firstSchedule=True)

            priority_schedule = Schedule(dayStart, dayEnd)
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
                    if target[0].name == observation.name:
                        print(target[0].name, " has been observed once")
                        target[1] = target[1] - 1
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
            timeLeft += target[1] * target[3]
            print(target[0].name, ' observations left ', target[1], ' scan size ', target[3], ' priority ', target[2])
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

    def edit_targets(self):
        self.clear_window()

        targetLayout = QGridLayout()
        targetBox = QGroupBox()
        targetBox.setMaximumSize(400,400)

        nameLabel = QLabel("Target:")
        nameLabel.setMaximumWidth(100)
        self.target_nameBox = QComboBox()
        for key in self.targetsDict:
            self.target_nameBox.addItem(key)
        self.target_nameBox.currentIndexChanged.connect(self.target_changed)
        targetLayout.addWidget(nameLabel, 0, 0)
        targetLayout.addWidget(self.target_nameBox, 0, 1)

        raLabel = QLabel("Ra:")
        self.target_raBox = QLineEdit()
        raLabel.setParent(targetBox)
        self.target_raBox.setParent(targetBox)
        targetLayout.addWidget(raLabel, 1, 0)
        targetLayout.addWidget(self.target_raBox, 1, 1)

        decLabel = QLabel("Dec:")
        self.target_decBox = QLineEdit()
        decLabel.setParent(targetBox)
        self.target_decBox.setParent(targetBox)
        targetLayout.addWidget(decLabel, 2, 0)
        targetLayout.addWidget(self.target_decBox, 2, 1)
        saveButton = QPushButton("Save changes")
        saveButton.clicked.connect(self.save_changes)
        targetLayout.addWidget(saveButton, 3, 1)

        backButton = QPushButton("Back")
        backButton.clicked.connect(self.to_start)
        targetLayout.addWidget(backButton, 4, 1)

        targetBox.setLayout(targetLayout)
        self.layout.addWidget(targetBox,0,0)


    def target_changed(self):
        target = self.targetsDict[self.target_nameBox.currentText()]
        self.target_raBox.setText(target["ra"].to_string())
        self.target_decBox.setText(target["dec"].to_string(unit=u.degree))

    def save_changes(self):
        targetName = self.target_nameBox.currentText()
        raPattern = re.compile("[0-9]{2}h[0-9]{2}m[0-9]{2}\.[0-9]{2}s")
        decPattern = re.compile("-?[0-9]{2}°[0-9]{2}'[0-9]{2}\\\"")
        ra = self.target_raBox.text()
        dec = self.target_decBox.text()
        if not raPattern.match(ra):
            error_dialog = QErrorMessage()
            error_dialog.showMessage("Ra coordinates don't match pattern 00h00m00.00s")
            error_dialog.exec_()
        else:
            self.targetsDict[targetName]["ra"] = Angle(ra)
            self.targetsDict[targetName]["dec"] = Angle(dec)
        """elif not decPattern.match(dec):
            print(raPattern.match(ra))
            print(decPattern.match(dec))
            for char in dec:
                print (char,"  ",ord(char))
            print('-  ',ord('-'))
            print('°  ',ord('°'))
            print("'  ",ord("'"))
            print('"  ',ord('"'))
        else:
            print("Ra and Dec correct")"""

    def to_start(self):
        self.clear_window()
        self.load_ui()

    def clear_window(self):
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

if __name__=="__main__":
    main()
