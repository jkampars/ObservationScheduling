import numpy as np
import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, Angle
from astropy.time import Time
from astroplan import Observer, FixedTarget, ObservingBlock
from astroplan.constraints import AltitudeConstraint, TimeConstraint
from astroplan.scheduling import Transitioner, PriorityScheduler, Schedule, SequentialScheduler
from astroplan.plots import  plot_schedule_altitude
from observation import Observation

import configparser
import datetime

def insert (source_str, insert_str, pos):
    return source_str[:pos]+insert_str+source_str[pos:]


def main():


    plt.style.use(astropy_mpl_style)


    source = "g33p64"
    configFilePath = "config/config.cfg"
    config = configparser.RawConfigParser()
    config.read(configFilePath)
    coordinates = config.get('sources', source).replace(" ", "").split(",")
    targets = []
    for key in config['sources']:
        sourceName = key
        sourceCoordinates = config.get('sources', key).replace(" ", "").split(",")

        raText = str(sourceCoordinates[0])
        raText = insert(raText, 'h', 2)
        raText = insert(raText, 'm', 5)
        raText = insert(raText, 's', len(raText))

        decText = str(sourceCoordinates[1])
        if(decText[0]!="-"):
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
        ra = targetCoord.ra.hour
        dec = targetCoord.dec.degree
        targetCoord = SkyCoord(frame='icrs', ra=ra*u.hour, dec=dec*u.deg, obstime="J2000")
        target = FixedTarget(coord = targetCoord, name=sourceName)
        targets.append(target)


    irbeneLocation = EarthLocation(lat=57.5535171694 * u.deg, lon=21.8545525000 * u.deg, height=87.30 * u.m)
    irbene = Observer(location=irbeneLocation, name="Irbene", timezone="Europe/Riga")
    noon_before = Time('2016-07-06 00:00:00')
    noon_after = Time('2016-07-07 00:00:00')

    constraints = [AltitudeConstraint(20*u.deg, 85*u.deg)]

    read_out = 1 * u.second
    target_exp = 300 * u.second
    n = 1
    blocks = []

    priority = 1
    for target in targets[0:5]:
        b = ObservingBlock.from_exposures(target, priority, target_exp, n, read_out)
        blocks.append(b)

    target_exp = 600 * u.second

    priority = 2

    for target in targets[10:15]:
        b = ObservingBlock.from_exposures(target, priority, target_exp, n, read_out)
        blocks.append(b)

    target_exp = 900 * u.second

    priority = 3

    for target in targets[20:25]:
        b = ObservingBlock.from_exposures(target, priority, target_exp, n, read_out)
        blocks.append(b)



    slew_rate = 2 * u.deg / u.second
    transitioner = Transitioner(slew_rate, {'filter':{'default': 5*u.second}})

    prior_scheduler = PriorityScheduler(constraints=constraints,
                                observer = irbene,
                                transitioner = transitioner)

    priority_schedule = Schedule(noon_before, noon_after)
    prior_scheduler(blocks, priority_schedule)


    for block in priority_schedule.scheduled_blocks:
        if (type(block) == type(ObservingBlock(target, 1*u.second, 1))):
            #print(block.target.name)
            #print(block.start_time.datetime)
            #print((block.start_time+block.duration).datetime)
            observation = Observation(block.target.name, block.start_time.datetime, (block.start_time+block.duration).datetime)
            print(observation)
    plot_schedule_altitude(priority_schedule)
    plt.legend(loc="upper right")
    plt.show()


if __name__=="__main__":
    main()
