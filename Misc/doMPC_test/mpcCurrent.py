import numpy as np
import matplotlib.pyplot as plt
import do_mpc
from Misc.settings import Settings
from casadi import *
from casadi.tools import *

# Weights for objective function
w1 = 0.001 # CO2
w2 = 1000 # Cost
w3 = w1 # additional penalty for CO2 above threshold
n_horizon = 50

def template_mpc(model, silence_solver = False):  
    mpc = do_mpc.controller.MPC(model)
    
    mpc.settings.n_horizon = n_horizon
    mpc.settings.n_robust = 0
    mpc.settings.open_loop = 0
    mpc.settings.t_step = 600
    mpc.settings.state_discretization = 'collocation'
    mpc.settings.collocation_type = 'radau'
    mpc.settings.collocation_deg = 3
    mpc.settings.collocation_ni = 1
    mpc.settings.store_full_solution = True
    
    if silence_solver:
        mpc.settings.supress_ipopt_output()

    # Objectives
    _x = model.x
    terminalCost = w2*(_x['cost']) # terminal cost
    stageCost = w1*(_x['CO2']-400)**2  # stage cost
    #stageCost = w1*(_x['CO2'])
    mpc.set_objective(mterm=terminalCost, lterm=stageCost)
    #mpc.set_nl_cons('CO2', _x['CO2'], ub=Settings.CO2Threshold, soft_constraint=True, penalty_term_cons=w3)

    # Bounds of the inputs
    mpc.bounds['lower', '_u', 'pos'] = 0
    mpc.bounds['upper', '_u', 'pos'] = 1

    tvp_template = mpc.get_tvp_template()

    def tvp_fun(t_ind): 
        for i in range(n_horizon):
            tvp_template['_tvp', i, 'occPredict'] = 20 - ((t_ind+i*Settings.timeStep)/600)%10
            if t_ind % 10000 > 7000:
                tvp_template['_tvp', i, 'elPrice'] = 0
            else:
                tvp_template['_tvp', i, 'elPrice'] = 500
        return tvp_template

    mpc.set_tvp_fun(tvp_fun)
    mpc.setup()
    return mpc

def template_simulator(model):
    simulator = do_mpc.simulator.Simulator(model)

    params_simulator = {
        # Note: cvode doesn't support DAE systems.
        'integration_tool': 'idas',
        'abstol': 1e-8,
        'reltol': 1e-8,
        't_step': Settings.timeStep
    }

    simulator.set_param(**params_simulator)

    tvp_template = simulator.get_tvp_template()

    def tvp_fun(t_ind):
        
        return tvp_template

    simulator.set_tvp_fun(tvp_fun)

    simulator.setup()

    return simulator

def template_model(symvar_type='SX'):
    model_type = 'continuous' # either 'discrete' or 'continuous'
    model = do_mpc.model.Model(model_type, symvar_type)
    
    # States struct (optimization variables):
    CO2 = model.set_variable(var_type='_x', var_name='CO2', shape=(1,1))
    model.set_variable(var_type='_x', var_name='cost', shape=(1,1))

    # Input struct (optimization variables):
    pos = model.set_variable(var_type='_u', var_name='pos')

    # Parameters
    timeStep = Settings.timeStep
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
    global elPrice
    elPrice = model.set_variable('_tvp', 'elPrice')
    global occPredict
    occPredict = model.set_variable('_tvp', 'occPredict')
    
    # Test parameters
    occ = 10
    price = 400
    
    # Aux terms
    flowSupFan = nomFlowDamper*pos/nomFlowSupFan
    plSupFan = flowSupFan #cSupFan[0] + cSupFan[1]*flowSupFan + cSupFan[2]*flowSupFan**2 + cSupFan[3]*flowSupFan**3
    wSupFan = plSupFan * nomWSupFan
    flowExhFan = nomFlowDamper*pos/nomFlowExhFan
    plExhFan = flowExhFan 
    wExhFan = plExhFan * nomWExhFan
    
    # variables for visualisation
    model.set_expression(expr_name='stepCost', expr=pos*price*timeStep/3600)
    model.set_expression(expr_name='power', expr=wSupFan+wExhFan)

    # Differential equations
    #model.set_rhs('CO2', (occ*CO2GenPerson*1000000-(nomFlowDamper*pos+airInf)*(CO2-CO2Out))/vol)
    model.set_rhs('CO2', (occ*CO2GenPerson*1000000-(nomFlowDamper*pos+airInf)*500)/vol)
    model.set_rhs("cost", (wSupFan+wExhFan) * elPrice /(3600*1000))

    model.setup()
    return model

# Initiate model, simulater, mpc and estimator
model = template_model()
simulator = template_simulator(model)
mpc = template_mpc(model)
estimator = do_mpc.estimator.StateFeedback(model)

# Set initial state
simulator.x0['CO2'] = 400
simulator.x0['cost'] = 0
x0 = simulator.x0.cat.full()
mpc.x0 = x0
estimator.x0 = x0
mpc.set_initial_guess()

# Run MPC main loop
n_steps = 50
for k in range(n_steps):
    u0 = mpc.make_step(x0)
    y_next = simulator.make_step(u0)
    x0 = estimator.make_step(y_next)

# Setup penalties
def log_penalties():
    xLog = mpc.data['_x']
    auxLog = mpc.data['_aux']
    penaltyCO2 = []
    penaltyPrice = []
    for i in range(len(xLog)):
        penaltyCO2.append(w1*Settings.timeStep*(xLog[i,0]-400)**2) 
        #penaltyCO2.append(xLog[i,0]*w1+(max(xLog[i,0],Settings.CO2Threshold)-Settings.CO2Threshold)*w3) 
        penaltyPrice.append(auxLog[i,1]*w2)
    return penaltyCO2, penaltyPrice

[penaltyCO2, penaltyPrice] = log_penalties()
time = np.linspace(0,Settings.timeStep*(n_steps-1),n_steps)

# Graphics
mpc_graphics = do_mpc.graphics.Graphics(mpc.data)
fig, ax = plt.subplots(8, sharex=True, figsize=(16,15))

mpc_graphics.add_line(var_type='_x', var_name='CO2', axis=ax[0])
mpc_graphics.add_line(var_type='_u', var_name='pos', axis=ax[1])
mpc_graphics.add_line(var_type='_x', var_name='cost', axis=ax[2])
mpc_graphics.add_line(var_type='_aux', var_name='stepCost', axis=ax[3])
mpc_graphics.add_line(var_type='_aux', var_name='power', axis=ax[4])
ax[5].plot(time, penaltyCO2, label="CO2")
ax[5].plot(time, penaltyPrice, label='Price')
mpc_graphics.add_line(var_type='_tvp', var_name='elPrice', axis=ax[6])
mpc_graphics.add_line(var_type='_tvp', var_name='occPredict', axis=ax[7])
ax[0].set_ylabel('CO2 [ppm]')
ax[1].set_ylabel('Damper pos')
ax[2].set_ylabel('Cost [DKK]')
ax[3].set_ylabel('Step cost [DKK]')
ax[4].set_ylabel('Power [W]')
ax[5].set_ylabel('Penalty')
ax[5].legend()
ax[6].set_ylabel('El price [DKK/MWh]')
ax[7].set_ylabel('Pred. occ')
ax[7].set_xlabel('time [s]')

