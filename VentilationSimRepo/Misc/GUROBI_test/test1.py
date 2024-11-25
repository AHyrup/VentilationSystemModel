import gurobipy as gp
from gurobipy import GRB
import numpy as np
import math
from Misc.settings import Settings


w1 = 0.02/(1000*3600)
w2 = 0

CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
airInf = Settings.airInfSpace # [m^3/s]

spaceList = []
spaceVol = []
nomFlowDamper = []
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

x = np.empty([nSpaces, mpcSteps+1], dtype=gp.Var) # CO2 diff from outdoor
u = np.empty([nSpaces, mpcSteps], dtype=gp.Var) # damper pos
price = np.ones((1, mpcSteps)) * 500
vol = np.ones((nSpaces, 1)) * 200
vol[1,0] = 100
occ = np.ones((nSpaces, mpcSteps)) * 10 * CO2GenPerson * 1000000 / vol

nomFlow = np.ones((nSpaces, 1)) * 0.1
flow = np.empty([nSpaces, mpcSteps], dtype=gp.Var)
ven = np.empty([nSpaces, mpcSteps], dtype=gp.Var)
venInv = np.empty([nSpaces, mpcSteps], dtype=gp.Var)

expInner = np.empty([nSpaces, mpcSteps], dtype=gp.Var)
expTerm = np.empty([nSpaces, mpcSteps], dtype=gp.Var)

sysFlow = np.empty([1, mpcSteps], dtype=gp.Var)
wSup = np.empty([1, mpcSteps], dtype=gp.Var)
wExh = np.empty([1, mpcSteps], dtype=gp.Var)

for k in range(mpcSteps+1):
    for n in range(nSpaces):
        x[n][k] = m.addVar(vtype=GRB.CONTINUOUS)

for k in range(mpcSteps):
    sysFlow[0,k] = m.addVar(vtype=GRB.CONTINUOUS)
    wSup[0,k] = m.addVar(vtype=GRB.CONTINUOUS)
    wExh[0,k] = m.addVar(vtype=GRB.CONTINUOUS)
    
    for n in range(nSpaces):
        u[n][k] = m.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1)
        
        ven[n][k] = m.addVar(vtype=GRB.CONTINUOUS)
        venInv[n][k] = m.addVar(vtype=GRB.CONTINUOUS)
        expTerm[n][k] = m.addVar(vtype=GRB.CONTINUOUS)
        expInner[n][k] = m.addVar(vtype=GRB.CONTINUOUS)
  
for k in range(mpcSteps):
    #m.addGenConstrPoly(x, y, [2, 1.5, 0, 1])
    #m.addConstr(sysFlow[k] == sum(flow[:][k]))
    m.addConstr(sysFlow[k] == flow[:,k].sum())
    
    for n in range(nSpaces):
        m.addConstr(flow[n][k] == u[n][k]*nomFlow[n])
        m.addConstr(ven[n][k] == u[n][k]*nomFlow[n]/vol[n])
        m.addGenConstrPow(ven[n][k], venInv[n][k], -1)
        m.addConstr(expInner[n][k] == -ven[n][k]*timeStep)
        m.addGenConstrExp(expInner[n][k], expTerm[n][k])
        
        m.addConstr(x[n][k+1] == occ[n,k]*venInv[n][k] + x[n][k]-occ[n,k]*venInv[n][k]*expTerm[n][k])
    
               
        
         





