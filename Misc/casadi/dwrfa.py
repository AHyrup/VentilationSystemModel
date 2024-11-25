import gurobipy as gp
from gurobipy import GRB
import numpy as np
import math
from Misc.settings import Settings

m = gp.Model('MPC')

a = m.addVar(vtype=GRB.CONTINUOUS)

b = np.empty([2, 2], dtype=gp.Var)

b[0][0] = a

b[1][0] = m.addVar(vtype=GRB.CONTINUOUS)



