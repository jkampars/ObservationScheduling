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
from PyQt5.QtWidgets import QApplication, QWidget, QFormLayout, QGridLayout, QGroupBox, QLineEdit, QLabel, QPushButton, QProgressBar
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


from observation import Observation
from googlecalendar import get_next_week_events, get_all_events
from plot_qt5 import Plot

import argparse
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
                    decText = insert(decText, '°', 2)
                    decText = insert(decText, '′', 5)
                    decText = insert(decText, '″', len(decText))
                else:
                    decText = insert(decText, '°', 3)
                    decText = insert(decText, '′', 6)
                    decText = insert(decText, '″', len(decText))

                ra = Angle(raText)
                dec = Angle(decText)

                targetCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                target = FixedTarget(coord=targetCoord, name=sourceName)
                self.targets.append([target, int(row[3]), int(row[4]), int(row[5])])  # target / obs per_week / priority / scans per obs
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

        self.load_ui()

    def load_ui(self):
        self.layout = QGridLayout()
        row = 0
        column = 0
        for count, target in enumerate(self.targets[:20]):
            targetLayout = QFormLayout()
            targetBox = QGroupBox()

            nameLabel = QLabel("Target:")
            nameBox = QLineEdit(target[0].name)
            nameLabel.setParent(targetBox)
            nameBox.setParent(targetBox)
            targetLayout.addRow(nameLabel, nameBox)

            raLabel = QLabel("Ra:")
            raBox = QLineEdit(target[0].coord.ra.to_string())
            raLabel.setParent(targetBox)
            raBox.setParent(targetBox)
            targetLayout.addRow(raLabel, raBox)

            decLabel = QLabel("Dec:")
            decBox = QLineEdit(target[0].coord.dec.to_string())
            decLabel.setParent(targetBox)
            decBox.setParent(targetBox)
            targetLayout.addRow(decLabel, decBox)

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
        self.setLayout(self.layout)



    def start_schedule(self):
        items = (self.layout.itemAt(i).widget() for i in range(self.layout.count()))
        self.targets = []
        for item in items:
            if type(item) is QGroupBox:
                textboxes = []
                for child in item.children():
                    if type(child) is QLineEdit:
                        textboxes.append(child.text())
                sourceName = textboxes[0]
                ra = textboxes[1]
                dec = textboxes[2]
                targetCoord = SkyCoord(frame='icrs', ra=ra, dec=dec, obstime="J2000")
                target = FixedTarget(coord=targetCoord, name=sourceName)
                self.targets.append([target, int(textboxes[4]), int(textboxes[3]),
                                     int(textboxes[5])])  # target / obs per_week / priority / scans per obs
        self.plots_idx = 0
        self.plots = []
        self.schedules=[]
        for day in self.week:
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

            self.schedules.append(priority_schedule)
        timeLeft = 0
        for target in self.targets:
            timeLeft += target[1] * target[3]
            print(target[0].name, ' observations left ', target[1], ' scan size ', target[3], ' priority ', target[2])
        print('Total time left to observe ', timeLeft)

        self.show_schedule()

    def show_schedule(self):
        self.clear_window()
        if len(self.plots) == 0 or self.plots_idx > (len(self.plots) - 1):
            sky = Plot()
            sky.plot_sky_schedule(self.schedules[self.plots_idx])
            alt = Plot(width=6)
            alt.plot_altitude_schedule(self.schedules[self.plots_idx])
            self.plots.append([sky, alt])
        else:
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
        if self.plots_idx == (len(self.schedules) - 1):
            nextButton.hide()

    def next_schedule(self):
        self.plots_idx += 1
        self.show_schedule()


    def back_schedule(self):
        self.plots_idx -= 1
        self.show_schedule()

    def clear_window(self):
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

if __name__=="__main__":
    main()
