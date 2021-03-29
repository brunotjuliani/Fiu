import pandas as pd
import sacsma
import sacsma2021
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Leitura
PEQ = pd.read_csv('../peq_fiu.csv', skiprows=1, index_col='datahora_UTC')
area = pd.read_csv('../peq_fiu.csv', nrows=1, header=None).values[0][0]
dt = 0.25
PME = PEQ['pme'].to_numpy()
ETP = PEQ['etp'].to_numpy()
Qjus = PEQ['qjus'].to_numpy()
fconv = area/(dt*86.4) # mm -> m3/s
PAR = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
Qsim= sacsma.simulacao(area, dt, PME, ETP,
                        PAR['parUZTWM'], PAR['parUZFWM'], PAR['parLZTWM'], PAR['parLZFPM'], PAR['parLZFSM'],
                        PAR['parADIMP'], PAR['parPCTIM'], PAR['parPFREE'],
                        PAR['parUZK'], PAR['parLZPK'], PAR['parLZSK'],
                        PAR['parZPERC'], PAR['parREXP'],
                        PAR['parK_HU'], PAR['parN_HU'])

params = pd.read_csv('par_sacsma2021_fiu.csv', index_col='parNome').to_dict('dict')['parValor']
Qsim2021, Qbfp, Qbfs, Qtci, Qtco = sacsma2021.simulacao(area, dt, PME, ETP, params, Qmon=None, estados=None)


# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=PEQ.index, y=PME, name="PME (mm)"), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
fig.add_trace(go.Scatter(x=PEQ.index, y=Qjus, name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig['data'][2]['line']['color']="black"
fig.add_trace(go.Scatter(x=PEQ.index, y=Qsim, name='Qsim - Antigo (m3/s)', marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=PEQ.index, y=Qsim2021, name='Qsim - Novo (m3/s)', marker_color='green'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_layout(legend_title_text='Comparação Modelo Sacramento')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.show()
