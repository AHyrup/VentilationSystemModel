from Misc.settings import Settings
import numpy as np
import do_mpc
import matplotlib.pyplot as plt

model_type = 'continuous' # either 'discrete' or 'continuous'
model = do_mpc.model.Model(model_type)

spaces = 2

#States and input:
CO2 = [None] * spaces
pos = [None] * spaces
for i in range(spaces):
    index = str(i)
    CO2[i] = model.set_variable(var_type='_x', var_name='CO2'+index, shape=(1,1))
    pos[i] = model.set_variable(var_type='_u', var_name='pos'+index, shape=(1,1))  
cost = model.set_variable(var_type='_x', var_name='cost', shape=(1,1))

# Settings
timeStep = Settings.timeStep
steps = 50
CO2Threshold = Settings.CO2Threshold

# Certain parameters
CO2GenPerson = Settings.CO2GenPerson # [m^3/s]
airInf = np.ones([spaces,1])*Settings.airInfSpace # [m^3/s]
vol = np.array([400, 500]) # [m^3] (test value)
nomFlowDamper = np.array([0.22, 0.3]) # [m^3/s] (test value)
CO2Out = Settings.ppmCO2Out
cSupFan = [0, 0.8321, -0.9847, 1.1526]
cExhFan = [0, 0.8843, -0.4617, 0.5775]
nomFlowSupFan = 12.08 # [m^3/s]
nomFlowExhFan = 11.74 # [m^3/s]
nomWSupFan = 9703 # W
nomWExhFan = 8462 # W

# Test parameters
occ = np.array([10, 5])
price = 400

# Weights for objective function
w1 = 1 # CO2
w2 = 50 # Cost
w3 = w1 # additional penalty for CO2 above threshold

# Aux terms
flowSupFan = (nomFlowDamper[0]*model.u['pos0']+nomFlowDamper[1]*model.u['pos1'])/nomFlowSupFan
plSupFan = flowSupFan #cSupFan[0] + cSupFan[1]*flowSupFan + cSupFan[2]*flowSupFan**2 + cSupFan[3]*flowSupFan**3
wSupFan = plSupFan * nomWSupFan
flowExhFan = (nomFlowDamper[0]*model.u['pos0']+nomFlowDamper[1]*model.u['pos1'])/nomFlowExhFan
plExhFan = flowExhFan 
wExhFan = plExhFan * nomWExhFan

# variables for visualisation
stepCost = model.set_expression(expr_name='stepCost', expr=(wSupFan+wExhFan)*price*timeStep/(3600*1000))
power = model.set_expression(expr_name='power', expr=wSupFan+wExhFan)

# Differential equations
for i in range(spaces):
    index = str(i)
    model.set_rhs('CO2'+index, (occ[i]*CO2GenPerson*1000000-(nomFlowDamper[i]*pos[i]+airInf[i])*(CO2[i]-CO2Out))/vol[i])
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

mpc.scaling['_u', 'pos0'] = 100
mpc.scaling['_u', 'pos1'] = 100


_x = model.x
terminalCost = w2*(_x['cost']) # terminal cost
stageCost = w1*sum(CO2)  # stage cost

mpc.set_objective(mterm=terminalCost, lterm=stageCost)

for i in range(spaces):
    index = str(i)
    mpc.set_nl_cons('CO2'+index, _x['CO2'+index], ub=CO2Threshold, soft_constraint=True, penalty_term_cons=w3)

# Bounds of the inputs
for i in range(spaces):
    index = str(i)
    mpc.bounds['lower', '_u', 'pos'+index] = 0
    mpc.bounds['upper', '_u', 'pos'+index] = 1

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

    
CO2Initial = np.array([400] * spaces)
costInitial = np.array([0])
x0 = np.concatenate((CO2Initial, costInitial))

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
    penaltyCO2 = np.empty((len(xLog),spaces))
    penaltyPrice = []
    for i in range(len(xLog)):
        for j in range(spaces):
            penaltyCO2[i,j]=xLog[i,j]*w1+(max(xLog[i,j],CO2Threshold)-CO2Threshold)*w3
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
mpc_graphics.add_line(var_type='_x', var_name='CO20', axis=ax[0])
mpc_graphics.add_line(var_type='_x', var_name='CO21', axis=ax[0])
mpc_graphics.add_line(var_type='_u', var_name='pos0', axis=ax[1])
mpc_graphics.add_line(var_type='_u', var_name='pos1', axis=ax[1])
mpc_graphics.add_line(var_type='_x', var_name='cost', axis=ax[2])
mpc_graphics.add_line(var_type='_aux', var_name='stepCost', axis=ax[3])
mpc_graphics.add_line(var_type='_aux', var_name='power', axis=ax[4])
ax[5].plot(time, penaltyCO2[:,0], label="CO2 space0")
ax[5].plot(time, penaltyCO2[:,1], label="CO2 space1")
ax[5].plot(time, penaltyPrice, label='Price')
ax[0].set_ylabel('CO2 [ppm]')
ax[1].set_ylabel('Damper pos')
ax[2].set_ylabel('Cost [DKK]')
ax[3].set_ylabel('Step cost [DKK]')
ax[4].set_ylabel('Power [W]')
ax[5].set_ylabel('Penalty')
ax[5].set_xlabel('time [s]')
ax[5].legend()
