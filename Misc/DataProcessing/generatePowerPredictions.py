import pandas as pd
import os
import math
from datetime import datetime
import datetime as dt
from dateutil.tz import tzutc
from Misc.settings import Settings
import numpy as np

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

fileName = 'ElspotpricesDK1.csv'
path = getProjectPath()
file = os.path.abspath(os.path.join(path, 'Data', 'ElspotPrices', fileName))
df = pd.read_csv(file, sep=';')

fileName2 = 'CO2Emis.csv'
file2 = os.path.abspath(os.path.join(path, 'Data', 'ElspotPrices', fileName2))
df2 = pd.read_csv(file2, sep=';')
#! NB missing value at 26-07-2022 09:05

formatedTimes = []
formatedPrices = []
dateFormat = '%Y-%m-%d %H:%M'
for idx in range(len(df)):
    formated = datetime.strptime(df['HourDK'][idx], dateFormat)
    formated = formated.replace(tzinfo=tzutc())
    formatedTimes.append(formated)
    price = float(df['SpotPriceDKK'][idx].replace(',', '.'))
    formatedPrices.append(price)
df.insert(5, 'Datetime', formatedTimes) 
df = df.drop(['SpotPriceDKK'], axis=1)
df.insert(3, 'SpotPriceDKK', formatedPrices) 
    
formatedTimes2 = []
formatedEmm = []
dateFormat2 = '%d-%m-%Y %H:%M'
for idx in range(len(df2)):
    formated = datetime.strptime(df2['Minutes5DK'][idx], dateFormat2)
    formated = formated.replace(tzinfo=tzutc())
    formatedTimes2.append(formated)
    emm = float(df2['CO2Emission'][idx])
    formatedEmm.append(emm)
df2.insert(4, 'Datetime', formatedTimes2)
df2 = df2.drop(['CO2Emission'], axis=1)
df2.insert(3, 'CO2Emission', formatedEmm) 

timeStep = Settings.timeStep
stepsPerHour = 3600/timeStep

timeStamps = []
prices = []
for idx in range(len(df)):
    for step in range(int(stepsPerHour)):
        timeStamp = df['Datetime'][idx] + dt.timedelta(seconds=timeStep)*step
        timeStamps.append(timeStamp)
        price = df['SpotPriceDKK'][idx] 
        prices.append(price)

#%%
#startTime2 = df2['Datetime'][0]
#endTime2 = df2['Datetime'].iloc[-1]

dstWinterSwap = [dt.datetime(2019,10,27,2,55,tzinfo=tzutc()),
                 dt.datetime(2020,10,25,2,55,tzinfo=tzutc()),
                 dt.datetime(2021,10,31,2,55,tzinfo=tzutc()),
                 dt.datetime(2022,10,30,2,55,tzinfo=tzutc()),
                 dt.datetime(2023,10,29,2,55,tzinfo=tzutc()),
                 None]
missingTime = dt.datetime(2022,7,26,9,5,tzinfo=tzutc()) 

timeStamps2 = []
CO2 = []
i = 0
for idx in range(len(df2)):
    time = df2['Datetime'][idx]
    timeStamps2.append(time)
    CO2.append(df2['CO2Emission'][idx])
    if time == dstWinterSwap[i]:
        addTime = timeStamps2[-12:]
        addCO2 = CO2[-12:]
        for j in range(len(addTime)):
            timeStamps2.append(addTime[j])
            CO2.append(addCO2[j])
        i = i + 1
    if time == missingTime-dt.timedelta(seconds=timeStep):
        timeStamps2.append(missingTime)
        CO2.append(CO2[-1:])
    
#%%
timeStamps2Short = []
CO2Short = []
for idx in range(math.ceil(len(timeStamps2)/2)):
    timeStamps2Short.append(timeStamps2[idx*2])
    CO2Short.append(CO2[idx*2])
    
for idx in range(len(CO2Short)):
    if type(CO2Short[idx]) == list:
        CO2Short[idx] = float(CO2Short[idx][0])
    CO2Short[idx] = CO2Short[idx]/1000000

dfOut = pd.DataFrame({'DateTime': timeStamps, 'DKKPerMWh': prices, 'gCO2PerKWh': CO2Short})
   
here = os.getcwd()
path = here + '\\PowerPredictions\\' + 'power_' + str(Settings.timeStep) + 's.csv'
dfOut.to_csv(path)