from Misc.settings import Settings
import datetime
import warnings

class Controller:
    def __init__(self,
                 id = None,
                 containedIn = None,
                 superSystem = None,
                 controlsElementType = None,
                 startTime = None,
                 ruleset = None,
                 controlType = None,
                 **kwargs):
        self.id = id
        self.containedIn = containedIn
        self.superSystem = superSystem
        self.controlsElementType = controlsElementType
        self.ruleset = [[0,    0], #(Nx2 dimension matrix with CO2 thresholds and corresponding position)
                        [600,  .45],
                        [750,  .7],
                        [900,  1]]
        self.setSchedule = [[0, 0],
                            [7*3600, 0.33],
                            [18*3600, 0]]
        self.controlType = controlType
        
        self.prevCO2 = Settings.ppmCO2Out
        
        self.startTime = startTime
        self.step = 0
        self.P = 0.0026
        self.D = 0
        
        self.input = {"inputValue": None}
        self.output = {"outputSignal": None}

    def doStep(self):   
        if self.controlType == "MPC":
            self.input["inputValue"] = self.inputSender["inputValue"].output[self.inputSenderProperty["inputValue"][0]][self.inputSenderProperty["inputValue"][1]]
            self.output['outputSignal'] = self.input["inputValue"]
        
        elif self.controlType == 'ruleSet': 
            self.input["inputValue"] = self.inputSender["inputValue"].output[self.inputSenderProperty["inputValue"]]
            for row in self.ruleset:
                if row[0] <= self.input["inputValue"]:
                    self.output["outputSignal"] = row[1]
    
        elif self.controlType == 'PD': 
            self.input["inputValue"] = self.inputSender["inputValue"].output[self.inputSenderProperty["inputValue"]]
            co2 = self.input["inputValue"]
            threshold = 573
            p = self.P * (co2-threshold)
            d = self.D * (co2 - self.prevCO2) / Settings.timeStep 
            self.output["outputSignal"] = min(1,max(0,p+d))
            self.prevCO2 = co2
            
        elif self.controlType == 'schedule': 
            time = self.startTime + datetime.timedelta(seconds=600)*self.step
            midnight = time.replace(hour=0, minute=0)
            timeOfDay = time-midnight
            for idx in range(len(self.setSchedule)):
                if timeOfDay.seconds >= self.setSchedule[idx][0]:
                    opening = self.setSchedule[idx][1]
            if time.weekday() > 4:
                opening = opening / 3
            self.output["outputSignal"] = opening
            
        elif self.controlType == 'constant': 
            self.output["outputSignal"] = 0.33
        else:
            warnings.warn('Unknown control type for ' + self.id)
            
        self.step += 1
        
        
