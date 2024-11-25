from Misc.settings import Settings

class OutdoorEnvironment:
    def __init__(self,
                 id = None,
                 **kwargs):
        self.id = id
        self.output = {"ppmCO2": None}
           
    def doStep(self):
        self.output["ppmCO2"] = Settings.ppmCO2Out
    

