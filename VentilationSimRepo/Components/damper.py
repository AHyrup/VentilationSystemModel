class Damper:
    def __init__(self,
                 id = None,
                 containedIn = None,
                 superSystem = None,
                 operationMode = None,
                 flowMax=None,
                 **kwargs):
        self.id = id
        self.containedIn = containedIn
        self.superSystem = superSystem
        self.operationMode = operationMode
        self.containedIn = containedIn
        self.flowMax=flowMax
        
        self.input = {"posSignal": None}
        self.output = {"flow": None}

    def doStep(self): #supply flow capacity from ventilation [m^3/s] and supply damper postion (pos ∈ [0,1]) for a space. Returns air flow [m^3/s].
        self.input["posSignal"] = self.inputSender["posSignal"].output[self.inputSenderProperty["posSignal"]]
        
        self.output["flow"] = self.input["posSignal"] * self.flowMax

