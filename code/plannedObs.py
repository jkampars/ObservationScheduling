import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from astroplanventa import FixedTarget

class PlannedObs:

    def __init__(self):
        self.target = FixedTarget()
        self.priority = 0
        self.obs_per_week = 0
        self.scans_per_obs = 0
        self.name = ""
        self.times = {}
        self.global_time = ""

    def __init__(self, target, prio, obs, scan):
        self.target = target
        self.priority = prio
        self.obs_per_week = obs
        self.scans_per_obs = scan
        self.name = target.name
        self.times = {}
        self.global_time = ""


    def __init__(self, target, prio, obs, scan, times = None, global_time = None):
        self.target = target
        self.priority = prio
        self.obs_per_week = obs
        self.scans_per_obs = scan
        self.name = target.name
        if times == None:
            times = ""
        self.times = times
        if global_time == None:
            global_time = ""
        self.global_time = global_time

    def __str__(self):
        return ("%s priority %s obs per week %s scans per obs %s"%(self.target.name,self.priority,self.obs_per_week, self.scans_per_obs))

    def get_times(self):
        return self.times, self.global_time