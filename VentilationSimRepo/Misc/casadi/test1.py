import numpy as np
import casadi as ca

mpcSteps = 5
price = [100, 500, 500, 500, 700]
occ = [10, 12, 11, 8, 13]

opti = ca.Opti()

x = opti.variable(2, mpcSteps+1)  
u = opti.variable(2, mpcSteps)  
p = opti.parameter(2, mpcSteps)

opti.set_value(p, np.array([price, occ]))

for k in range(mpcSteps):
    opti.subject_to(x(:,k+1)==x(:,k)+x(:,k)*u(:,k))
    
"""# Define state, control, and parameter variables
x = ca.MX.sym("x", 1)  # State vector (n-dimensional)
u = ca.MX.sym("u", 1)  # Control vector (m-dimensional)
p = ca.MX.sym("p", 10)  # Time-dependent parameter vector (p_dim-dimensional)

# Define the system dynamics with the parameter p
f = ca.Function("f", [x, u, p], [your_dynamics_with_p(x, u, p)])

# Define the cost function including the parameter p
L = ca.Function("L", [x, u, p], [your_cost_with_p(x, u, p)])

opti = ca.Opti()

X = opti.variable(n, N+1)  # State variables
U = opti.variable(m, N)    # Control variables
P = opti.parameter(p_dim, N)  # Time-dependent parameters (dimension p_dim)

for i in range(mpcSteps):
    opti.subject_to(X[:, i+1] == f(X[:, i], U[:, i], P[:, i]))
    opti.set_value(P, current_parameter_values)  # Update parameters at each time step
    """