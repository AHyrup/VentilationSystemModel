from Misc.settings import Settings

class Sensor:
    def __init__(self,
                 id = None,
                 containedIn = None,
                 measuresProperty=None,
                 **kwargs):
        self.id = id
        self.containedIn = containedIn
        self.measuresProperty=measuresProperty
        
        self.firstStep = True
        
        self.input = {"value": None}
        self.output = {"value": None}

    def doStep(self):
        if self.firstStep:
            self.input["value"] = Settings.ppmCO2BuildingInitial
            self.firstStep = False
        else:
            self.input["value"] = self.inputSender["value"].output[self.inputSenderProperty["value"]]
            
        self.output["value"] = self.input["value"] 