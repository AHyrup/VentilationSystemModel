import numpy as np
from casadi import *
import do_mpc

import matplotlib.pyplot as plt

model_type = 'continuous' # either 'discrete' or 'continuous'
model = do_mpc.model.Model(model_type)

# States struct (optimization variables):
CO2 = model.set_variable(var_type='_x', var_name='CO2', shape=(1,1))

# Input struct (optimization variables):
pos = model.set_variable(var_type='_u', var_name='pos')

# Certain parameters

model.set_rhs('CO2', -pos*CO2 + 50*0.7 - 50*CO2)

# Build the model
model.setup()

mpc = do_mpc.controller.MPC(model)

setup_mpc = {
    'n_horizon': 20,
    'n_robust': 0,
    'open_loop': 0,
    't_step': 0.005,
    'state_discretization': 'collocation',
    'collocation_type': 'radau',
    'collocation_deg': 2,
    'collocation_ni': 2,
    'store_full_solution': True,
    # Use MA27 linear solver in ipopt for faster calculations:
    #'nlpsol_opts': {'ipopt.linear_solver': 'MA27'}
}

mpc.set_param(**setup_mpc)

mpc.scaling['_u', 'pos'] = 100

_x = model.x
mterm = (_x['CO2'] - 0.6)**2 # terminal cost
lterm = (_x['CO2'] - 0.6)**2 # stage cost

mpc.set_objective(mterm=mterm, lterm=lterm)

mpc.set_rterm(pos=0.1) # input penalty

# lower bounds of the states
mpc.bounds['lower', '_x', 'CO2'] = 0.1

# upper bounds of the states
mpc.bounds['upper', '_x', 'CO2'] = 2

# lower bounds of the inputs
mpc.bounds['lower', '_u', 'pos'] = 5

# upper bounds of the inputs
mpc.bounds['upper', '_u', 'pos'] = 100

mpc.setup()

estimator = do_mpc.estimator.StateFeedback(model)

simulator = do_mpc.simulator.Simulator(model)

params_simulator = {
    'integration_tool': 'cvodes',
    'abstol': 1e-10,
    'reltol': 1e-10,
    't_step': 0.005
}

simulator.set_param(**params_simulator)

simulator.setup()

# Set the initial state of mpc, simulator and estimator:
CO2_0 = 0.5 # This is the controlled variable [mol/l]
x0 = np.array([CO2_0]).reshape(-1,1)

mpc.x0 = x0
simulator.x0 = x0
estimator.x0 = x0

mpc.set_initial_guess()

for k in range(50):
    u0 = mpc.make_step(x0)
    y_next = simulator.make_step(u0)
    x0 = estimator.make_step(y_next)
    
mpc_graphics = do_mpc.graphics.Graphics(mpc.data)

from matplotlib import rcParams
rcParams['axes.grid'] = True
rcParams['font.size'] = 18

fig, ax = plt.subplots(2, sharex=True, figsize=(16,12))
# Configure plot:
mpc_graphics.add_line(var_type='_x', var_name='CO2', axis=ax[0])
mpc_graphics.add_line(var_type='_u', var_name='pos', axis=ax[1])
ax[0].set_ylabel('CO2 [ppm]')
ax[1].set_ylabel('Flow [l/h]')
ax[1].set_xlabel('time [h]')