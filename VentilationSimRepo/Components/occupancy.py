import datetime

class Occupancy:
    def __init__(self,
                 id = None,
                 containedIn = None,
                 dateTimeDf = None,
                 dataFile = None,
                 data = None,
                 scheduleFromData = None,
                 ventilationSystem = None,
                 **kwargs):
        self.id = id
        self.containedIn = containedIn
        self.dateTimeDf = dateTimeDf
        self.dataFile = dataFile
        self.data = data
        self.scheduleFromData = scheduleFromData
        self.ventilationSystem = ventilationSystem
        
        self.stepCount = 0
        
        self.output = {"occupants": 0}
        
        # Fixed schedule
        self.fixedScheduleWeekDay = [[0,              0],
                                     [7*3600,         5],
                                     [8*3600,         15],
                                     [8*3600 + 1800,  20],
                                     [12*3600,        13],
                                     [14*3600,        10],
                                     [16*3600,        5],
                                     [18*3600,        0]]
        self.fixedScheduleWeekend = [[0,         0],
                                     [8*3600,    5],
                                     [16*3600,   0]]       
        self.fixedScheduleHoliday = []
        
    def doStep(self):
        if self.dataFile != None:
            self.output["occupants"] = self.scheduleFromData["OCC"][self.stepCount]
        elif type(self.scheduleFromData) != 'NoneType':
            self.output["occupants"] = self.scheduleFromData[self.stepCount]
        else:
            time = self.dateTimeDf['DateTime'][self.stepCount]
            midnight = self.dateTimeDf['DateTime'][self.stepCount].replace(hour=0, minute=0, second=0, microsecond=0)
            timeOfDay = (time-midnight).seconds
            if time.weekday() <= 4:
                for row in self.fixedScheduleWeekDay:
                    if timeOfDay >= row[0]:
                        self.output["occupants"] = row[1]
            else:
                for row in self.fixedScheduleWeekend:
                    if timeOfDay >= row[0]:
                        self.output["occupants"] = row[1]
        self.stepCount = self.stepCount + 1