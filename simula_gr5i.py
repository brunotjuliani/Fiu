import pandas as pd
import gr5i
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Leitura
PEQ = pd.read_csv('peq_fiu.csv', skiprows=1, index_col='datahora_UTC')
area = pd.read_csv('peq_fiu.csv', nrows=1, header=None).values[0][0]
PME = PEQ['pme'].to_numpy()
ETP = PEQ['etp'].to_numpy()
Qjus = PEQ['qjus'].to_numpy()
PEQ['qmon'] = 0
Qmon = PEQ['qmon'].to_numpy()
PAR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
Qsim= gr5i.simulacao(PAR['dt'], area, PME, ETP, Qmon, PAR['x1'], PAR['x2'],
                     PAR['x3'], PAR['x4'], PAR['x5'])
# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=PEQ.index, y=PME, name="PME (mm)"), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
fig.add_trace(go.Scatter(x=PEQ.index, y=Qjus, name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig['data'][2]['line']['color']="black"
fig.add_trace(go.Scatter(x=PEQ.index, y=Qsim, name='Qsim (m3/s)', marker_color='red'), row=2, col=1)
fig.show()
