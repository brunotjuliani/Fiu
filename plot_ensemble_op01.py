import pandas as pd
import numpy as np
import gr5i
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Data previsao
d_prev = '2020-08-16'

# Leitura
PEQ = pd.read_csv('peq_'+d_prev+'.csv', skiprows=1, index_col='datahora_UTC')
area = pd.read_csv('peq_'+d_prev+'.csv', nrows=1, header=None).values[0][0]
ETP = PEQ['etp'].to_numpy()
Qjus = PEQ['qjus'].to_numpy()
PEQ['qmon'] = 0
Qmon = PEQ['qmon'].to_numpy()

#Simulacao GR5i
PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
QsimsGR = pd.DataFrame()
n=0
while n <= 50:
    PME = PEQ['pme_'+str(n)].to_numpy()
    QsimsGR['Qgr5_'+str(n)]= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                            PAR_GR['x1'], PAR_GR['x2'],
                                            PAR_GR['x3'], PAR_GR['x4'],
                                            PAR_GR['x5'])
    n += 1
QsimsGR.index = PEQ.index
QsimsGR['Qmed'] = QsimsGR.median(axis=1)
QsimsGR['Q25'] = QsimsGR.quantile(0.25, axis=1)
QsimsGR['Q75'] = QsimsGR.quantile(0.75, axis=1)
QsimsGR['Qobs'] = PEQ['qjus']
QsimsGR = QsimsGR.loc[d_prev:]
QsimsGR.to_csv('sim_GR_'+d_prev+'.csv', float_format='%.3f')

# Plotagem
fig = go.Figure()
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], name="Q75 (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], name="Q25 (m3/s)", marker_color='blue', fill='tonexty'))
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qsim_'+str(n)], name='Qsim_'+str(n), marker_color='darkgray'))
    n += 1
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], name="Q75 (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qmed'], name="Qmed (m3/s)", marker_color='red'))
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], name="Q25 (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qobs'], name="Qobs (m3/s)", marker_color='black'))
fig.show()
