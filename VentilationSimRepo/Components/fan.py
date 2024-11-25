from Misc.settings import Settings

class Fan:
    def __init__(self,
                 id = None,
                 superSystem = None,
                 operationMode = None,
                 c1 = None,
                 c2 = None,
                 c3 = None,
                 c4 = None,
                 c5 = None,
                 flowMax = None,
                 WMax = None,
                 **kwargs):
        self.id = id
        self.superSystem = superSystem
        self.operationMode = operationMode
        self.c1 = c1
        self.c2 = c2
        self.c3 = c3
        self.c4 = c4
        self.c5 = c5
        self.flowMax = flowMax
        self.WMax = WMax
        
        self.input = {"flow": None} 
        self.output = {"W": None,
                       "Energy": 0}
        
    def doStep(self): #Calculate fan power consuption from fan specific constants and mass flow
        flow = 0
        for row in range(len(self.inputSender["flow"])):
            flow = flow + self.inputSender["flow"][row].output[self.inputSenderProperty["flow"][row]]
        self.input["flow"] = flow
    
        fFlow = self.input["flow"] / self.flowMax
        fpl = self.c1 + self.c2*fFlow + self.c3*fFlow**2 + self.c4*fFlow**3 + self.c5*fFlow**4
        W = fpl * self.WMax
        self.output["W"] = W
        self.output["Energy"] = self.output["Energy"] + W * Settings.timeStep