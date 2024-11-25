from Misc.settings import Settings
import math

class BuildingSpace:
    def __init__(self,
                 id = None,
                 contains = None,
                 vol = None,
                 name = None,
                 ventilationSystem = None,
                 **kwargs):
        self.id = id
        self.contains = contains
        self.vol = vol
        self.name = name
        self.ventilationSystem = ventilationSystem
        
        self.timeStep = Settings.timeStep
        self.MCO2 = Settings.MCO2
        self.MAir = Settings.MAir
        self.rhoAir = Settings.rhoAir
        self.airInf = Settings.airInfSpace
        self.rhoCO2 = Settings.rhoCO2
        self.CO2GenPerson = Settings.CO2GenPerson
        
        self.firstStep = True
        
        self.input = {"occupants": None,
                      "flowVenIn": None,
                      "flowVenOut": None,
                      "ppmCO2Out": Settings.ppmCO2Out}
        self.output = {"ppmCO2": None}        

    def doStep(self): #Takes previous CO2 concentration, occupancy impact, ventilation flow and infiltration flow. Returns CO2 concentration [ppm] in a space
        self.input["occupants"] = self.inputSender["occupants"].output[self.inputSenderProperty["occupants"]] #Number of occupants
        self.input["flowVenIn"] = self.inputSender["flowVenIn"].output[self.inputSenderProperty["flowVenIn"]] #[m^3/s] or [kg/s]?
        self.input["flowVenOut"] = self.inputSender["flowVenOut"].output[self.inputSenderProperty["flowVenOut"]] #[m^3/s] or [kg/s]?
        if self.firstStep:
            self.output["ppmCO2"] = Settings.ppmCO2BuildingInitial
            self.firstStep = False
        else:
            occGen = self.input["occupants"] * self.CO2GenPerson * 1000000 / self.vol
            flow = self.input["flowVenIn"] / self.vol + self.airInf
            
            #A differential equation of type dy/dt=b-ay has the general solution y=(b+ce^(-at))/a. This solution is used to find the co2 concentration (y) at time (t) when y(0) is known:
            a = flow
            b = occGen + flow*Settings.ppmCO2Out
            
            #c at t=0 is c=y(0)-b/a
            c = self.output["ppmCO2"]*a-b
            
            t1 = self.timeStep
            y1 = (b + c*math.exp(-a*t1))/a
            self.output["ppmCO2"] = y1
            
            
        """self.output["ppmCO2"] = (self.output["ppmCO2"] * self.vol + 
                                self.input["ppmCO2Out"] * (self.input["flowVenIn"] + self.airInf) * self.timeStep + 
                                self.input["occupants"] * self.CO2GenPerson * 1000000 * self.timeStep) / (self.vol + (self.input["flowVenIn"] + self.airInf)*self.timeStep)"""

        # !!! include difference between flow in and out depending on infiltration
    