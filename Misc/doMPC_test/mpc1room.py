from Misc.settings import Settings
import numpy as np
import do_mpc

import matplotlib.pyplot as plt

model_type = 'continuous' # either 'discrete' or 'continuous'
model = do_mpc.model.Model(model_type)

# States struct (optimization variables):
CO2 = model.set_variable(var_type='_x', var_name='CO2', shape=(1,1))
cost = model.set_variable(var_type='_x', var_name='cost', shape=(1,1))

# Input struct (optimization variables):
pos = model.set_variable(var_type='_u', var_name='pos')

# Settings
timeStep = Settings.timeStep
steps = 50
CO2Threshold = Settings.CO2Threshold

# Certain parameters
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

# Test parameters
occ = 10
price = 400

# Weights for objective function
w1 = 1 # CO2
w2 = 50 # Cost
w3 = w1 # additional penalty for CO2 above threshold

# Aux terms
flowSupFan = nomFlowDamper*pos/nomFlowSupFan
plSupFan = flowSupFan #cSupFan[0] + cSupFan[1]*flowSupFan + cSupFan[2]*flowSupFan**2 + cSupFan[3]*flowSupFan**3
wSupFan = plSupFan * nomWSupFan
flowExhFan = nomFlowDamper*pos/nomFlowExhFan
plExhFan = flowExhFan 
wExhFan = plExhFan * nomWExhFan

# variables for visualisation
stepCost = model.set_expression(expr_name='stepCost', expr=pos*price*timeStep/3600)
power = model.set_expression(expr_name='power', expr=wSupFan+wExhFan)

# Differential equations
model.set_rhs('CO2', (occ*CO2GenPerson*1000000-(nomFlowDamper*pos+airInf)*(CO2-CO2Out))/vol)
model.set_rhs("cost", (wSupFan+wExhFan) * price /(3600*1000))

# Build the model
model.setup()

mpc = do_mpc.controller.MPC(model)

setup_mpc = {
    'n_horizon': 20,
    'n_robust': 0,
    'open_loop': 0,
    't_step': timeStep,
    'state_discretization': 'collocation',
    'collocation_type': 'radau',
    'collocation_deg': 2,
    'collocation_ni': 2,
    'store_full_solution': True,
    # Use MA27 linear solver in ipopt for faster calculations:
    # 'nlpsol_opts': {'ipopt.linear_solver': 'MA27'}
}

mpc.set_param(**setup_mpc)

mpc.scaling['_u', 'pos'] = 100

_x = model.x
terminalCost = w2*(_x['cost']) # terminal cost
stageCost = w1*(_x['CO2'])  # stage cost

mpc.set_objective(mterm=terminalCost, lterm=stageCost)

mpc.set_nl_cons('CO2', _x['CO2'], ub=CO2Threshold, soft_constraint=True, penalty_term_cons=w3)

# lower bounds of the inputs
mpc.bounds['lower', '_u', 'pos'] = 0

# upper bounds of the inputs
mpc.bounds['upper', '_u', 'pos'] = 1

mpc.setup()

estimator = do_mpc.estimator.StateFeedback(model)

simulator = do_mpc.simulator.Simulator(model)

params_simulator = {
    'integration_tool': 'cvodes',
    'abstol': 1e-10,
    'reltol': 1e-10,
    't_step': timeStep
}

simulator.set_param(**params_simulator)

simulator.setup()

# Set the initial state of mpc, simulator and estimator:
CO2_0 = 400 # This is the controlled variable [mol/l]
cost_0 = 0
x0 = np.array([CO2_0, cost_0]).reshape(-1,1)

mpc.x0 = x0
simulator.x0 = x0
estimator.x0 = x0

mpc.set_initial_guess()

for k in range(steps):
    u0 = mpc.make_step(x0)
    y_next = simulator.make_step(u0)
    x0 = estimator.make_step(y_next)

# Get penalties
def log_penalties():
    xLog = mpc.data['_x']
    auxLog = mpc.data['_aux']
    penaltyCO2 = []
    penaltyPrice = []
    for i in range(len(xLog)):
        penaltyCO2.append(xLog[i,0]*w1+(max(xLog[i,0],CO2Threshold)-CO2Threshold)*w3) 
        penaltyPrice.append(auxLog[i,1]*w2)
    return penaltyCO2, penaltyPrice

[penaltyCO2, penaltyPrice] = log_penalties()
time = np.linspace(0,timeStep*(steps-1),steps)
    
mpc_graphics = do_mpc.graphics.Graphics(mpc.data)

from matplotlib import rcParams
rcParams['axes.grid'] = True
rcParams['font.size'] = 18

fig, ax = plt.subplots(6, sharex=True, figsize=(16,12))
# Configure plot:
mpc_graphics.add_line(var_type='_x', var_name='CO2', axis=ax[0])
mpc_graphics.add_line(var_type='_u', var_name='pos', axis=ax[1])
mpc_graphics.add_line(var_type='_x', var_name='cost', axis=ax[2])
mpc_graphics.add_line(var_type='_aux', var_name='stepCost', axis=ax[3])
mpc_graphics.add_line(var_type='_aux', var_name='power', axis=ax[4])
ax[5].plot(time, penaltyCO2, label="CO2")
ax[5].plot(time, penaltyPrice, label='Price')
ax[0].set_ylabel('CO2 [ppm]')
ax[1].set_ylabel('Damper pos')
ax[2].set_ylabel('Cost [DKK]')
ax[3].set_ylabel('Step cost [DKK]')
ax[4].set_ylabel('Power [W]')
ax[5].set_ylabel('Penalty')
ax[5].set_xlabel('time [s]')
ax[5].legend()