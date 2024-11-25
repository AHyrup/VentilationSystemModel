class Settings:
    
#--------------------------------- Constants ----------------------------------
    rhoAir = 1.225 #[kg/m^3]
    rhoCO2 = 1.98 #[kg/m^3]
    MAir = 28.9647 #[g/mol]
    MCO2 = 44.01 #[g/mol]

#--------------------------- Data dependent values ----------------------------
    timeStep = 600 #Timestep in seconds

#------------------------------ User Assumptions ------------------------------
    ppmCO2Out = 400 #Outdoor concentration of CO2 in ppm
    airInfSpace = 0.05 / 3600 #s^-1
    CO2GenPerson = 15 / (3600*1000) # [m^3/s] (15 [L/h])
    ppmCO2BuildingInitial = ppmCO2Out #Initial concentration of CO2 in ppm in spaces

#-------------------------------- User Choices --------------------------------
    CO2Threshold = 700 #[ppm]
    mpcSteps = 12
    mpcTimeStep = 1200 # s (should be timeStep multiplied by a whole number)
    
    
"""
    #Supply fan constants 
    c1SupFan = 0 #assumed
    c2SupFan = 0.8321 #from parameter estimation
    c3SupFan = -0.9847 #from parameter estimation
    c4SupFan = 1.1526 #from parameter estimation
    mFlowMaxSupFan = 35500 / 3600 #[m^3/s] from system documentation
    WMaxSupFan = mFlowMaxSupFan * 984 #[W] from system documentation

    #Exhaust fan constants 
    c1ExhFan = 0 #assumed
    c2ExhFan = 0.8843 #from parameter estimation
    c3ExhFan = -0.4617 #from parameter estimation
    c4ExhFan = 0.5775 #from parameter estimation
    mFlowMaxExhFan = 35500 / 3600 #[m^3/s] from system documentation
    WMaxExhFan = mFlowMaxExhFan * 984 #[W] from system documentation"""

    