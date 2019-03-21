from astroplan import FixedTarget

class PlannedObs:

    def __init__(self):
        self.target = FixedTarget()
        self.priority = 0
        self.obs_per_week = 0
        self.scans_per_obs = 0
        self.name = ""

    def __init__(self, target, prio, obs, scan):
        self.target = target
        self.priority = prio
        self.obs_per_week = obs
        self.scans_per_obs = scan
        self.name = target.name

    def __str__(self):
        return ("%s priority %s obs per week %s scans per obs %s"%(self.target.name,self.priority,self.obs_per_week, self.scans_per_obs))