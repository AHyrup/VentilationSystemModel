class System:
    def __init__(self,
                 id = None,
                 subSystem = None,
                 systemType = None,
                 **kwargs):
        self.id = id
        self.subSystem = subSystem
        self.systemType = systemType