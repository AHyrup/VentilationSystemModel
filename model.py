import os
import pandas as pd
import datetime as dt
import numpy as np
from datetime import datetime
from dateutil.tz import tzutc
from pytz import timezone
import math
import matplotlib.pyplot as plt
import openpyxl
import warnings
import time
from tabulate import tabulate

from Misc.settings import Settings
from Components.controller import Controller
from Components.fan import Fan
from Components.damper import Damper
from Components.system import System
from Components.sensor import Sensor
from Components.occupancy import Occupancy
from Components.systemMPC import SystemMPC

from Spaces.buildingSpace import BuildingSpace
from Spaces.outdoorEnvironment import OutdoorEnvironment

from Data.Occupancy.occDataConnect import OccDataConnect

class Model:
    def __init__(self,
                 configFile = None,
                 startTimeInput = None,
                 endTimeInput = None,    
                 discardStartup = False,
                 startupDuration = None,
                 occData = None,
                 createBuildingSpacePlots = False,
                 createMPCPlots = False,
                 createSystemPlots = False,
                 createBuildingPlots = False,
                 damperControlType = 'ruleSet',
                 occDiv = 'normalDiv',
                 occPredictionDiv = 'normalDiv',
                 saveResults = False,
                 outputName = 'defaultName',
                 simTimer = None,
                 mpcW1 = None,
                 mpcW2 = None,
                 mpcW3 = None,
                 **kwargs):
        self.projectPath = None
        self.elementDict = {}
        self.outputType = {}
        self.simResults = {}
        self.buildingResults = None
        
        self.configFile = configFile
        self.startTimeInput = startTimeInput
        self.endTimeInput = endTimeInput
        self.discardStartup = discardStartup
        self.startupDuration = startupDuration
        self.occData = occData
        self.createBuildingSpacePlots = createBuildingSpacePlots
        self.createMPCPlots = createMPCPlots
        self.createBuildingPlots = createBuildingPlots
        self.createSystemPlots = createSystemPlots
        self.damperControlType = damperControlType
        self.occDiv = occDiv
        self.occPredictionDiv = occPredictionDiv
        self.occPredictedData = None
        self.saveResults = saveResults
        self.outputName = outputName
        self.simTimer = simTimer
        self.mpcW1 = mpcW1
        self.mpcW2 = mpcW2
        self.mpcW3 = mpcW3

        self.dstSwitchDate = [[2019, 3, 31, 2, True], #year, month, day, hour, DST on? 
                             [2019, 10, 27, 2, False],
                             [2020, 3, 29, 2, True], 
                             [2020, 10, 25, 2, False],
                             [2021, 3, 28, 2, True], 
                             [2021, 10, 31, 2, False],
                             [2022, 3, 27, 2, True], 
                             [2022, 10, 30, 2, False],
                             [2023, 3, 26, 2, True], 
                             [2023, 10, 29, 2, False],
                             [2024, 3, 31, 2, True], 
                             [2024, 10, 27, 2, False]]
        
        if self.damperControlType == 'MPC':
            self.powerPredictions = None
            self.occPredictions = None
        
    def getProjectPath(self): #The project should be contained in a folder named VentilationSim
        projectPath = None
        level = os.getcwd()
        if level[-14:] == "VentilationSim":
            projectPath = level
        else:
            for levels in range(10):
                if os.path.dirname(level)[-14:] == "VentilationSim":
                    projectPath = os.path.dirname(level)
                    break
                else:
                    level = os.path.dirname(level)
        if projectPath == None:
            warnings.warn("Project directory not found")
        else:
            self.projectPath = projectPath
            
    def convertTimeFormat(self):
        self.startTime = dt.datetime(self.startTimeInput["year"], self.startTimeInput["month"], self.startTimeInput["day"], self.startTimeInput["hour"], self.startTimeInput["minute"], self.startTimeInput["second"], tzinfo=tzutc())
        self.endTime = dt.datetime(self.endTimeInput["year"], self.endTimeInput["month"], self.endTimeInput["day"], self.endTimeInput["hour"], self.endTimeInput["minute"], self.endTimeInput["second"], tzinfo=tzutc())
        self.timeStep = dt.timedelta(seconds=Settings.timeStep)
        
    def importConfig(self):
        path = self.projectPath
        fileName = self.configFile
        file = os.path.abspath(os.path.join(path, "Data", "Config", fileName))

        openpyxl.reader.excel.warnings.simplefilter(action='ignore')
        
        dfSystem = pd.read_excel(file, sheet_name="System")
        dfBuildingSpace = pd.read_excel(file, sheet_name="BuildingSpace")
        dfDamper = pd.read_excel(file, sheet_name="Damper")
        dfFan = pd.read_excel(file, sheet_name="Fan")
        dfController = pd.read_excel(file, sheet_name="Controller")
        dfSensor = pd.read_excel(file, sheet_name="Sensor")
        
        warnings.simplefilter('always', UserWarning)
        
        self.configDict = {"System": dfSystem,
                           "BuildingSpace": dfBuildingSpace.dropna(),
                           "Damper": dfDamper.dropna(),
                           "Fan": dfFan.dropna(),
                           "Controller": dfController.dropna(),
                           "Sensor": dfSensor.dropna()}
    
    def importPredictions(self):
        path = self.projectPath
        if self.occDiv == 'normalDiv':
            occFileName = 'config_OU44_600s_NormalDivOcc.csv'
        else:
            occFileName = 'config_OU44_600s_RoundedOcc.csv'
        occFile = os.path.abspath(os.path.join(path, "Misc", "DataProcessing", "OccPredictions", occFileName))
        occPredictedData = pd.read_csv(occFile)
        startIdx = None
        endIdx = None
        for idx in range(len(occPredictedData)):
            if occPredictedData['DateTime'][idx] == str(self.startTime):
                startIdx = idx
            if occPredictedData['DateTime'][idx] == str(self.endTime):
                endIdx = idx
        if self.startTime + self.timeStep * (endIdx-startIdx) == self.endTime:
            self.occPredictedData = occPredictedData.loc[startIdx:endIdx]
            self.occPredictedData.index = range(len(self.occPredictedData.index))
        else:
            warnings.warn('Missing or incorrect timesteps in occupancy prediction file: ' + occFile)
                    
        if self.damperControlType == "MPC":
            powerFileName = 'power_600s.csv'
            powerFile = os.path.abspath(os.path.join(path, "Misc", "DataProcessing", "PowerPredictions", powerFileName))
            powerPredictions = pd.read_csv(powerFile)
            startIdx = None
            endIdx = None
            for idx in range(len(powerPredictions)):
                if powerPredictions['DateTime'][idx] == str(self.startTime):
                    startIdx = idx
                if powerPredictions['DateTime'][idx] == str(self.endTime):
                    endIdx = idx
            if self.startTime + self.timeStep * (endIdx-startIdx) == self.endTime:
                self.powerPredictions = powerPredictions.loc[startIdx:endIdx+Settings.mpcSteps*int(Settings.mpcTimeStep/Settings.timeStep)]
                self.powerPredictions.index = range(len(self.powerPredictions.index))
            else:
                warnings.warn('Missing or incorrect timesteps in power prediction file: ' + powerFile)
            
            if self.occPredictionDiv == 'normalDiv':
                occPredFileName = 'config_OU44_600s_NormalDivOcc.csv'
            else:
                occPredFileName = 'config_OU44_600s_RoundedOcc.csv'
            occPredFile = os.path.abspath(os.path.join(path, "Misc", "DataProcessing", "OccPredictions", occPredFileName))
            occPredictions = pd.read_csv(occPredFile)
            startIdx = None
            endIdx = None
            for idx in range(len(occPredictions)):
                if occPredictions['DateTime'][idx] == str(self.startTime):
                    startIdx = idx
                if occPredictions['DateTime'][idx] == str(self.endTime):
                    endIdx = idx
            if self.startTime + self.timeStep * (endIdx-startIdx) == self.endTime:
                self.occPredictions = occPredictions.loc[startIdx:endIdx+Settings.mpcSteps*int(Settings.mpcTimeStep/Settings.timeStep)]
                self.occPredictions.index = range(len(self.occPredictions.index))
            else:
                warnings.warn('Missing or incorrect timesteps in occupancy prediction file: ' + occPredFile)
              
    def createElementDicts(self):
        for key in self.configDict:
            self.elementDict[key] = {}
        self.elementDict["OutdoorEnvironment"] = {}
        self.elementDict["Occupancy"] = {}
        if self.damperControlType == "MPC":
            self.elementDict["SystemMPC"] = {}
        
    def addElement(self, element):
        try:
            self.elementDict[type(element).__name__][element.id] = element
        except:
            warnings.warn("Failed to add " + element.id + " to elementDict")
        
    def addOutdoorEnvironment(self):
        outEnv = OutdoorEnvironment(id="Outdoor environment")
        self.addElement(outEnv)
        
    def initiateElements(self): 
        for sysName in self.configDict["System"]["Ventilation system name"].dropna():
            sys = System(id=sysName, systemType="ventilationSystem", subSystem=[])
            self.addElement(sys)
            if self.damperControlType == "MPC":
                MPC = SystemMPC(id=sysName + " MPC", superSystem=sysName, w1=self.mpcW1, w2=self.mpcW2, w3=self.mpcW3)
                self.addElement(MPC)
        
        spaceRows = self.configDict["BuildingSpace"].shape[0]
        for rowLoc in range(spaceRows):
            row = self.configDict["BuildingSpace"].iloc[rowLoc]
            buildingSpace = BuildingSpace(id=row["id"], vol=row["airVolume"], name=row["name"], ventilationSystem=row['ventilationSystem'], contains=[])
            self.addElement(buildingSpace)
            if self.occData != None:
                occConnectDict = getattr(OccDataConnect, self.occData)
                foundData = False
                for key in occConnectDict:
                    if buildingSpace.name == key:
                        occDataFile = occConnectDict[key]
                        foundData = True
                        occupancy = Occupancy(id=row["id"] + " occupancy", containedIn=row["id"], ventilationSystem=row['ventilationSystem'], dataFile=occDataFile)
                        break
                if foundData == False:
                    occupancy = Occupancy(id=row["id"] + " occupancy", containedIn=row["id"], ventilationSystem=row['ventilationSystem'])
            elif type(self.occPredictedData) != 'NoneType':
                spaceName = row["id"]
                data = self.occPredictedData[spaceName]
                occupancy = Occupancy(id=row["id"] + " occupancy", containedIn=row["id"], ventilationSystem=row['ventilationSystem'], scheduleFromData=data)
            else:
                occupancy = Occupancy(id=row["id"] + " occupancy", containedIn=row["id"], ventilationSystem=row['ventilationSystem'])
            self.addElement(occupancy)
        
        damperRows = self.configDict["Damper"].shape[0]
        for rowLoc in range(damperRows):
            row = self.configDict["Damper"].iloc[rowLoc]
            damper = Damper(id=row["id"], flowMax = row["nominalAirFlowRate"], superSystem=row["subSystemOf"], containedIn=row["isContainedIn"], operationMode=row["operationMode"])
            self.addElement(damper)
            
        fanRows = self.configDict["Fan"].shape[0]    
        for rowLoc in range(fanRows):
            row = self.configDict["Fan"].iloc[rowLoc]
            fan = Fan(id=row["id"], flowMax=row["nominalAirFlowRate"], WMax=row["nominalPowerRate"], c1=row["c1"], c2=row["c2"], c3=row["c3"], c4=row["c4"], c5=row["c5"], operationMode=row["operationMode"], superSystem=row["subSystemOf"])
            self.addElement(fan)
        
        controllerRows = self.configDict["Controller"].shape[0]
        for rowLoc in range(controllerRows):
            row = self.configDict["Controller"].iloc[rowLoc]
            controller = Controller(id=row["id"], controlsElementType=row["controlsElementType"], superSystem=row["subSystemOf"], containedIn=row["isContainedIn"], controlType=self.damperControlType, startTime=self.startTime)
            self.addElement(controller)
            
        sensorRows = self.configDict["Sensor"].shape[0]
        for rowLoc in range(sensorRows):
            row = self.configDict["Sensor"].iloc[rowLoc]
            sensor = Sensor(id=row["id"], measuresProperty=row["measuresProperty"], containedIn=row["isContainedIn"])
            self.addElement(sensor)
            
    def importElementData(self):
        for occupancy in self.elementDict["Occupancy"]:
            if self.elementDict["Occupancy"][occupancy].dataFile != None:
                self.elementDict["Occupancy"][occupancy].data = pd.read_csv(self.projectPath + '\\Data\\Occupancy\\' + self.elementDict["Occupancy"][occupancy].dataFile)
                dateFormat = getattr(OccDataConnect, self.occData)['dateFormat']
                dateTimes = []
                for row in range(len(self.elementDict["Occupancy"][occupancy].data)):
                    dateTime = datetime.strptime(self.elementDict["Occupancy"][occupancy].data['Timestamp'][row], dateFormat)
                    dateTime = dateTime.replace(tzinfo=tzutc())
                    dateTimes.append(dateTime)
                self.elementDict["Occupancy"][occupancy].data.insert(2, 'DateTime', dateTimes)
                
    def addRelations(self):
        for subElementDict in self.elementDict:
            for element in self.elementDict[subElementDict]:
                if hasattr(self.elementDict[subElementDict][element], "superSystem"):
                    if self.elementDict[subElementDict][element].superSystem in self.elementDict["System"].keys():
                        self.elementDict["System"][self.elementDict[subElementDict][element].superSystem].subSystem.append(self.elementDict[subElementDict][element].id) 
                    else:
                        warnings.warn("Supersystem for " + self.elementDict[subElementDict][element].id + " not found in element dictionary")                   
                if hasattr(self.elementDict[subElementDict][element], "containedIn"):
                    if self.elementDict[subElementDict][element].containedIn in self.elementDict["BuildingSpace"].keys():
                        self.elementDict["BuildingSpace"][self.elementDict[subElementDict][element].containedIn].contains.append(self.elementDict[subElementDict][element].id) 
                    else:
                        warnings.warn("Containing space for " + self.elementDict[subElementDict][element].id + " not found in element dictionary")
                if hasattr(self.elementDict[subElementDict][element], "input"):
                    self.elementDict[subElementDict][element].connection = []
                    self.elementDict[subElementDict][element].inputSender = {}
                    self.elementDict[subElementDict][element].inputSenderProperty = {}
        
    def dstCheck(self, timeStamp): # account for daylight savings  
        dst = False
        index = -1
        for idx in range(len(self.dstSwitchDate)):
            if timeStamp > dt.datetime(self.dstSwitchDate[idx][0], self.dstSwitchDate[idx][1], self.dstSwitchDate[idx][2], self.dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc()):
                dst = self.dstSwitchDate[idx][4]
                index = idx
        return dst, index
    
    def createTimesteps(self):
        startNoDst = self.startTime
        endNoDst = self.endTime
        startDst, startIdx = self.dstCheck(self.startTime)
        endDst, endIdx = self.dstCheck(self.endTime)
        if startDst:
            startNoDst = self.startTime-dt.timedelta(hours=1)
        if endDst:
            endNoDst = self.endTime-dt.timedelta(hours=1)
        
        simDuration = endNoDst - startNoDst
        self.steps = math.floor(simDuration/self.timeStep) + 1
        timeSteps = []
        
        idx = startIdx + 1 
        dst = startDst # True or false
        nextDstChange = datetime(self.dstSwitchDate[idx][0], self.dstSwitchDate[idx][1], self.dstSwitchDate[idx][2], self.dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc())
        for step in range(self.steps):
            timestamp = startNoDst+step*self.timeStep
            if timestamp >= nextDstChange:
                dst = self.dstSwitchDate[idx][4]
                idx = idx + 1
                nextDstChange = datetime(self.dstSwitchDate[idx][0], self.dstSwitchDate[idx][1], self.dstSwitchDate[idx][2], self.dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc())
            if dst:
                timeSteps.append(timestamp+dt.timedelta(hours=1))
            else:
                timeSteps.append(timestamp)
            
        self.simResults["DateTime"] = pd.DataFrame({"DateTime": timeSteps})
        for occupancy in self.elementDict["Occupancy"]:
            self.elementDict["Occupancy"][occupancy].dateTimeDf = pd.DataFrame({"DateTime": timeSteps})
            if self.elementDict["Occupancy"][occupancy].dataFile != None:
                self.elementDict["Occupancy"][occupancy].scheduleFromData = pd.merge(self.elementDict["Occupancy"][occupancy].dateTimeDf, self.elementDict["Occupancy"][occupancy].data, how='inner', on='DateTime')
                if len(self.elementDict["Occupancy"][occupancy].scheduleFromData) != len(self.elementDict["Occupancy"][occupancy].dateTimeDf):
                    warnings.warn("The occupancy schedule for " + self.elementDict["Occupancy"][occupancy].containedIn + " is incomplete")
    
    def addConnectionConfig(self, reciever, sender, recieverProperty, senderProperty):
        newConnection = {"reciever": reciever, "sender": sender, "recieverProperty": recieverProperty, "senderProperty": senderProperty}
        reciever.connection.append(newConnection)
        
    def generateConnectionConfig(self):
        for sensor in self.elementDict["Sensor"]:
            if self.elementDict["Sensor"][sensor].measuresProperty == "CO2":
                buildingSpace = self.elementDict["BuildingSpace"][self.elementDict["Sensor"][sensor].containedIn] 
                self.addConnectionConfig(self.elementDict["Sensor"][sensor], buildingSpace, "value", "ppmCO2")
                
        if self.damperControlType == "MPC":
            for systemMPC in self.elementDict['SystemMPC']:
                for sensor in self.elementDict["Sensor"]: 
                    sensorSpace = self.elementDict['Sensor'][sensor].containedIn
                    if self.elementDict['BuildingSpace'][sensorSpace].ventilationSystem == self.elementDict['SystemMPC'][systemMPC].superSystem:
                        self.addConnectionConfig(self.elementDict['SystemMPC'][systemMPC], self.elementDict['Sensor'][sensor], 'CO2', 'value')
                for occupancy in self.elementDict['Occupancy']:
                    if self.elementDict['Occupancy'][occupancy].ventilationSystem == self.elementDict['SystemMPC'][systemMPC].superSystem:
                        self.addConnectionConfig(self.elementDict['SystemMPC'][systemMPC], self.elementDict['Occupancy'][occupancy], 'occ', 'occupants')
                
        for controller in self.elementDict["Controller"]:
            if self.elementDict["Controller"][controller].controlsElementType == "damper":
                if self.damperControlType == "MPC":
                    foundMPC = False
                    for systemMPC in self.elementDict["SystemMPC"]: 
                        if self.elementDict["SystemMPC"][systemMPC].superSystem == self.elementDict["Controller"][controller].superSystem:
                            self.addConnectionConfig(self.elementDict["Controller"][controller], self.elementDict['SystemMPC'][systemMPC], "inputValue", "outputSignal")
                            foundMPC = True
                            break
                    if foundMPC == False:
                        warnings.warn("No MPC found for " + self.elementDict["Controller"][controller].id)
                else:
                    foundSensor = False
                    for sensor in self.elementDict["Sensor"]: 
                        if self.elementDict["Sensor"][sensor].containedIn == self.elementDict["Controller"][controller].containedIn:
                            self.addConnectionConfig(self.elementDict["Controller"][controller], self.elementDict["Sensor"][sensor], "inputValue", "value")
                            foundSensor = True
                            break
                    if foundSensor == False:
                        warnings.warn("No sensor found for " + self.elementDict["Controller"][controller].id)
        
        for damper in self.elementDict["Damper"]:
            foundController = False
            for controller in self.elementDict["Controller"]:
                if self.elementDict["Controller"][controller].containedIn == self.elementDict["Damper"][damper].containedIn and self.elementDict["Controller"][controller].controlsElementType == "damper":
                    self.addConnectionConfig(self.elementDict["Damper"][damper], self.elementDict["Controller"][controller], "posSignal", "outputSignal")
                    foundController = True
                    break
            if foundController == False:
                warnings.warn("No controller found for " + self.elementDict["Damper"][damper].id)
                
        for buildingSpace in self.elementDict["BuildingSpace"]:
            for damper in self.elementDict["Damper"]:
                if self.elementDict["Damper"][damper].containedIn == self.elementDict["BuildingSpace"][buildingSpace].id:
                    if self.elementDict["Damper"][damper].operationMode == "supply":
                        self.addConnectionConfig(self.elementDict["BuildingSpace"][buildingSpace], self.elementDict["Damper"][damper], "flowVenIn", "flow")
                    elif self.elementDict["Damper"][damper].operationMode == "exhaust":
                        self.addConnectionConfig(self.elementDict["BuildingSpace"][buildingSpace], self.elementDict["Damper"][damper], "flowVenOut", "flow")
            for occupancy in self.elementDict["Occupancy"]:
                if self.elementDict["Occupancy"][occupancy].containedIn == self.elementDict["BuildingSpace"][buildingSpace].id:
                    self.addConnectionConfig(self.elementDict["BuildingSpace"][buildingSpace], self.elementDict["Occupancy"][occupancy], "occupants", "occupants")
        
        for fan in self.elementDict["Fan"]:
            for damper in self.elementDict["Damper"]:
                if self.elementDict["Fan"][fan].superSystem == self.elementDict["Damper"][damper].superSystem and self.elementDict["Fan"][fan].operationMode == self.elementDict["Damper"][damper].operationMode:
                    self.addConnectionConfig(self.elementDict["Fan"][fan], self.elementDict["Damper"][damper], "partialFlow", "flow")
                    
    def setupMPCUtility(self):
        for systemMPC in self.elementDict['SystemMPC']:
            self.elementDict['SystemMPC'][systemMPC].data = pd.DataFrame(self.occPredictions['DateTime'])
            self.elementDict['SystemMPC'][systemMPC].data.insert(1, 'DKKPerMWh', self.powerPredictions['DKKPerMWh'])
            self.elementDict['SystemMPC'][systemMPC].data.insert(2, 'gCO2PerKWh', self.powerPredictions['gCO2PerKWh'])
            for connect in range(len(self.elementDict['SystemMPC'][systemMPC].connection)):
                if type(self.elementDict['SystemMPC'][systemMPC].connection[connect]['sender']).__name__ == "Occupancy":
                    space = self.elementDict['SystemMPC'][systemMPC].connection[connect]['sender'].containedIn
                    self.elementDict['SystemMPC'][systemMPC].spaceList.append(space)
                    self.elementDict['SystemMPC'][systemMPC].data.insert(len(self.elementDict['SystemMPC'][systemMPC].spaceList)+2, space, self.occPredictions[space])
                    for buildingSpace in self.elementDict['BuildingSpace']:
                        if buildingSpace == space:
                            self.elementDict['SystemMPC'][systemMPC].spaceVol.append(self.elementDict['BuildingSpace'][buildingSpace].vol)
                    for damper in self.elementDict['Damper']:
                        if self.elementDict['Damper'][damper].operationMode == 'supply':
                            if self.elementDict['Damper'][damper].containedIn == space:
                                self.elementDict['SystemMPC'][systemMPC].nomFlowDamper.append(self.elementDict['Damper'][damper].flowMax)  
            self.elementDict['SystemMPC'][systemMPC].input['CO2'] = [None] * len(self.elementDict['SystemMPC'][systemMPC].spaceList)
            self.elementDict['SystemMPC'][systemMPC].input['occ'] = [None] * len(self.elementDict['SystemMPC'][systemMPC].spaceList)
            self.elementDict['SystemMPC'][systemMPC].output['outputSignal'] = [None] * len(self.elementDict['SystemMPC'][systemMPC].spaceList)
            
            for fan in self.elementDict['Fan']:
                if self.elementDict['Fan'][fan].superSystem == self.elementDict['SystemMPC'][systemMPC].superSystem:
                    if self.elementDict['Fan'][fan].operationMode == 'supply':
                        self.elementDict['SystemMPC'][systemMPC].ConstantsSupFan = [self.elementDict['Fan'][fan].c1, 
                                                                                    self.elementDict['Fan'][fan].c2,
                                                                                    self.elementDict['Fan'][fan].c3,
                                                                                    self.elementDict['Fan'][fan].c4]
                        self.elementDict['SystemMPC'][systemMPC].nomFlowSupFan = self.elementDict['Fan'][fan].flowMax   
                        self.elementDict['SystemMPC'][systemMPC].nomWSupFan = self.elementDict['Fan'][fan].WMax
                    if self.elementDict['Fan'][fan].operationMode == 'exhaust':
                        self.elementDict['SystemMPC'][systemMPC].ConstantsExhFan = [self.elementDict['Fan'][fan].c1, 
                                                                                    self.elementDict['Fan'][fan].c2,
                                                                                    self.elementDict['Fan'][fan].c3,
                                                                                    self.elementDict['Fan'][fan].c4]
                        self.elementDict['SystemMPC'][systemMPC].nomFlowExhFan = self.elementDict['Fan'][fan].flowMax   
                        self.elementDict['SystemMPC'][systemMPC].nomWExhFan = self.elementDict['Fan'][fan].WMax       
            
            nSpaces = len(self.elementDict['SystemMPC'][systemMPC].spaceList)
            mpcSteps = Settings.mpcSteps
            simSteps = self.steps
            self.elementDict['SystemMPC'][systemMPC].results['Cost'] = np.zeros((mpcSteps+1,simSteps))
            self.elementDict['SystemMPC'][systemMPC].results['CO2Imp'] = np.zeros((mpcSteps+1,simSteps))
            self.elementDict['SystemMPC'][systemMPC].results['emm'] = np.zeros((mpcSteps+1,simSteps))
            self.elementDict['SystemMPC'][systemMPC].results['totalEmm'] = np.zeros((mpcSteps+1,simSteps))
            self.elementDict['SystemMPC'][systemMPC].results['stepPrice'] = np.zeros((mpcSteps+1,simSteps))
            self.elementDict['SystemMPC'][systemMPC].results['damperPos'] = np.zeros((nSpaces,mpcSteps+1,simSteps))                                            
            self.elementDict['SystemMPC'][systemMPC].results['spaceCO2'] = np.zeros((nSpaces,mpcSteps+1,simSteps))      
  
    def connectElements(self): # For easy model scaling this function should be generalised to treat all types of elements at once
        for sensor in self.elementDict["Sensor"]:
            if self.elementDict["Sensor"][sensor].measuresProperty == "CO2":
                self.elementDict["Sensor"][sensor].inputSender["value"] = self.elementDict["Sensor"][sensor].connection[0]["sender"]
                self.elementDict["Sensor"][sensor].inputSenderProperty["value"] = self.elementDict["Sensor"][sensor].connection[0]["senderProperty"]

        for controller in self.elementDict["Controller"]:
            self.elementDict["Controller"][controller].inputSender["inputValue"] = self.elementDict["Controller"][controller].connection[0]["sender"]
            if self.damperControlType == 'MPC':
                foundSpace = False
                for idx in range(len(self.elementDict["Controller"][controller].inputSender["inputValue"].spaceList)):
                    if self.elementDict["Controller"][controller].inputSender["inputValue"].spaceList[idx] == self.elementDict["Controller"][controller].containedIn:
                        self.elementDict["Controller"][controller].inputSenderProperty["inputValue"] = [self.elementDict["Controller"][controller].connection[0]["senderProperty"], idx]
                        foundSpace = True
                        break
                if foundSpace == False:
                    warnings.warn("Failed to connect MPC to " + self.elementDict['Controller'][controller].id)
            else:
                self.elementDict["Controller"][controller].inputSenderProperty["inputValue"] = self.elementDict["Controller"][controller].connection[0]["senderProperty"]
  
        for damper in self.elementDict["Damper"]:
            self.elementDict["Damper"][damper].inputSender["posSignal"] = self.elementDict["Damper"][damper].connection[0]["sender"]
            self.elementDict["Damper"][damper].inputSenderProperty["posSignal"] = self.elementDict["Damper"][damper].connection[0]["senderProperty"]
           
        for buildingSpace in self.elementDict["BuildingSpace"]:
            for key in self.elementDict["BuildingSpace"][buildingSpace].input:
                for connect in range(len(self.elementDict["BuildingSpace"][buildingSpace].connection)):
                    if key == self.elementDict["BuildingSpace"][buildingSpace].connection[connect]["recieverProperty"]:
                        self.elementDict["BuildingSpace"][buildingSpace].inputSender[key] = self.elementDict["BuildingSpace"][buildingSpace].connection[connect]["sender"]
                        self.elementDict["BuildingSpace"][buildingSpace].inputSenderProperty[key] = self.elementDict["BuildingSpace"][buildingSpace].connection[connect]["senderProperty"]
                        
        for fan in self.elementDict["Fan"]:
            self.elementDict["Fan"][fan].inputSender["flow"] = []
            self.elementDict["Fan"][fan].inputSenderProperty["flow"] = []
            for connect in range(len(self.elementDict["Fan"][fan].connection)):
                self.elementDict["Fan"][fan].inputSender["flow"].append(self.elementDict["Fan"][fan].connection[connect]["sender"])
                self.elementDict["Fan"][fan].inputSenderProperty["flow"].append(self.elementDict["Fan"][fan].connection[connect]["senderProperty"])
                     
        if self.damperControlType == "MPC":
            for systemMPC in self.elementDict['SystemMPC']:
                self.elementDict["SystemMPC"][systemMPC].inputSender["CO2"] = [None] * len(self.elementDict["SystemMPC"][systemMPC].spaceList)
                self.elementDict["SystemMPC"][systemMPC].inputSenderProperty["CO2"] = [None] * len(self.elementDict["SystemMPC"][systemMPC].spaceList)
                self.elementDict["SystemMPC"][systemMPC].inputSender["occ"] = [None] * len(self.elementDict["SystemMPC"][systemMPC].spaceList)
                self.elementDict["SystemMPC"][systemMPC].inputSenderProperty["occ"] = [None] * len(self.elementDict["SystemMPC"][systemMPC].spaceList)
                for connect in range(len(self.elementDict["SystemMPC"][systemMPC].connection)):
                    foundSpace = False
                    if self.elementDict["SystemMPC"][systemMPC].connection[connect]["recieverProperty"] == "CO2":
                        for idx in range(len(self.elementDict["SystemMPC"][systemMPC].spaceList)):
                            if self.elementDict["SystemMPC"][systemMPC].spaceList[idx] == self.elementDict["SystemMPC"][systemMPC].connection[connect]["sender"].containedIn:
                                self.elementDict["SystemMPC"][systemMPC].inputSender["CO2"][idx] = self.elementDict["SystemMPC"][systemMPC].connection[connect]["sender"]
                                self.elementDict["SystemMPC"][systemMPC].inputSenderProperty["CO2"][idx] = self.elementDict["SystemMPC"][systemMPC].connection[connect]["senderProperty"]
                                foundSpace = True
                                break
                    elif self.elementDict["SystemMPC"][systemMPC].connection[connect]["recieverProperty"] == "occ":
                        foundSpace = False
                        for idx in range(len(self.elementDict["SystemMPC"][systemMPC].spaceList)):
                            if self.elementDict["SystemMPC"][systemMPC].spaceList[idx] == self.elementDict["SystemMPC"][systemMPC].connection[connect]["sender"].containedIn:
                                self.elementDict["SystemMPC"][systemMPC].inputSender["occ"][idx] = self.elementDict["SystemMPC"][systemMPC].connection[connect]["sender"]
                                self.elementDict["SystemMPC"][systemMPC].inputSenderProperty["occ"][idx] = self.elementDict["SystemMPC"][systemMPC].connection[connect]["senderProperty"]
                                foundSpace = True
                                break
                    if foundSpace == False:
                        warnings.warn(self.elementDict["SystemMPC"][systemMPC].connection['sender'].containedIn + ' (containing ' + self.elementDict["SystemMPC"][systemMPC].connection['sender'].id + ') was not found in the list of spaces for ' + self.elementDict["SystemMPC"][systemMPC].id)

    def outputDfSetup(self):
        for subElementDict in self.elementDict:
            if subElementDict != 'OutdoorEnvironment':
                outputNames = []
                for element in self.elementDict[subElementDict]:
                    if hasattr(self.elementDict[subElementDict][element], "output"):
                        if subElementDict == "SystemMPC":
                            for idx in range(len(self.elementDict[subElementDict][element].output['outputSignal'])):
                                outputNames.append(self.elementDict[subElementDict][element].id + ': outputSignal ' + self.elementDict[subElementDict][element].spaceList[idx])
                        else:
                            for row in self.elementDict[subElementDict][element].output:
                                outputNames.append(self.elementDict[subElementDict][element].id + ": " + row)
                self.outputType[subElementDict] = outputNames
    
        for list in self.outputType:
            self.simResults[list] = pd.DataFrame(index=range(self.steps), columns=self.outputType[list])
                                   
    def simulationSetup(self): #Run all function needed for model setup
        if self.simTimer != False:
            self.simStart = time.time()
        print("Preparing simulation setup...")
        self.getProjectPath()
        self.convertTimeFormat()
        self.importConfig()
        self.importPredictions()
        self.createElementDicts()
        self.addOutdoorEnvironment()
        self.initiateElements()
        self.importElementData()
        self.addRelations()
        self.createTimesteps()
        self.generateConnectionConfig()
        if self.damperControlType == "MPC":
            self.setupMPCUtility()
        self.connectElements()
        self.outputDfSetup()
        print("Simulation setup complete.")
            
    def runSimulation(self):
        #Simulation order: occupancy -> CO2sensor -> (MPC) -> damperController -> damper -> buildingSpace -> fan
        print("Starting simulation...")
        simCount = 0
        
        for step in range(self.steps): # Run step for all elements 
            if self.simTimer != None:
                if simCount % self.simTimer == 0 :
                    if simCount == 0:
                        start = time.time()
                    else:
                        end = time.time()
                        duration = end-start
                        print('Simulations of timesteps ' + str(simCount-self.simTimer+1) + '-' + str(simCount) + ' complete. Duration: ' + str(duration) + ' seconds.')
                        start = time.time()
                        
            occupancyOutputs = []    
            sensorOutputs = []
            if self.damperControlType == 'MPC':
                systemMPCOutputs = []
            controllerOutputs = []
            damperOutputs = []
            buildingSpaceOutputs = []
            fanOutputs = []

            for occupancy in self.elementDict["Occupancy"]:
                self.elementDict["Occupancy"][occupancy].doStep()
                occupancyOutputs.append( self.elementDict["Occupancy"][occupancy].output["occupants"])
            
            for sensor in self.elementDict["Sensor"]:
                self.elementDict["Sensor"][sensor].doStep()
                sensorOutputs.append(self.elementDict["Sensor"][sensor].output["value"])
                
            if self.damperControlType == 'MPC':
                for systemMPC in self.elementDict['SystemMPC']:
                    self.elementDict["SystemMPC"][systemMPC].doStep()
                    for idx in range(len(self.elementDict["SystemMPC"][systemMPC].spaceList)):
                        systemMPCOutputs.append(self.elementDict["SystemMPC"][systemMPC].output['outputSignal'][idx])
                    
            for controller in self.elementDict["Controller"]:
                self.elementDict["Controller"][controller].doStep()
                controllerOutputs.append(self.elementDict["Controller"][controller].output["outputSignal"])
                    
            for damper in self.elementDict["Damper"]:
                self.elementDict["Damper"][damper].doStep()
                damperOutputs.append(self.elementDict["Damper"][damper].output["flow"])
                
            for buildingSpace in self.elementDict["BuildingSpace"]:
                self.elementDict["BuildingSpace"][buildingSpace].doStep()
                buildingSpaceOutputs.append(self.elementDict["BuildingSpace"][buildingSpace].output["ppmCO2"])
                    
            for fan in self.elementDict["Fan"]:
                self.elementDict["Fan"][fan].doStep()
                fanOutputs.append(self.elementDict["Fan"][fan].output["W"])
                fanOutputs.append(self.elementDict["Fan"][fan].output["Energy"])
                
            # Store data after running step
            self.simResults["Occupancy"].iloc[simCount] = occupancyOutputs
            self.simResults["Sensor"].iloc[simCount] = sensorOutputs
            if self.damperControlType == 'MPC':
                self.simResults['SystemMPC'].iloc[simCount] = systemMPCOutputs
            self.simResults["Controller"].iloc[simCount] = controllerOutputs
            self.simResults["Damper"].iloc[simCount] = damperOutputs
            self.simResults["BuildingSpace"].iloc[simCount] = buildingSpaceOutputs
            self.simResults["Fan"].iloc[simCount] = fanOutputs
            
            simCount = simCount + 1
            
        if self.discardStartup == True:
            discardedSteps = math.ceil(self.startupDuration/Settings.timeStep)
            for elementResults in self.simResults:
                self.simResults[elementResults] = self.simResults[elementResults].iloc[discardedSteps:]
        print("Simulation complete")
        
    def myRound(self, x, base):
        return base * round(x/base)
    
    def myCeil(self, x, base):
        return base * math.ceil(x/base)
    
    def calculateTotals(self):
        path = self.projectPath
        fileName = 'power_600s.csv'
        file = os.path.abspath(os.path.join(path, 'Misc', 'DataProcessing', 'PowerPredictions', fileName))
        
        df = pd.read_csv(file, sep=',')
        
        startIdx = None
        endIdx = None
        startup = 0
        if self.discardStartup:
            startup = int(self.startupDuration/self.timeStep.seconds)
        
        for idx in range(len(df)):
            if df['DateTime'][idx] == str(self.startTime):
                    startIdx = idx + startup
            if df['DateTime'][idx] == str(self.endTime):
                endIdx = idx
        powerDf = df.loc[startIdx:endIdx]
        powerDf.index = range(len(powerDf.index))
        
        price = powerDf['DKKPerMWh'] 
        emmFactor = powerDf['gCO2PerKWh']
        power = []
        el = []
        cost = []
        totCost = []
        emm = []
        totEmm = []
        for idx in range(len(powerDf)):
            powerSum = 0
            for key in self.simResults['Fan']:
                if key[-1] == 'W':
                    powerSum = powerSum + self.simResults['Fan'][key][idx+startup]
            power.append(powerSum)
            cost.append(powerSum*price[idx]*self.timeStep.seconds/(3600*1000000))
            emm.append(powerSum*emmFactor[idx]*self.timeStep.seconds/(3600*1000000))
            if idx == 0 :
                el.append(powerSum*self.timeStep.seconds/(3600*1000)) #kWh
                totCost.append(cost[idx])
                totEmm.append(emm[idx])
            else:
                el.append(el[idx-1]+powerSum*self.timeStep.seconds/(3600*1000))
                totCost.append(totCost[idx-1]+cost[idx])
                totEmm.append(totEmm[idx-1]+emm[idx])
        
        d = {'DKKPerMWh': price, 'gCO2PerKWh': emmFactor, 'powerW': power, 'el': el,
             'cost': cost, 'totCost': totCost, 'kgCO2emm': emm, 'totCO2emm': totEmm}
        self.buildingResults = pd.DataFrame(data=d)
                        
    def plotSettings(self):
        self.ymargin = 0.05
        
    def clacAirKPI(self):
        self.KPI = 0
        for space in self.elementDict["BuildingSpace"]:
            KPIspace = 0 # [ppm*s*occ] where ppm is the positive difference between concentration and threshold in timesteps where CO2 concentration is above threshold
            for step in range(self.simResults['Sensor'].index.start, self.simResults['Sensor'].index.stop):
                if self.simResults["BuildingSpace"][space + ": ppmCO2"][step] > Settings.CO2Threshold:
                    KPIspace = KPIspace + ((self.simResults["BuildingSpace"][space + ": ppmCO2"][step]-Settings.CO2Threshold) * Settings.timeStep * self.simResults["Occupancy"][space + " occupancy: occupants"][step])
            self.KPI = self.KPI + KPIspace  
          
    def SpacePlots(self):
        for space in self.elementDict["BuildingSpace"]:    
            
            # Figure setup
            fig, ax = plt.subplots()
            plt.suptitle(self.elementDict["BuildingSpace"][space].name)
            fig.set_figheight(6)
            fig.set_figwidth(10)
            fig.subplots_adjust(right=0.9)
            twin1 = ax.twinx()
            twin2 = ax.twinx()
            twin2.spines.right.set_position(("axes", 1.12))
            
            # data
            dateTime = self.simResults["DateTime"]["DateTime"]
            co2 = self.simResults["BuildingSpace"][space + ": ppmCO2"]
            occupancy = self.simResults["Occupancy"][space + " occupancy: occupants"]
            for damper in self.elementDict["Damper"]:
                if self.elementDict["Damper"][damper].containedIn == space:
                    spaceDamper = damper
                    break
            damperOpening = self.simResults["Damper"][spaceDamper + ": flow"]/self.elementDict['Damper'][spaceDamper].flowMax
            
            #plot
            p1, = ax.plot(dateTime, co2, "b-", label="CO2")
            p2, = twin1.plot(dateTime, occupancy, "r-", label="Occupancy") 
            p3, = twin2.plot(dateTime, damperOpening, "g-", label="Damper") 
            
            ax.set_xlabel("Time")
            ax.set_ylabel("CO2 [ppm]")
            twin1.set_ylabel("Occupants")
            twin2.set_ylabel("Damper opening ")
            
            ax.yaxis.label.set_color(p1.get_color())
            twin1.yaxis.label.set_color(p2.get_color())
            twin2.yaxis.label.set_color(p3.get_color())
            
            ax.tick_params(axis='y', colors=p1.get_color())
            twin1.tick_params(axis='y', colors=p2.get_color())
            twin2.tick_params(axis='y', colors=p3.get_color())
            
            ax.legend(handles=[p1, p2, p3], loc="upper right")
            
            # Axis setup
            co2MaxTick = self.myRound(max(co2), 50)
            co2MinTick = Settings.ppmCO2Out
            if co2MaxTick-co2MinTick != 0:
                if (max(co2)-co2MinTick)/(co2MaxTick-co2MinTick) > (1+self.ymargin):
                    co2MaxTick = self.myCeil(max(co2), 50)
            co2TickRange = co2MaxTick-co2MinTick
            ax.set_ylim(co2MinTick-self.ymargin*co2TickRange, co2MaxTick+self.ymargin*co2TickRange)
            
            occMaxTick = max(occupancy)
            occMinTick = min(occupancy)
            occTickRange = occMaxTick-occMinTick
            twin1.set_ylim(occMinTick-self.ymargin*occTickRange, occMaxTick+self.ymargin*occTickRange)
            
            twin2.set_ylim(-self.ymargin, 1+self.ymargin)
            
            yRange = max(self.simResults["BuildingSpace"][space + ": ppmCO2"])-Settings.ppmCO2Out
            nTicksIdeal = 6
            tickSize = self.myRound(yRange/nTicksIdeal, 50)
            if tickSize != 0:
                yMajor = np.arange(Settings.ppmCO2Out, co2MaxTick+1, tickSize)
                yMinor = np.arange(Settings.ppmCO2Out, co2MaxTick+1, 25)
                nTicks = len(yMajor)
                y2Major = np.linspace(occMinTick, occMaxTick, nTicks)
                y3Major = np.linspace(0, 1, nTicks)
                ax.set_yticks(yMajor)
                ax.set_yticks(yMinor, minor=True)
                twin1.set_yticks(y2Major)
                twin2.set_yticks(y3Major)
            ax.grid(which='both')
            ax.grid(which='minor', alpha=0.2)
            ax.grid(which='major', alpha=0.5)
            fig.autofmt_xdate(rotation=30)
            plt.show()
    
    def systemPlots(self):
        for system in self.elementDict["System"]:
            if self.elementDict["System"][system].systemType == "ventilationSystem":
            
                # Figure setup
                fig, ax = plt.subplots()
                plt.suptitle(system)
                fig.set_figheight(6)
                fig.set_figwidth(10)
                #fig.subplots_adjust(right=0.75)
                twin1 = ax.twinx()
            
                # data
                dateTime = self.simResults["DateTime"]["DateTime"]
                for fan in self.elementDict["Fan"]:
                    if self.elementDict["Fan"][fan].superSystem == system:
                        fanW = self.simResults["Fan"][fan + ": W"]
                        fanEnergy = self.simResults["Fan"][fan + ": Energy"]
                        if self.elementDict["Fan"][fan].operationMode == "supply":
                            p1, = ax.plot(dateTime, fanW, "b-", label="supply fan power")
                            p2, = twin1.plot(dateTime, fanEnergy, "r-", label="supply fan energy")
                        elif self.elementDict["Fan"][fan].operationMode == "exhaust":
                            p3, = ax.plot(dateTime, fanW, "g-", label="exhaust fan power")
                            p4, = twin1.plot(dateTime, fanEnergy, "y-", label="exhaust fan energy")

                ax.set_xlabel("Time")
                ax.set_ylabel("Power consumption [W]")
                twin1.set_ylabel("Accumulated energy comsumption [J]")
            
                ax.legend(handles=[p1, p2, p3, p4], loc="upper left")
                ax.grid(which='both')
                ax.grid(which='minor', alpha=0.2)
                ax.grid(which='major', alpha=0.5)
                fig.autofmt_xdate(rotation=30)
                plt.show()
                
    def buildingPlots(self):
        time = self.simResults["DateTime"]["DateTime"]
        
        plt.figure(figsize=(14,12))
        plt.title('Building')
        plt.subplot(8,1,1)
        plt.step(time, self.buildingResults['DKKPerMWh'])
        plt.ylabel('Price [DKK/MWh]', rotation=75)
        plt.subplot(8,1,2)
        plt.step(time, self.buildingResults['gCO2PerKWh'])
        plt.ylabel('CO2 emm. factor [g/kWh]', rotation=75)
        plt.subplot(8,1,3)
        plt.step(time, self.buildingResults['powerW'])
        plt.ylabel('Power usage [W]', rotation=75)
        plt.subplot(8,1,4)
        plt.step(time, self.buildingResults['el'])
        plt.ylabel('Energy [kWh]', rotation=75)
        plt.subplot(8,1,5)
        plt.step(time, self.buildingResults['cost'])
        plt.ylabel('Cost [DKK/t_step]', rotation=75)
        plt.subplot(8,1,6)
        plt.step(time, self.buildingResults['totCost'])
        plt.ylabel('Total cost [DKK]', rotation=75)
        plt.subplot(8,1,7)
        plt.step(time, self.buildingResults['kgCO2emm'])
        plt.ylabel('CO2 emm. [kg/t_step]', rotation=75)
        plt.subplot(8,1,8)
        plt.step(time, self.buildingResults['totCO2emm'])
        plt.ylabel('Total CO2 emm. [kg]', rotation=75)
        plt.xlabel('time')
        plt.show()
               
    def MPCPlots(self):
        for idx in self.createMPCPlots: 
            startTime = self.startTime+idx*self.timeStep
            time = []
            for i in range(Settings.mpcSteps+1):
                time.append(startTime+i*self.timeStep*int(Settings.mpcTimeStep/Settings.timeStep))
                
            for systemMPC in self.elementDict['SystemMPC']:
                spaceList = self.elementDict['SystemMPC'][systemMPC].spaceList
                nSpaces = len(spaceList)
                cost = self.elementDict['SystemMPC'][systemMPC].results['Cost'][:,idx]
                CO2Imp = self.elementDict['SystemMPC'][systemMPC].results['CO2Imp'][:,idx]
                price = self.elementDict['SystemMPC'][systemMPC].results['stepPrice'][:,idx]
                pos = self.elementDict['SystemMPC'][systemMPC].results['damperPos'][:,:,idx]
                CO2 = self.elementDict['SystemMPC'][systemMPC].results['spaceCO2'][:,:,idx]
                CO2Emm = self.elementDict['SystemMPC'][systemMPC].results['totalEmm'][:,idx]

                plt.figure(figsize=(14,12))
                plt.title(self.elementDict['SystemMPC'][systemMPC].id + ' - step ' + str(idx))
                plt.subplot(6,1,1)
                for space in range(nSpaces):
                    plt.step(time,pos[space],'-', label='space'+str(space))
                plt.ylabel('Damper position')
                plt.legend()
                plt.subplot(6,1,2)
                for space in range(nSpaces):
                    plt.plot(time,CO2[space],'-*', label='space'+str(space))
                plt.ylabel('CO2 [ppm]')
                plt.legend()
                plt.subplot(6,1,3)
                plt.step(time,price,'r-')
                plt.ylabel('price [DKK/s]')
                plt.subplot(6,1,4)
                plt.plot(time,CO2Imp,'b-')
                plt.ylabel('CO2 impact [ppm*s*occ]')
                plt.subplot(6,1,5)
                plt.plot(time,cost,'r-')
                plt.ylabel('Cost [DKK]')
                plt.subplot(6,1,6)
                plt.step(time,CO2Emm,'r-')
                plt.ylabel('CO2 emission [kg]')
                plt.xlabel('time')
                plt.show()
                
    def objectiveResults(self):
        startup = 0
        if self.discardStartup:
            startup = int(self.startupDuration/self.timeStep.seconds)
            
        cost = self.buildingResults['totCost'][self.steps-1-startup]
        KPI = self.KPI
        CO2Emm = self.buildingResults['totCO2emm'][self.steps-1-startup]
        table = [['Energy cost:', str(cost) + ' DKK'],
                 ['KPI (air polution):', str(KPI) + ' ppm*occ*s'],
                 ['CO2 emission:', str(CO2Emm) + ' kg']]
        print(tabulate(table))
        if self.saveResults:
            fileName = self.outputName + 'Results.txt'
            file = os.path.abspath(os.path.join(self.projectPath, "Results", fileName))
            f = open(file, 'w')
            print(tabulate(table), file = f)
                
    def storeResults(self):
        first = True
        for key in self.simResults:
            if first:
                resultDf = self.simResults[key]
                first = False
            else:
                resultDf = resultDf.join(self.simResults[key])
                
        fileName = self.outputName + '.csv'
        fileName2 = self.outputName + '_building.csv'
        file = os.path.abspath(os.path.join(self.projectPath, "Results", fileName))
        file2 = os.path.abspath(os.path.join(self.projectPath, "Results", fileName2))
        resultDf.to_csv(file)
        self.buildingResults.to_csv(file2)
        
        if self.damperControlType == 'MPC':
            for mpc in self.elementDict['SystemMPC']:
                mpcFileName = self.outputName + self.elementDict['SystemMPC'][mpc].id
                
                for key in self.elementDict['SystemMPC'][mpc].results:
                    arr = self.elementDict['SystemMPC'][mpc].results[key]
                    if self.elementDict['SystemMPC'][mpc].results[key].ndim == 3:
                        arr = arr.reshape(arr.shape[0], -1)
                    
                    np.savetxt(self.projectPath + '\\Results\\' + mpcFileName + key + '.txt', arr, delimiter=',')    
                
    def resultVisualisation(self):
        print("Preparing result visualisation...")
        self.calculateTotals()
        self.plotSettings()
        self.clacAirKPI()
        if self.createBuildingSpacePlots:
            self.SpacePlots()
        if self.createSystemPlots:
            self.systemPlots()
        if self.createBuildingPlots:
            self.buildingPlots()
        if self.createMPCPlots != False:
            self.MPCPlots()
        if self.saveResults:
            self.storeResults()
        print("Visualisation complete")
        self.objectiveResults()
        if self.simTimer != False:
            duration = time.time() - self.simStart
            print('Total running time: ' + str(duration) + ' seconds')
    

#-----------------------------------------------------------------------------
#------------------------------- RUN SIMULATION ------------------------------
#-----------------------------------------------------------------------------
# NB! This section is only intended for testing during model development. 
# Simulations should normally be initiated from a file in the "Simulations" 
# folder.

# Chose simulation start and end time. Make sure the chosen date covers the chosen duration
"""startTime = {"year": 2020, "month": 1, "day": 3, "hour": 0, "minute": 0, "second": 0}
endTime = {"year": 2020, "month": 1, "day": 4, "hour": 0, "minute": 0, "second": 0}

# Chose configuration file for simulation. The configuration file defines the elements (components, spaces and systems) included in the simulation.
configFileName = "config_1sys_2rooms.xlsx"

# Chose wether the first part of the simulation duration should be discarded from the results and if so how much (in seconds). This may be done to reduce error from inaccurate initial conditions guesses.
discardStartupPeriod = False
StartupPeriodLength = 3600*3 #Seconds

model = Model(configFile = configFileName, startTimeInput = startTime, endTimeInput = endTime, 
              discardStartup = discardStartupPeriod, startupDuration = StartupPeriodLength,
              damperControlType="MPC", createBuildingSpacePlots = True, createSystemPlots = True)

model.simulationSetup()
model.runSimulation()
model.resultVisualisation()"""