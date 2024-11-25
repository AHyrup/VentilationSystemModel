#-----------------------------------------------------------------------------
#--------------------------------- USER INPUT --------------------------------
#-----------------------------------------------------------------------------

# Chose simulation start and end time (CET with daylight savings). Make sure the chosen date covers the chosen duration
startTime = {"year": 2020, "month": 1, "day": 3, "hour": 8, "minute": 0, "second": 0}
endTime = {"year": 2020, "month": 1, "day": 3, "hour": 8, "minute": 0, "second": 0}

# Chose configuration file for simulation. The configuration file defines the elements (components, spaces and systems) included in the simulation.
configFileName = "config_OU44.xlsx"

# Chose wether the first part of the simulation duration should be discarded from the results and if so how much (in seconds). This may be done to reduce error from inaccurate initial conditions guesses.
discardStartupPeriod = False
StartupPeriodLength = 3600*3 #Seconds

# To save the results in file(s) set save = True. Choose output file name.
save = False
name = 'OU44MPC'

# Set weights for mpc objectives. w1 is the wight for indoor CO2 impact on occupancy and w2 is the weight for (outdoor) CO2 emmision from electricity usage.
w1 = 0.02/(1000*3600) #[DKK/(ppm*s*occ)] (only ppm above threshold)
w2 = 0 #[DKK/kg_CO2]

# Ensure that the settings in Misc/settings.py are correct


#-----------------------------------------------------------------------------
#------------------------------- RUN SIMULATION ------------------------------
#-----------------------------------------------------------------------------

from model import Model
model = Model(configFile = configFileName, startTimeInput = startTime, endTimeInput = endTime, 
              discardStartup = discardStartupPeriod, startupDuration = StartupPeriodLength,
              damperControlType = "MPC", createBuildingSpacePlots = False, createSystemPlots = True,
              createBuildingPlots = True, createMPCPlots = [0], #[0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132], 
              saveResults = save, outputName = name, simTimer = 6, mpcW1 = w1, mpcW2 = w2)

model.simulationSetup()
model.runSimulation()
model.resultVisualisation()