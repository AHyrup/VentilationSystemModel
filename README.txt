This repository contains a ventilation system model and data for simulation of OU44 (university building in Odense, Denmark). Use of the model with this data is showcased in this article: https://doi.org/10.3390/app15010451

To run a simulation for OU44:
1. Ensure you have python and the libraries listed below installed.
2. Run the file "Misc\DataProcessing\generateOccPredictions.py" to generate occupancy profiles (they were too large to upload)
3. Run a simulation in the "Simulations" folder

Known issues:
- The "GEKKO" library seems not to be working at the moment (15/11/24). In that case the MPC controller does not function.
- The model cannot handle summer time/winter time switches. Choose a simulation without these (this should be easy to fix, but this repository will not recieve updates) 

Libraries used:
- os
- pandas
- datetime
- numpy
- dateutil.tz 
- pytz 
- math
- matplotlib.pyplot
- openpyxl
- warnings
- time
- tabulate
- gekko

All measurement are in SI-units unless otherwise specified (or missed)

Abbriviations for naming:
    sup = supply
    exh = exhaust
    gen = generation
    occ = occupancy
    ven = ventilation
    pos = position (typically opening degree)
    flow = flowrate
    m = mass
    M = molar mass
    rho = density
    W = power
    prev = previous
    vol = volume
    inf = infiltration
    out = outdoor (Condition around element)
    inf = infiltration
    config = configuration
    dict = dictionary
    env = environment
    sys = system
    var = variable
    df = dataframe
    id = identification
    sim = simulation
    pred = predicted
    emm = emission
    

