import pandas as pd
import numpy as np
import math
import sacsma2021
import datetime
from sacsma2021 import Xnomes, Xmin, Xmax
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import HydroErr as he
import hydroeval as hv

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

for m_hrs in ['Novo', 'Anterior']:
    params = pd.read_csv(f'./param_macs/param_macs_{bnome}_{m_hrs}.csv',
                         index_col='Parametros')
    Simul[f'Simul_{m_hrs}'] = sim(params['Par_MACS'])
Simul['QObs'] = Qobs
Simul.to_csv('./param_macs/simulacoes.csv', sep = ",",
             date_format='%Y-%m-%dT%H:%M:%S+00:00', float_format = '%.3f')
Simul

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=idx, y=PME, name="PME (mm)"), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
#fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qobs, name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Simul['Simul_Anterior'], name='Calibração Anterior', marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Simul['Simul_Novo'], name='Calibração Nova', marker_color='green'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_layout(legend_title_text='Comparação Modelo Sacramento')
fig.update_layout(autosize=False,width=800,height=450,margin=dict(l=30,r=30,b=10,t=10))
fig.write_html(f'./param_macs/teste_calib_{bnome}.html')
fig.show()

Simul = Simul.loc['2019':'2021']
Qobs = Qobs.loc['2019':'2021']

print('Nash Calib. Nova = ' + str(he.nse(Simul['Simul_Novo'],Qobs)))
print('Log-Nash Calib. Nova = ' + str(he.nse(np.log(Simul['Simul_Novo']),np.log(Qobs))))
print('PBIAS Calib. Nova = ' + str(hv.evaluator(hv.pbias,Simul['Simul_Novo'],Qobs)))

print('Nash Calib. Anterior = ' + str(he.nse(Simul['Simul_Anterior'],Qobs)))
print('Log-Nash Calib. Anterior = ' + str(he.nse(np.log(Simul['Simul_Anterior']),np.log(Qobs))))
print('PBIAS Calib. Anterior = ' + str(hv.evaluator(hv.pbias,Simul['Simul_Anterior'],Qobs)))
