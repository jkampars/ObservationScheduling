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
from astroplan.scheduling import Transitioner, PriorityScheduler, Schedule, SequentialScheduler
from astroplan.plots import  plot_schedule_altitude, plot_altitude
from dateutil.parser import parse

from observation import Observation
from googlecalendar import get_next_week_events

import os
import json
import datetime
import csv

def insert (source_str, insert_str, pos):
    return source_str[:pos]+insert_str+source_str[pos:]


def main():
    try:
        urlopen('http://maia.usno.navy.mil/ser7/finals2000A.all')
    except HTTPError as e:
        print("Main IERS link not working, using mirror")
        iers.conf.iers_auto_url = 'http://toshi.nofs.navy.mil/ser7/finals2000A.all'
    except URLError as e:
        print("Main IERS link not working, using mirror")
        iers.conf.iers_auto_url = 'http://toshi.nofs.navy.mil/ser7/finals2000A.all'

    plt.style.use(astropy_mpl_style)

    targets = []
    with open("config/config.csv","r") as csvfile:
        next(csvfile)
        spamreader = csv.reader(csvfile, delimiter=",", quotechar="|")
        for row in spamreader:
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
            targets.append([target, int(row[3]), int(row[4]), int(row[5])]) #target / obs per_week / priority / scans per obs

    targets = sorted(targets, key=lambda x: x[2]) #sort targets by priority

    irbeneLocation = EarthLocation(lat=57.5535171694 * u.deg, lon=21.8545525000 * u.deg, height=87.30 * u.m)
    irbene = Observer(location=irbeneLocation, name="Irbene", timezone="Europe/Riga")

    week = []
    startArray, endArray, summaryArray = get_next_week_events()
    for i in range(len(startArray)):
        if ("(C band)" not in summaryArray[i]):
            dayStart = parse(startArray[i])
            dayEnd = parse(endArray[i])
            week.append([dayStart, dayEnd])

    for day in week:
            dayStart = Time(day[0]) #convert from datetime to astropy.time
            dayEnd = Time(day[1])

            min_Altitude = 20
            max_Altitude = 85
            constraints = [AltitudeConstraint(min_Altitude*u.deg, max_Altitude*u.deg)]

            read_out = 1 * u.second
            target_exp = 60 * u.second
            blocks = []

            for target in targets:
                n = target[3]
                priority = target[2]
                if (target[1] != 0):
                    b = ObservingBlock.from_exposures(target[0], priority, target_exp, n, read_out)
                    blocks.append(b)

            slew_rate = 2 * u.deg / u.second
            transitioner = Transitioner(slew_rate, {'filter':{'default': 5*u.second}})

            prior_scheduler = SequentialScheduler(constraints=constraints,
                                        observer = irbene,
                                        transitioner = transitioner)

            priority_schedule = Schedule(dayStart, dayEnd)
            prior_scheduler(blocks, priority_schedule)

            observations = []
            for block in priority_schedule.scheduled_blocks:
                if (type(block) == type(ObservingBlock(target, 1*u.second, 1))):
                    observation = Observation(block.target.name, block.start_time.datetime, (block.start_time+block.duration).datetime)
                    observations.append(observation)

            dict_array = []
            for observation in observations:
                for target in targets:
                    if target[0].name == observation.name:
                        print(target[0].name," has been observed once")
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
            with open("observations/"+day[0].strftime("%Y-%m-%d-%H-%M")+".json", 'w') as outfile:
                json.dump(json_dict,  outfile, indent=4)
            ax = plot_schedule_altitude(priority_schedule)
            ax.axhline(y=min_Altitude, color='r', dashes=[2,2], label='Altitude constraint')
            ax.axhline(y=max_Altitude, color='r', dashes=[2,2])
            ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
            #plt.show()

    timeLeft = 0
    for target in targets:
        timeLeft += target[1] * target[3]
        print(target[0].name,' observations left ',target[1],' scan size ',target[3],' priority ',target[2])
    print('Total time left to observe ',timeLeft)

if __name__=="__main__":
    main()
