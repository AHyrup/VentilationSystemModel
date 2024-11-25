#-----------------------------------------------------------------------------
#--------------------------------- USER INPUT --------------------------------
#-----------------------------------------------------------------------------

# Chose simulation start and end time (CET with daylight savings). Make sure the chosen date covers the chosen duration
startTime = {"year": 2024, "month": 3, "day": 5, "hour": 0, "minute": 0, "second": 0}
endTime = {"year": 2024, "month": 3, "day": 12, "hour": 23, "minute": 50, "second": 0}

# Chose configuration file for simulation. The configuration file defines the elements (components, spaces and systems) included in the simulation.
configFileName = "config_1sys_2rooms.xlsx"

# Chose wether the first part of the simulation duration should be discarded from the results and if so how much (in seconds). This may be done to reduce error from inaccurate initial conditions guesses.
discardStartupPeriod = True
StartupPeriodLength = 3600*24 #Seconds

# To save the results in file(s) set save = True. Choose output file name.
save = False
name = '1sys2rooms1dayRule'

# Ensure that the settings in Misc/settings.py are correct


#-----------------------------------------------------------------------------
#------------------------------- RUN SIMULATION ------------------------------
#-----------------------------------------------------------------------------

from model import Model
model = Model(configFile = configFileName, startTimeInput = startTime, endTimeInput = endTime, 
              discardStartup = discardStartupPeriod, startupDuration = StartupPeriodLength,
              damperControlType = "PD", createBuildingSpacePlots = True, createSystemPlots = True,
              createBuildingPlots = True, simTimer=144, saveResults = save, outputName = name)

model.simulationSetup()
model.runSimulation()
model.resultVisualisation()