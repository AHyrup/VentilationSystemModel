import gurobipy as gp
from gurobipy import GRB
import numpy as np
from Misc.settings import Settings


w1 = 0.11/(1000*3600)
w2 = 0

CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
airInf = Settings.airInfSpace # [m^3/s]
c = Settings.CO2Threshold - Settings.ppmCO2Out

#spaceList = []
#spaceVol = []
#nomFlowDamper = []
ConstantsSupFan = [0, 0.83, -0.98, 1.15]
ConstantsExhFan = [0, 0.88, -0.46, 0.57]
nomFlowSupFan = 35500 / 3600
nomFlowExhFan = 35500 / 3600
nomWSupFan = 984
nomWExhFan = 984
mpcSteps = Settings.mpcSteps
timeStep = Settings.timeStep        

m = gp.Model('MPC')

mpcSteps = 10
nSpaces = 2

x = m.addVars(nSpaces, mpcSteps+1, vtype=GRB.CONTINUOUS) # CO2 diff from outdoor
u = m.addVars(nSpaces, mpcSteps, vtype=GRB.CONTINUOUS, lb=0, ub=1) # damper pos

price = np.ones((1, mpcSteps)) * 500
emmFactor = np.ones((1, mpcSteps)) * 100
vol = np.ones((nSpaces, 1)) * 200
occ = np.ones((nSpaces, mpcSteps)) * 10 * CO2GenPerson * 1000000 / vol
co2Innit = np.ones((nSpaces, 1)) * 100

nomFlow = np.ones((nSpaces, 1)) * 0.1
flow = m.addVars(nSpaces, mpcSteps, vtype=GRB.CONTINUOUS)
ven = m.addVars(nSpaces, mpcSteps, vtype=GRB.CONTINUOUS)

sysFlow = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
fFlow = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
fPlSup = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
fPlExh = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
wSup = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
wExh = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
w = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
sCost = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
cost = m.addVar(vtype=GRB.CONTINUOUS)

rKPI = m.addVars(nSpaces, mpcSteps, vtype=GRB.CONTINUOUS)
#rtKPI = m.addVars(nSpaces, mpcSteps, vtype=GRB.CONTINUOUS)
sKPI = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
KPI = m.addVar(vtype=GRB.CONTINUOUS)

sEmm = m.addVars(mpcSteps, vtype=GRB.CONTINUOUS)
emm = m.addVar(vtype=GRB.CONTINUOUS)

m.addConstr(gp.quicksum(sCost[k] for k in range(mpcSteps)) == cost)
m.addConstr(gp.quicksum(sKPI[k] for k in range(mpcSteps)) == KPI)
m.addConstr(gp.quicksum(sEmm[k] for k in range(mpcSteps)) == emm)
  
for k in range(mpcSteps):
    m.addConstr(gp.quicksum(flow[i,k] for i in range(nSpaces)) == sysFlow[k])
    m.addConstr(fFlow[k] == sysFlow[k]/nomFlowSupFan)
    m.addGenConstrPoly(fFlow[k], fPlSup[k], [ConstantsSupFan[3], ConstantsSupFan[2], ConstantsSupFan[1], ConstantsSupFan[0]])
    m.addGenConstrPoly(fFlow[k], fPlExh[k], [ConstantsExhFan[3], ConstantsExhFan[2], ConstantsExhFan[1], ConstantsExhFan[0]])
    m.addConstr(wSup[k] == fPlSup[k]*nomWSupFan)
    m.addConstr(wExh[k] == fPlExh[k]*nomWExhFan)
    m.addConstr(w[k] == wSup[k] + wExh[k])
    m.addConstr(sCost[k] == w[k] * timeStep / (1000000*3600) * price[0,k])
    m.addConstr(gp.quicksum(rKPI[i,k] for i in range(nSpaces)) == sKPI[k])
    m.addConstr(sEmm[k] == w[k] * timeStep / (1000000*3600) * emmFactor[0,k])
    
    for n in range(nSpaces):
        m.addConstr(flow[n,k] == u[n,k]*nomFlow[n])
        m.addConstr(ven[n,k] == flow[n,k]/vol[n]+airInf)
        m.addConstr(x[n,k+1] == x[n,k]+timeStep*(occ[n,k]-ven[n,k]*x[n,k+1]))
        m.addConstr(rKPI[n,k] == x[n,k+1]*occ[n,k]*timeStep)
        #m.addGenConstrMax(rtKPI[n,k], [rKPI[n,k]], c)
        
for n in range(nSpaces):
    m.addConstr(x[n,0] == co2Innit[n])
    
obj = cost + w1*KPI + w2*emm

m.setObjective(obj, GRB.MINIMIZE)

m.optimize()

for v in m.getVars():
    print(f"{v.VarName} = {v.X}")