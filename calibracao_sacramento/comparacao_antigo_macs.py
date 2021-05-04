import pandas as pd
import numpy as np
import math
import sacsma2021
import datetime
from sacsma2021 import Xnomes, Xmin, Xmax
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def sim(X):
    params = X
    Qsim = sacsma2021.simulacao(area, dt, PME, ETP, params)
    Qsim = pd.Series(index=idx, data=Qsim, name='qsim')
    return Qsim

### LEITURA FORÇANTES
bn = 'XX'
bnome = 'Fiu'
area = pd.read_csv(f'../Dados/{bnome}_peq.csv', nrows=1, header=None).values[0][0]
dt = 0.25 # 6 hr
PEQ = pd.read_csv(f'../Dados/{bnome}_peq.csv', skiprows=1,
                  parse_dates=True, index_col='datahora')
PME = PEQ['pme']
ETP = PEQ['etp']
idx = PME.index
Qobs = PEQ[f'M_6'].rename('qobs')

Simul = pd.DataFrame()

for m_hrs in [6, 12, 'Antigo']:
    params = pd.read_csv(f'./param_macs/param_macs_{bnome}_{m_hrs}.csv',
                         index_col='Parametros')
    Simul[f'MACS_{m_hrs}'] = sim(params['Par_MACS'])

#Simul = Simul.loc['2021-03']

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=idx, y=PME, name="PME (mm)"), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
#fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qobs, name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Simul['MACS_6'], name='Calibração MACS - 6 hrs', marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Simul['MACS_12'], name='Calibração MACS - 12 hrs', marker_color='purple'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Simul['MACS_Antigo'], name='Calibração Antiga', marker_color='red'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_layout(legend_title_text='Comparação Modelo Sacramento')
fig.update_layout(autosize=False,width=800,height=450,margin=dict(l=30,r=30,b=10,t=10))
fig.write_html(f'./param_macs/teste_calib_{bnome}.html')
fig.show()
