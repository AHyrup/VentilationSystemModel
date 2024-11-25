#
#   This file is part of do-mpc
#
#   do-mpc: An environment for the easy, modular and efficient implementation of
#        robust nonlinear model predictive control
#
#   Copyright (c) 2014-2019 Sergio Lucia, Alexandru Tatulea-Codrean
#                        TU Dortmund. All rights reserved
#
#   do-mpc is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as
#   published by the Free Software Foundation, either version 3
#   of the License, or (at your option) any later version.
#
#   do-mpc is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with do-mpc.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import matplotlib.pyplot as plt
from casadi import *
from casadi.tools import *
import pdb
import sys
import os
rel_do_mpc_path = os.path.join('..','..')
sys.path.append(rel_do_mpc_path)
import do_mpc

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle
from matplotlib import rcParams
from matplotlib.animation import FuncAnimation, FFMpegWriter, ImageMagickWriter
# Plot settings
rcParams['text.usetex'] = False
rcParams['axes.grid'] = True
rcParams['lines.linewidth'] = 2.0
rcParams['axes.labelsize'] = 'xx-large'
rcParams['xtick.labelsize'] = 'xx-large'
rcParams['ytick.labelsize'] = 'xx-large'

import time


def template_mpc(model, silence_solver = False):
    
    mpc = do_mpc.controller.MPC(model)

    mpc.settings.n_horizon =  20
    mpc.settings.n_robust =  0
    mpc.settings.open_loop =  0
    mpc.settings.t_step =  0.04
    mpc.settings.state_discretization =  'collocation'
    mpc.settings.collocation_type =  'radau'
    mpc.settings.collocation_deg =  3
    mpc.settings.collocation_ni =  1
    mpc.settings.store_full_solution =  True

    if silence_solver:
        mpc.settings.supress_ipopt_output()


    mterm = model.aux['E_kin'] - model.aux['E_pot']
    lterm = -model.aux['E_pot']+10*(model.x['pos']-model.tvp['pos_set'])**2 # stage cost

    mpc.set_objective(mterm=mterm, lterm=lterm)
    mpc.set_rterm(force=0.1)

    mpc.bounds['lower','_u','force'] = -4
    mpc.bounds['upper','_u','force'] = 4

    # Avoid the obstacles:
    mpc.set_nl_cons('obstacles', -model.aux['obstacle_distance'], 0)

    tvp_template = mpc.get_tvp_template()

    # When to switch setpoint:
    t_switch = 4    # seconds
    ind_switch = t_switch // mpc.settings.t_step

    def tvp_fun(t_ind):
        ind = t_ind // mpc.settings.t_step
        if ind <= ind_switch:
            tvp_template['_tvp',:, 'pos_set'] = -0.8
        else:
            tvp_template['_tvp',:, 'pos_set'] = 0.8
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
        't_step': 0.04
    }

    simulator.set_param(**params_simulator)

    tvp_template = simulator.get_tvp_template()

    def tvp_fun(t_ind):
        return tvp_template

    simulator.set_tvp_fun(tvp_fun)


    simulator.setup()

    return simulator

def template_model(obstacles, symvar_type='SX'):
    """
    --------------------------------------------------------------------------
    template_model: Variables / RHS / AUX
    --------------------------------------------------------------------------
    """
    model_type = 'continuous' # either 'discrete' or 'continuous'
    model = do_mpc.model.Model(model_type, symvar_type)

    # Certain parameters
    m0 = 0.6  # kg, mass of the cart
    m1 = 0.2  # kg, mass of the first rod
    m2 = 0.2  # kg, mass of the second rod
    L1 = 0.5  #m, length of the first rod
    L2 = 0.5  #m, length of the second rod
    l1 = L1/2
    l2 = L2/2
    J1 = (m1 * l1**2) / 3   # Inertia
    J2 = (m2 * l2**2) / 3   # Inertia

    m1 = 1
    m2 = 1

    g = 9.80665 # m/s^2, gravity

    h1 = m0 + m1 + m2
    h2 = m1*l1 + m2*L1
    h3 = m2*l2
    h4 = m1*l1**2 + m2*L1**2 + J1
    h5 = m2*l2*L1
    h6 = m2*l2**2 + J2
    h7 = (m1*l1 + m2*L1) * g
    h8 = m2*l2*g

    # Setpoint x:
    pos_set = model.set_variable('_tvp', 'pos_set')


    # States struct (optimization variables):
    pos = model.set_variable('_x',  'pos')
    theta = model.set_variable('_x',  'theta', (2,1))
    dpos = model.set_variable('_x',  'dpos')
    dtheta = model.set_variable('_x',  'dtheta', (2,1))
    # Algebraic states:
    ddpos = model.set_variable('_z', 'ddpos')
    ddtheta = model.set_variable('_z', 'ddtheta', (2,1))

    # Input struct (optimization variables):
    u = model.set_variable('_u',  'force')

    # Differential equations
    model.set_rhs('pos', dpos)
    model.set_rhs('theta', dtheta)
    model.set_rhs('dpos', ddpos)
    model.set_rhs('dtheta', ddtheta)

    # Euler Lagrange equations for the DIP system (in the form f(x,u,z) = 0)
    euler_lagrange = vertcat(
        # 1
        h1*ddpos+h2*ddtheta[0]*cos(theta[0])+h3*ddtheta[1]*cos(theta[1])
        - (h2*dtheta[0]**2*sin(theta[0]) + h3*dtheta[1]**2*sin(theta[1]) + u),
        # 2
        h2*cos(theta[0])*ddpos + h4*ddtheta[0] + h5*cos(theta[0]-theta[1])*ddtheta[1]
        - (h7*sin(theta[0]) - h5*dtheta[1]**2*sin(theta[0]-theta[1])),
        # 3
        h3*cos(theta[1])*ddpos + h5*cos(theta[0]-theta[1])*ddtheta[0] + h6*ddtheta[1]
        - (h5*dtheta[0]**2*sin(theta[0]-theta[1]) + h8*sin(theta[1]))
    )

    model.set_alg('euler_lagrange', euler_lagrange)

    # Expressions for kinetic and potential energy
    E_kin_cart = 1 / 2 * m0 * dpos**2
    E_kin_p1 = 1 / 2 * m1 * (
        (dpos + l1 * dtheta[0] * cos(theta[0]))**2 +
        (l1 * dtheta[0] * sin(theta[0]))**2) + 1 / 2 * J1 * dtheta[0]**2
    E_kin_p2 = 1 / 2 * m2 * (
        (dpos + L1 * dtheta[0] * cos(theta[0]) + l2 * dtheta[1] * cos(theta[1]))**2 +
        (L1 * dtheta[0] * sin(theta[0]) + l2 * dtheta[1] * sin(theta[1]))**
        2) + 1 / 2 * J2 * dtheta[0]**2

    E_kin = E_kin_cart + E_kin_p1 + E_kin_p2

    E_pot = m1 * g * l1 * cos(
    theta[0]) + m2 * g * (L1 * cos(theta[0]) +
                                l2 * cos(theta[1]))

    model.set_expression('E_kin', E_kin)
    model.set_expression('E_pot', E_pot)

    # Calculations to avoid obstacles:

    # Coordinates of the nodes:
    node0_x = model.x['pos']
    node0_y = np.array([0])

    node1_x = node0_x+L1*sin(model.x['theta',0])
    node1_y = node0_y+L1*cos(model.x['theta',0])

    node2_x = node1_x+L2*sin(model.x['theta',1])
    node2_y = node1_y+L2*cos(model.x['theta',1])

    obstacle_distance = []

    for obs in obstacles:
        d0 = sqrt((node0_x-obs['x'])**2+(node0_y-obs['y'])**2)-obs['r']*1.05
        d1 = sqrt((node1_x-obs['x'])**2+(node1_y-obs['y'])**2)-obs['r']*1.05
        d2 = sqrt((node2_x-obs['x'])**2+(node2_y-obs['y'])**2)-obs['r']*1.05
        obstacle_distance.extend([d0, d1, d2])


    model.set_expression('obstacle_distance',vertcat(*obstacle_distance))
    model.set_expression('tvp', pos_set)


    # Build the model
    model.setup()

    return model

""" User settings: """
show_animation = True
store_animation = False
store_results = False

# Define obstacles to avoid (cicles)
obstacles = [
    {'x': 0., 'y': 0.6, 'r': 0.3},
]

scenario = 1  # 1 = down-down start, 2 = up-up start, both with setpoint change.

"""
Get configured do-mpc modules:
"""

model = template_model(obstacles)
simulator = template_simulator(model)
mpc = template_mpc(model)
estimator = do_mpc.estimator.StateFeedback(model)

"""
Set initial state
"""

if scenario == 1:
    simulator.x0['theta'] = .9*np.pi
    simulator.x0['pos'] = 0
elif scenario == 2:
    simulator.x0['theta'] = 0.
    simulator.x0['pos'] = 0.8
else:
    raise Exception('Scenario not defined.')

x0 = simulator.x0.cat.full()

mpc.x0 = x0
estimator.x0 = x0

mpc.set_initial_guess()
z0 = simulator.init_algebraic_variables()

"""
Setup graphic:
"""

# Function to create lines:
L1 = 0.5  #m, length of the first rod
L2 = 0.5  #m, length of the second rod
def pendulum_bars(x):
    x = x.flatten()
    # Get the x,y coordinates of the two bars for the given state x.
    line_1_x = np.array([
        x[0],
        x[0]+L1*np.sin(x[1])
    ])

    line_1_y = np.array([
        0,
        L1*np.cos(x[1])
    ])

    line_2_x = np.array([
        line_1_x[1],
        line_1_x[1] + L2*np.sin(x[2])
    ])

    line_2_y = np.array([
        line_1_y[1],
        line_1_y[1] + L2*np.cos(x[2])
    ])

    line_1 = np.stack((line_1_x, line_1_y))
    line_2 = np.stack((line_2_x, line_2_y))

    return line_1, line_2

mpc_graphics = do_mpc.graphics.Graphics(mpc.data)

fig = plt.figure(figsize=(16,9))
plt.ion()

ax1 = plt.subplot2grid((4, 2), (0, 0), rowspan=4)
ax2 = plt.subplot2grid((4, 2), (0, 1))
ax3 = plt.subplot2grid((4, 2), (1, 1))
ax4 = plt.subplot2grid((4, 2), (2, 1))
ax5 = plt.subplot2grid((4, 2), (3, 1))

ax2.set_ylabel('$E_{kin}$ [J]')
ax3.set_ylabel('$E_{pot}$ [J]')
ax4.set_ylabel('position  [m]')
ax5.set_ylabel('Input force [N]')

mpc_graphics.add_line(var_type='_aux', var_name='E_kin', axis=ax2)
mpc_graphics.add_line(var_type='_aux', var_name='E_pot', axis=ax3)
mpc_graphics.add_line(var_type='_x', var_name='pos', axis=ax4)
mpc_graphics.add_line(var_type='_tvp', var_name='pos_set', axis=ax4)
mpc_graphics.add_line(var_type='_u', var_name='force', axis=ax5)

ax1.axhline(0,color='black')

# Axis on the right.
for ax in [ax2, ax3, ax4, ax5]:
    ax.yaxis.set_label_position("right")
    ax.yaxis.tick_right()

    if ax != ax5:
        ax.xaxis.set_ticklabels([])

ax5.set_xlabel('time [s]')

bar1 = ax1.plot([],[], '-o', linewidth=5, markersize=10)
bar2 = ax1.plot([],[], '-o', linewidth=5, markersize=10)


for obs in obstacles:
    circle = Circle((obs['x'], obs['y']), obs['r'])
    ax1.add_artist(circle)

ax1.set_xlim(-1.8,1.8)
ax1.set_ylim(-1.2,1.2)
ax1.set_axis_off()

fig.align_ylabels()
fig.tight_layout()


"""
Run MPC main loop:
"""
time_list = []

n_steps = 240
for k in range(n_steps):
    tic = time.time()
    u0 = mpc.make_step(x0)
    toc = time.time()
    y_next = simulator.make_step(u0)
    x0 = estimator.make_step(y_next)

    time_list.append(toc-tic)


    if show_animation:
        line1, line2 = pendulum_bars(x0)
        bar1[0].set_data(line1[0],line1[1])
        bar2[0].set_data(line2[0],line2[1])
        mpc_graphics.plot_results()
        mpc_graphics.plot_predictions()
        mpc_graphics.reset_axes()
        plt.show()
        plt.pause(0.04)

time_arr = np.array(time_list)
mean = np.round(np.mean(time_arr[1:])*1000)
var = np.round(np.std(time_arr[1:])*1000)
print('mean runtime:{}ms +- {}ms for MPC step'.format(mean, var))


# The function describing the gif:
if store_animation:
    x_arr = mpc.data['_x']
    def update(t_ind):
        line1, line2 = pendulum_bars(x_arr[t_ind])
        bar1[0].set_data(line1[0],line1[1])
        bar2[0].set_data(line2[0],line2[1])
        mpc_graphics.plot_results(t_ind)
        mpc_graphics.plot_predictions(t_ind)
        mpc_graphics.reset_axes()

    anim = FuncAnimation(fig, update, frames=n_steps, repeat=False)
    gif_writer = ImageMagickWriter(fps=20)
    anim.save('anim_dip.gif', writer=gif_writer)


# Store results:
if store_results:
    do_mpc.data.save_results([mpc, simulator], 'dip_mpc')

input('Press any key to exit.')
