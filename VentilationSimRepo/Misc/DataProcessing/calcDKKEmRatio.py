import pandas as pd
import os
import math
from datetime import datetime
import datetime as dt
from dateutil.tz import tzutc
from Misc.settings import Settings

here = os.getcwd()
file = here + '\\PowerPredictions\\' + 'power_600s.csv'
df = pd.read_csv(file, sep=',')

price2024 = df['DKKPerMWh'].iloc[262944:-1]
em2024 = df['gCO2PerKWh'].iloc[262944:-1]


priceAvg = sum(price2024)/len(price2024)
emAvg = sum(em2024)/len(em2024)

ratio = priceAvg/emAvg