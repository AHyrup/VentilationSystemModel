#%%
"""
Space Types:
    Toilet area
    Teaching
    Study zone
    Copy room
    Hallway
    Atrium (hallway center)
    Meeting place
    PHD. Work space
    Tea kitchen
    Storage room
    Auditorium
    
Period Types:
    Summer break
    Holiday period
    Weekend
    Summer school
    Exam period
    Study day
"""

import datetime as dt
from dateutil.tz import tzutc
import math
import pandas as pd
import os
import openpyxl
import random
import numpy as np
from Misc.settings import Settings

dstSwitchDate = [[2019, 3, 31, 2, True], #year, month, day, hour, DST on? 
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

fixedDateHolidays = [[1, 1], #Month, day
                     [12, 23],
                     [12, 24],
                     [12, 25],
                     [12, 26],
                     [12, 27],
                     [12, 28],
                     [12, 29],
                     [12, 30],
                     [12, 31]] 

variableHolidays2019 = [[4, 14], #Month, day
                        [4, 18],
                        [4, 19],
                        [4, 21],
                        [4, 22],
                        [5, 17],
                        [5, 30],
                        [6, 9],
                        [6, 10]]
                        
variableHolidays2020 = [[4, 5], #Month, day
                        [4, 9],
                        [4, 10],
                        [4, 12],
                        [4, 13],
                        [5, 8],
                        [5, 21],
                        [5, 31],
                        [6, 1]]
                        
variableHolidays2021 = [[3, 28], #Month, day
                        [4, 1],
                        [4, 2],
                        [4, 4],
                        [4, 5],
                        [4, 30],
                        [5, 13],
                        [5, 23],
                        [5, 24]]                   

variableHolidays2022 = [[4, 10], #Month, day
                        [4, 14],
                        [4, 15],
                        [4, 17],
                        [4, 18],
                        [5, 13],
                        [5, 26],
                        [6, 5],
                        [6, 6]]

variableHolidays2023 = [[4, 2], #Month, day
                        [4, 6],
                        [4, 7],
                        [4, 9],
                        [4, 10],
                        [5, 5],
                        [5, 18],
                        [5, 28],
                        [5, 29]]
                
variableHolidays2024 = [[3, 24], #Month, day
                        [3, 28],
                        [3, 29],
                        [3, 31],
                        [4, 1],
                        [5, 9],
                        [5, 19],
                        [5, 20]]

dailySchedule = [[0,        0], #startpoint (seconds), occupancy multiplyer
                 [6*3600,   0.1],
                 [7*3600,   0.3],
                 [8*3600,   1],
                 [14*3600,  0.7],
                 [16*3600,  0.3],
                 [18*3600,  0.1],
                 [20*3600,  0],
                 ]

areaPerOcc = [['Toilet area', 15], #Areatype, Area (m^2) per occupant at base peak (before randomness)
              ['Teaching', 5],
              ['Study zone', 10],
              ['Copy room', 30],
              ['Hallway', 20],
              ['Atrium (hallway center)', 15],
              ['Meeting place', 15],
              ['PHD. Work space', 10],
              ['Tea kitchen', 20],
              ['Storage room', 50],
              ['Auditorium', 4],
              ['Office area', 12]

def holiday(timestamp):
    holiday = False
    
    if timestamp.isocalendar().week == 42:
        holiday = True   

    for idx in range(len(fixedDateHolidays)):
        if timestamp.month == fixedDateHolidays[idx][0] and timestamp.day == fixedDateHolidays[idx][1]:
            holiday = True   
    
    variableHolidays = None
    if timestamp.year == 2019:
        variableHolidays = variableHolidays2019
    elif timestamp.year == 2020:
        variableHolidays = variableHolidays2020
    elif timestamp.year == 2021:
        variableHolidays = variableHolidays2021
    elif timestamp.year == 2022:
        variableHolidays = variableHolidays2022
    elif timestamp.year == 2023:
        variableHolidays = variableHolidays2023
    elif timestamp.year == 2024:
        variableHolidays = variableHolidays2024
    for idx in range(len(variableHolidays)):
        if timestamp.month == variableHolidays[idx][0] and timestamp.day == variableHolidays[idx][1]:
            holiday = True          
             
    return holiday

def findDatetimePeriodType(timestamp):
    if timestamp.month == 7:
        periodType = 'Summer break'
        weight = 0
    elif holiday(timestamp):
        periodType = 'Holiday period'
        weight = 0
    elif timestamp.weekday() > 4:
        periodType = 'Weekend'
        weight = 0.1
    elif timestamp.month == 8:
        periodType = 'Summer school'
        weight = 0.5
    elif timestamp.month == 1 or timestamp.month == 6:
        periodType = 'Exam period'
        weight = 0.3
    else:
        periodType = 'Study day'
        weight = 1
    
    return periodType, weight

def dstCheck(timeStamp): # account for daylight savings  
    dst = False
    index = -1
    for idx in range(len(dstSwitchDate)):
        if timeStamp > dt.datetime(dstSwitchDate[idx][0], dstSwitchDate[idx][1], dstSwitchDate[idx][2], dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc()):
            dst = dstSwitchDate[idx][4]
            index = idx
    return dst, index

def getProjectPath(): #The project should be contained in a folder named VentilationSim
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
    return projectPath

def propRound(occ):
    decimal = occ % 1 
    if decimal == 0:
        occWhole = occ       
    else:
        rand = random.uniform(0, 1)
        if rand <= decimal:
            occWhole = math.ceil(occ)
        else:
            occWhole = math.floor(occ)
    return occWhole

def normalDist(occ):
    if occ == 0:
        occDist = 0
    else:
        occDist = np.random.normal(loc=occ, scale=occ/6)
        occDist = max(0, occDist)
    return occDist

#%% Create Timestamps and period types

# datetime(year, month, day, hour, minute, second, microsecond)
timeStep = dt.timedelta(seconds=Settings.timeStep)
startTime = dt.datetime(2019, 1, 1, 0, 0, 0, tzinfo=tzutc())
endTime = dt.datetime(2024, 9, 17, 23, 23, 30, tzinfo=tzutc())

startNoDst = startTime
endNoDst = endTime
startDst, startIdx = dstCheck(startTime)
endDst, endIdx = dstCheck(endTime)
if startDst:
    startNoDst = startTime-dt.timedelta(hours=1)
if endDst:
    endNoDst = endTime-dt.timedelta(hours=1)

duration = endNoDst - startNoDst
steps = math.floor(duration/timeStep) + 1
timeSteps = []

idx = startIdx + 1 
dst = startDst # True or false
nextDstChange = dt.datetime(dstSwitchDate[idx][0], dstSwitchDate[idx][1], dstSwitchDate[idx][2], dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc())
for step in range(steps):
    timestamp = startNoDst+step*timeStep
    if timestamp >= nextDstChange:
        dst = dstSwitchDate[idx][4]
        idx = idx + 1
        nextDstChange = dt.datetime(dstSwitchDate[idx][0], dstSwitchDate[idx][1], dstSwitchDate[idx][2], dstSwitchDate[idx][3], 0, 0, tzinfo=tzutc())
    if dst:
        timeSteps.append(timestamp+dt.timedelta(hours=1))
    else:
        timeSteps.append(timestamp)
    
periodType = []
periodWeight = []
for timestamp in timeSteps:
    pType, pWeight = findDatetimePeriodType(timestamp)
    periodType.append(pType)
    periodWeight.append(pWeight)

#%% Create occupancy for each room

fileName = 'config_OU44.xlsx'
path = getProjectPath()
file = os.path.abspath(os.path.join(path, 'Data', 'Config', fileName))

openpyxl.reader.excel.warnings.simplefilter(action='ignore')
dfBuildingSpace = pd.read_excel(file, sheet_name="BuildingSpace")
dfBuildingSpace = dfBuildingSpace.dropna()

spaceName = []
baseOcc = []
for spaceIdx in range(len(dfBuildingSpace)):
    for spaceType in range(len(areaPerOcc)):
        if dfBuildingSpace.iloc[spaceIdx]['SpaceType'] == areaPerOcc[spaceType][0]:
            areaOcc = areaPerOcc[spaceType][1]
            area = dfBuildingSpace.iloc[spaceIdx]['Area']
    spaceName.append(dfBuildingSpace.iloc[spaceIdx]['id'])
    baseOcc.append(area/areaOcc)
    
dayTimeMult = []
for timestamp in timeSteps:
    midnight = timestamp.replace(hour=0, minute=0, second=0)
    timeOfDay = (timestamp-midnight).seconds
    for option in range(len(dailySchedule)):
        if timeOfDay >= dailySchedule[option][0]:
            mult = dailySchedule[option][1]
    dayTimeMult.append(mult)

spaceOccDict = {}
roundedDict = {}
normalDivDict = {}
for space in range(len(spaceName)):
    spaceOcc = np.zeros(len(dayTimeMult))
    rounded = np.zeros(len(dayTimeMult))
    normalDiv = np.zeros(len(dayTimeMult))
    for idx in range(len(dayTimeMult)):
        spaceOcc[idx] = baseOcc[space] * periodWeight[idx] * dayTimeMult[idx]
        rounded[idx] = propRound(spaceOcc[idx])
        normalDiv[idx] = propRound(normalDist(spaceOcc[idx]))
    spaceOccDict[spaceName[space]] = spaceOcc
    roundedDict[spaceName[space]] = rounded
    normalDivDict[spaceName[space]] = normalDiv
    
occDf = pd.DataFrame({'DateTime': timeSteps, 'periodType': periodType, 'periodWeight': periodWeight, 'dayTimeMult': dayTimeMult})
roundedDF = occDf.copy()
normalDivDf = occDf.copy()

idx = 0
for key in spaceOccDict:   
    occDf.insert(idx+4, spaceName[idx], spaceOccDict[key])
    roundedDF.insert(idx+4, spaceName[idx], roundedDict[key])
    normalDivDf.insert(idx+4, spaceName[idx], normalDivDict[key])
    idx = idx + 1

DataType = ['Occupancy', 'RoundedOcc', 'NormalDivOcc']
csvName = []
for row in DataType:
    csvName.append(fileName[:-5] + '_' + str(Settings.timeStep) + 's_' + row + '.csv')
    
path = []    
here = os.getcwd()
for idx in range(len(DataType)):
    path.append(here + '\\OccPredictions\\' + csvName[idx])
    
occDf.to_csv(path[0])
roundedDF.to_csv(path[1])
normalDivDf.to_csv(path[2])