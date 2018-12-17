import datetime

class Observation:

    def __init__(self):
        self.name = ""
        self.start_time = datetime.datetime()
        self.end_time = datetime.datetime()

    def __init__(self, name, start_time, end_time):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time

    def __str__(self):
        return ("Observation of target %s from %s till %s"%(self.name,self.start_time,self.end_time))