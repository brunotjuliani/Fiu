import pandas as pd
import numpy as np
import math
import sacsma2021
import gr5i
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
PEQ['Qmon'] = 0
Qmon = PEQ['Qmon']
PME = PEQ['pme']
ETP = PEQ['etp']
idx = PME.index
Qobs = PEQ[f'M_6'].rename('qobs')
Simul = pd.DataFrame()
Simul['QObs'] = Qobs

params = pd.read_csv(f'param_macs_{bnome}_Novo.csv',
                     index_col='Parametros')
Simul['SAC'] = sim(params['Par_MACS'])


PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
Simul['GR5i']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                        PAR_GR['x1'], PAR_GR['x2'],
                                        PAR_GR['x3'], PAR_GR['x4'],
                                        PAR_GR['x5'])

Simul = Simul.loc['2019':'2021']
Qobs = Qobs.loc['2019':'2021']

print('Nash SAC = ' + str(he.nse(Simul['SAC'],Qobs)))
print('Log-Nash SAC = ' + str(he.nse(np.log(Simul['SAC']),np.log(Qobs))))
print('PBIAS SAC = ' + str(hv.evaluator(hv.pbias,Simul['SAC'],Qobs)))

print('Nash Calib. GR5i = ' + str(he.nse(Simul['GR5i'],Qobs)))
print('Log-Nash Calib. GR5i = ' + str(he.nse(np.log(Simul['GR5i']),np.log(Qobs))))
print('PBIAS Calib. GR5i = ' + str(hv.evaluator(hv.pbias,Simul['GR5i'],Qobs)))

ano_print = '2020'
PME = PME.loc[ano_print]
Qobs = Qobs.loc[ano_print]
Simul = Simul.loc[ano_print]
idx = PME.index

fig = go.Figure()
fig.add_trace(go.Scatter(x=idx, y=Simul['SAC'], name='Modelo SAC-SMA', marker_color='red', marker_line_width=10))
fig.add_trace(go.Scatter(x=idx, y=Simul['GR5i'], name='Modelo GR5i', marker_color='green', marker_line_width=10))
fig.add_trace(go.Scatter(x=idx, y=Qobs, name="Vazão Observada", marker_color='black', marker_line_width=1))
fig.update_yaxes(title_text='Vazão [m3s-1]')
fig.update_layout(legend_title_text='Vazões Simuladas')
fig.update_layout(autosize=False,width=1000,height=500,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image('comparacao_vazoes.png')
fig.write_html('comparacao_vazoes.html')
fig.show()


# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Scatter(x=idx, y=PME, name="PME (mm)"), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# #fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
# fig.add_trace(go.Scatter(x=idx, y=Simul['SAC'], name='Modelo SAC-SMA', marker_color='red', marker_line_width=10), row=2, col=1)
# fig.add_trace(go.Scatter(x=idx, y=Simul['GR5i'], name='Modelo GR5i', marker_color='green', marker_line_width=10), row=2, col=1)
# fig.add_trace(go.Scatter(x=idx, y=Qobs, name="Vazão Observada", marker_color='black', marker_line_width=1), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_layout(legend_title_text='Vazões Simuladas')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image('comparacao_vazoes.png')
# fig.write_html('comparacao_vazoes.html')
# fig.show()
