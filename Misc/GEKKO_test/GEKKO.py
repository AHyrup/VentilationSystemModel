import numpy as np
from gekko import GEKKO
import matplotlib.pyplot as plt
from Misc.settings import Settings

#Settings
displaySolver = True
plotResults = True

nSpaces = 2
#occPredict = 

def setupMPC():
    #initialize GEKKO model
    m = GEKKO()
    
    #time
    nSteps = 50
    timeStep = Settings.timeStep
    m.time = np.linspace(0,timeStep*nSteps,nSteps+1)
    
    # Constants
    CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
    airInf = Settings.airInfSpace # [m^3/s]
    vol = [400, 1000] # [m^3] (test value)
    nomFlowDamper = [0.22] * nSpaces # [m^3/s] (test value)
    CO2Out = Settings.ppmCO2Out
    cSupFan = [0, 0.8321, -0.9847, 1.1526]
    cExhFan = [0, 0.8843, -0.4617, 0.5775]
    nomFlowSupFan = 12.08 # [m^3/s]
    nomFlowExhFan = 11.74 # [m^3/s]
    nomWSupFan = 9703 # W
    nomWExhFan = 8462 # W
    
    #Parameters
    elPrice = m.Param([500] * (nSteps+1))
    occ = [None] * nSpaces
    for space in range(nSpaces):
        occ[space] = m.Param([10] * (nSteps+1))
    
    #Input
    global pos
    pos = [None] * nSpaces
    for space in range(nSpaces):
        pos[space] = m.MV(lb=0, ub=1)
        pos[space].STATUS = 1
    
    #Controlled variables
    global CO2
    CO2 = [None] * nSpaces
    for space in range(nSpaces):
        CO2[space] = m.CV(1000)
    global CO2Imp
    CO2Imp = m.CV(0)
    global price
    price = m.CV(0)
    global cost
    cost = m.CV(0)
    
    #State variables
    flowDamper = [None] * nSpaces
    for space in range(nSpaces):
        flowDamper[space] = m.SV(0)
    flowSupFan = m.SV(0, lb=0, ub=1)
    flowExhFan = m.SV(0, lb=0, ub=1)
    
    # Aux terms
    plSupFan = m.Intermediate(flowSupFan) #cSupFan[0] + cSupFan[1]*flowSupFan + cSupFan[2]*flowSupFan**2 + cSupFan[3]*flowSupFan**3
    wSupFan = m.Intermediate(plSupFan * nomWSupFan)
    plExhFan = m.Intermediate(flowExhFan) 
    wExhFan = m.Intermediate(plExhFan * nomWExhFan)
    CO2ImpSpace = [None] * nSpaces
    for space in range(nSpaces):
        CO2ImpSpace[space] = m.Intermediate(CO2[space] * occ[space])
    
    #Equations
    for space in range(nSpaces):
        m.Equation(flowDamper[space] == pos[space]*nomFlowDamper[space])
        m.Equation(CO2[space].dt() == (occ[space]*CO2GenPerson*1000000-(nomFlowDamper[space]*pos[space]+airInf)*(CO2[space]-CO2Out))/vol[space])
    m.Equation(CO2Imp.dt() == sum(CO2ImpSpace))
    m.Equation(price == (wSupFan+wExhFan) * elPrice /(1000*3600/Settings.timeStep))
    m.Equation(cost.dt() == price)
    
    m.Equation(flowSupFan == sum(flowDamper)/nomFlowSupFan)
    m.Equation(flowExhFan == sum(flowDamper)/nomFlowExhFan)
    
    #Objective
    m.Obj(CO2Imp)
    m.Obj(cost*100)
    
    m.options.IMODE = 6 #simultaneous control
    return m

m = setupMPC()
m.solve(disp=displaySolver)

if plotResults:
    plt.figure(figsize=(14,12))
    plt.subplot(5,1,1)
    for space in range(nSpaces):
        plt.step(m.time,pos[space].value,'-', label='space'+str(space))
    plt.ylabel('Damper position')
    plt.legend()
    plt.subplot(5,1,2)
    for space in range(nSpaces):
        plt.plot(m.time,CO2[space].value,'-*', label='space'+str(space))
    plt.ylabel('CO2 [ppm]')
    plt.legend()
    plt.subplot(5,1,3)
    plt.step(m.time,price.value,'r-')
    plt.ylabel('Step price [DKK]')
    plt.subplot(5,1,4)
    plt.plot(m.time,CO2Imp.value,'b-')
    plt.ylabel('CO2 impact')
    plt.subplot(5,1,5)
    plt.plot(m.time,cost.value,'r-')
    plt.ylabel('Cost [DKK]')
    plt.xlabel('time')
    plt.show()
