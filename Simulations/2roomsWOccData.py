#-----------------------------------------------------------------------------
#--------------------------------- USER INPUT --------------------------------
#-----------------------------------------------------------------------------

# Chose simulation start and end time (CET with daylight savings). Make sure the chosen date covers the chosen duration
startTime = {"year": 2018, "month": 3, "day": 23, "hour": 0, "minute": 0, "second": 0}
endTime = {"year": 2018, "month": 3, "day": 29, "hour": 0, "minute": 0, "second": 0}

#Chose configuration file for simulation. The configuration file defines the elements (components, spaces and systems) included in the simulation.
configFileName = "config_1sys_2rooms.xlsx"

#Chose wether the first part of the simulation duration should be discarded from the results and if so how much (in seconds). This may be done to reduce error from inaccurate initial conditions guesses.
discardStartupPeriod = False
StartupPeriodLength = 86400 #Seconds

# Ensure that the settings in Misc/settings.py are correct


#-----------------------------------------------------------------------------
#------------------------------- RUN SIMULATION ------------------------------
#-----------------------------------------------------------------------------

from model import Model
model = Model(configFile = configFileName, startTimeInput = startTime, endTimeInput = endTime,
              discardStartup = discardStartupPeriod, startupDuration = StartupPeriodLength,
              damperControlType="ruleSet", occData = "dataConnect1", createBuildingSpacePlots = True, 
              createSystemPlots = True, createBuildingPlots = True)

model.simulationSetup()
model.runSimulation()
model.resultVisualisation()

