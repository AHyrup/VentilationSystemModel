import numpy as np
from gekko import GEKKO
import matplotlib.pyplot as plt
from Misc.settings import Settings

#initialize GEKKO model
m = GEKKO()

#time
nSteps = 20
timeStep = Settings.timeStep
m.time = np.linspace(0,timeStep*nSteps,nSteps+1)

# Constants
CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
airInf = Settings.airInfSpace # [m^3/s]
vol = 400 # [m^3] (test value)
nomFlowDamper = 0.22 # [m^3/s] (test value)
CO2Out = Settings.ppmCO2Out
cSupFan = [0, 0.8321, -0.9847, 1.1526]
cExhFan = [0, 0.8843, -0.4617, 0.5775]
nomFlowSupFan = 12.08 # [m^3/s]
nomFlowExhFan = 11.74 # [m^3/s]
nomWSupFan = 9703 # W
nomWExhFan = 8462 # W

#Parameters
elPrice = m.Param([500] * (nSteps+1))
occ = m.Param([10] * (nSteps+1))

#Input
pos = m.MV(value=0, lb=0, ub=1)
pos.STATUS = 1

#Controlled variables
CO2 = m.CV(400)
CO2Imp = m.CV(0)
price = m.CV(0)
cost = m.CV(0)

#State variables
flowSupFan = m.SV(0, lb=0, ub=1)
flowExhFan = m.SV(0, lb=0, ub=1)

# Aux terms
plSupFan = m.Intermediate(flowSupFan) #cSupFan[0] + cSupFan[1]*flowSupFan + cSupFan[2]*flowSupFan**2 + cSupFan[3]*flowSupFan**3
wSupFan = m.Intermediate(plSupFan * nomWSupFan)
plExhFan = m.Intermediate(flowExhFan) 
wExhFan = m.Intermediate(plExhFan * nomWExhFan)

#Equations 
m.Equation(CO2.dt() == (occ*CO2GenPerson*1000000-(nomFlowDamper*pos+airInf)*(CO2-CO2Out))/vol)
m.Equation(CO2Imp.dt() == CO2)
m.Equation(price == (wSupFan+wExhFan) * elPrice /(1000*3600/Settings.timeStep))
m.Equation(cost.dt() == price)
m.Equation(flowSupFan == nomFlowDamper*pos/nomFlowSupFan)
m.Equation(flowExhFan == nomFlowDamper*pos/nomFlowExhFan)

#Objective
m.Obj(CO2Imp)
m.Obj(cost*10)

m.options.IMODE = 6 #simultaneous control
m.solve()

plt.figure(figsize=(14,12))
plt.subplot(5,1,1)
plt.step(m.time,pos.value,'g-')
plt.ylabel('Damper position')
plt.subplot(5,1,2)
plt.plot(m.time,CO2.value,'b-*')
plt.ylabel('CO2 [ppm]')
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





