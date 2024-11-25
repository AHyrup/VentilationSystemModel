import numpy as np
from gekko import GEKKO
#import matplotlib.pyplot as plt
from Misc.settings import Settings

class SystemMPC:
    def __init__(self,
                 id = None,
                 superSystem = None,
                 w1 = None,
                 w2 = None,
                 w3 = None,
                 **kwargs):
        self.id = id
        self.superSystem = superSystem
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        
        self.CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
        self.airInf = Settings.airInfSpace # [m^3/s]
        
        self.spaceList = []
        self.spaceVol = []
        self.nomFlowDamper = []
        self.ConstantsSupFan = None
        self.ConstantsExhFan = None
        self.nomFlowSupFan = None
        self.nomFlowExhFan = None
        self.nomWSupFan = None
        self.nomWExhFan = None
        self.model = None
        self.data = None
        self.mpcSteps = Settings.mpcSteps
        self.timeStep = Settings.timeStep
        self.mpcTimeStep = Settings.mpcTimeStep
        
        self.input = {"CO2": None,
                      "occ": None}
        self.output = {'outputSignal': None}
        self.step = 0
        
        self.results = {}
           
    def doStep(self):
        nSpaces = len(self.spaceList)
        
        for idx in range(nSpaces):
            self.input["CO2"][idx] = self.inputSender["CO2"][idx].output[self.inputSenderProperty["CO2"][idx]]
            self.input["occ"][idx] = self.inputSender["occ"][idx].output[self.inputSenderProperty["occ"][idx]]
        
        m = GEKKO()
        m.time = np.linspace(0,self.mpcTimeStep*self.mpcSteps,self.mpcSteps+1)
        
        idxList = np.arange(self.step, self.step+int(self.mpcTimeStep/self.timeStep)*(self.mpcSteps+1), int(self.mpcTimeStep/self.timeStep))
        self.idxList = idxList 
        
        # Param
        elPrice = m.Param(self.data['DKKPerMWh'].iloc[idxList].to_list())
        self.elPrice = elPrice
        if self.w3 != 0:
            emmImpact = m.Param(self.data['gCO2PerKWh'].iloc[idxList].to_list())
        occ = [None] * nSpaces
        for row in range(nSpaces):
            space = self.spaceList[row]
            occ[row] = m.Param(self.data[space].iloc[idxList].to_list())
            
        # Input
        pos = [None] * nSpaces
        for space in range(nSpaces):
            pos[space] = m.MV(lb=0, ub=1)
            pos[space].STATUS = 1
         
        # CV
        CO2 = [None] * nSpaces
        for space in range(nSpaces):
            CO2[space] = m.CV(self.input["CO2"][space])
        CO2Imp = m.CV(0)
        price = m.CV(0)
        cost = m.CV(0)
        if self.w3 != 0:
            emm = m.CV(0)
            totalEmm = m.CV(0)
        
        #State variables
        flowDamper = [None] * nSpaces
        for space in range(nSpaces):
            flowDamper[space] = m.SV(0)
        flowSupFan = m.SV(0, lb=0, ub=1)
        flowExhFan = m.SV(0, lb=0, ub=1)
        
        # Aux terms
        #plSupFan = m.Intermediate(self.ConstantsSupFan[0] + self.ConstantsSupFan[1]*flowSupFan + self.ConstantsSupFan[2]*flowSupFan**2 + self.ConstantsSupFan[3]*flowSupFan**3 + self.ConstantsSupFan[4]*flowSupFan**4)
        plSupFan = m.Intermediate(flowSupFan)
        wSupFan = m.Intermediate(plSupFan * self.nomWSupFan)
        #plExhFan = m.Intermediate(self.ConstantsExhFan[0] + self.ConstantsExhFan[1]*flowSupFan + self.ConstantsExhFan[2]*flowSupFan**2 + self.ConstantsSupFan[3]*flowExhFan**3 + self.ConstantsSupFan[4]*flowExhFan**4)
        plExhFan = m.Intermediate(flowExhFan)
        wExhFan = m.Intermediate(plExhFan * self.nomWExhFan)
        CO2ImpPerOcc = [None] * nSpaces
        CO2ImpSpace = [None] * nSpaces
        for space in range(nSpaces):
            #CO2ImpSpace[space] = m.Intermediate(CO2[space] * occ[space])
            CO2ImpPerOcc[space] = m.max2(CO2[space]-Settings.CO2Threshold,0)
            CO2ImpSpace[space] = m.Intermediate(CO2ImpPerOcc[space] * occ[space])
        
        #Equations
        for space in range(nSpaces):
            m.Equation(flowDamper[space] == pos[space]*self.nomFlowDamper[space])
            m.Equation(CO2[space].dt() == (occ[space]*self.CO2GenPerson*1000000-(self.nomFlowDamper[space]*pos[space]+self.airInf)*(CO2[space]-Settings.ppmCO2Out))/self.spaceVol[space])
        m.Equation(CO2Imp.dt() == sum(CO2ImpSpace))
        m.Equation(price == (wSupFan+wExhFan) * elPrice / (1000000*3600)) 
        m.Equation(cost.dt() == price)
        if self.w3 != 0:
            m.Equation(emm == (wSupFan+wExhFan) * emmImpact / (1000000*3600))
            m.Equation(totalEmm.dt() == emm)
        
        m.Equation(flowSupFan == sum(flowDamper)/self.nomFlowSupFan)
        m.Equation(flowExhFan == sum(flowDamper)/self.nomFlowExhFan)
        
        
        #Objective
        m.Obj(self.w1 * cost) #DKK 
        m.Obj(self.w2 * CO2Imp) #ppm*s*occ (above threshold)
        if self.w3 != 0:
            m.Obj(self.w3 * totalEmm) #kg CO2
        
        m.options.IMODE = 6 
        m.options.MAX_ITER = 5000
        m.options.SOLVER = 3
        
        try:
            m.solve(disp=True)
        
            # Store mpc data
            self.results['Cost'][:,self.step] = cost
            self.results['CO2Imp'][:,self.step] = CO2Imp
            self.results['stepPrice'][:,self.step] = price
            if self.w3 != 0:
                self.results['emm'][:,self.step] = emm
                self.results['totalEmm'][:,self.step] = totalEmm
            
            for idx in range(nSpaces):
                self.results['damperPos'][idx,:,self.step] = pos[idx]
                self.results['spaceCO2'][idx,:,self.step] = CO2[idx]
            
            for idx in range(nSpaces):
                self.output["outputSignal"][idx] = pos[idx][1] #self.input["CO2"][idx] * self.input["occ"][idx] / 10000
        except:
            if self.step == 0:
                for idx in range(nSpaces):
                    self.output["outputSignal"][idx] = 0
                    
            print(self.id + ' found no solution for optimizing damper control at step ' + str(self.step) + '. Damper positions for ' + self.superSystem + ' where set using fail-safe method.')
            
            """for idx in range(nSpaces):
                if self.input["CO2"][idx] > 600:
                    self.output["outputSignal"][idx] = 1
                else:
                    self.output["outputSignal"][idx] = 0"""
            
        self.step = self.step+1
            