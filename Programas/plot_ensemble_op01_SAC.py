import pandas as pd
import numpy as np
import gr5i
import sacsma
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Data previsao
d_prev = '2020-06-20'

# Leitura
PEQ = pd.read_csv('../peq_'+d_prev+'.csv', skiprows=1, index_col='datahora_UTC')
area = pd.read_csv('../peq_'+d_prev+'.csv', nrows=1, header=None).values[0][0]
ETP = PEQ['etp'].to_numpy()
Qjus = PEQ['qjus'].to_numpy()
PEQ['qmon'] = 0
Qmon = PEQ['qmon'].to_numpy()

# Simulacao SACRAMENTO
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('../par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS = pd.DataFrame()
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
#QsimsS.to_csv('sim_Sac_'+d_prev+'.csv', float_format='%.3f')

# Plotagem
fig = go.Figure()
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], showlegend=False, marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], showlegend=False, marker_color='blue', fill='tonexty'))
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'))
    n += 1
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qmed'], name="Mediana (m3/s)", marker_color='red'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'))
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qobs'], name="Qobs (m3/s)", marker_color='black'))
fig.update_yaxes(title_text='Vazão [m3s-1]')
fig.update_layout(legend_title_text='Modelo Sacramento')
fig.write_image('../teste_sacramento.png')
#fig.show()
