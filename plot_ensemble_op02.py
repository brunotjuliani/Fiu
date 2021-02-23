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

# Simulacao SACRAMENTO
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
n = 0
while n <=50:
    PME = PEQ['pme_'+str(n)].to_numpy()
    QsimsS['Qsac_'+str(n)]=sacsma.simulacao(area, dt, PME, ETP,
                PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
                PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
                PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
                PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
                PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
    n += 1
QsimsS.index = PEQ.index
QsimsS['Qmed'] = QsimsS.median(axis=1)
QsimsS['Q25'] = QsimsS.quantile(0.25, axis=1)
QsimsS['Q75'] = QsimsS.quantile(0.75, axis=1)
QsimsS['Qobs'] = PEQ['qjus']
QsimsS = QsimsS.loc[d_prev:]
QsimsS.to_csv('sim_Sac_'+d_prev+'.csv', float_format='%.3f')


# Plotagem
fig = go.Figure()
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qmed'], name="GR5i - Qmed (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qmed'], name="SACSMA - Qmed (m3/s)", marker_color='red'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qobs'], name="Qobs (m3/s)", marker_color='black'))
fig.show()
