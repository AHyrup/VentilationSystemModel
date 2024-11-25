import pandas as pd

df = pd.read_csv('power_600s.csv', sep=',')

notFloat = []
for idx in range(len(df['gCO2PerKWh'])):
    if type(df['gCO2PerKWh'][idx]) != float:
        notFloat.append(idx)
        