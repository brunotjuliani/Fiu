import pandas as pd
import sacsma
import gr5i
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Leitura
inicio = dt.datetime(2021, 3, 16,  00, tzinfo=dt.timezone.utc)
d_ini = inicio.isoformat()
final = dt.datetime(2021, 3, 26,  00, tzinfo=dt.timezone.utc)
d_fim = final.isoformat()
area = 534


vazao_hr = pd.read_csv(f'../Dados/vazao_fiu.csv',index_col='datahora', parse_dates=True)
vazao_hr = vazao_hr.loc[d_ini:d_fim]
vazao_6hrs = vazao_hr.copy().resample("6H", closed='right', label = 'right').mean()
vazao_6hrs

chuva_hr = pd.read_csv(f'../Dados/pme_fiu.csv',index_col='datahora', parse_dates=True)
chuva_hr = chuva_hr.loc[d_ini:d_fim]
chuva_6hrs = chuva_hr.copy().resample("6H", closed='right', label = 'right').sum()

#Somatorio chuvas observada e prevista
chuva_6hrs['obs_acum'] = chuva_6hrs['chuva_mm'].cumsum()


# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Bar(x=chuva_6hrs.index, y=chuva_6hrs['chuva_mm'], name="Chuva Observada - 6 hrs", marker=dict(color='cornflowerblue',line=dict(color='navy', width=1))), row=1, col=1)
#fig.add_trace(go.Scatter(x=chuva_6hrs.index, y=chuva_6hrs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=vazao_hr.index, y=vazao_hr['qjus'], name="Vazão Horária (m3/s)", marker_color='cadetblue'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_6hrs.index, y=vazao_6hrs['qjus'], name="Vazão Média - 6hrs (m3/s)", marker_color='black'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Dados Observados')
fig.update_layout(autosize=False,width=900,height=500,margin=dict(l=30,r=30,b=10,t=10))
#fig.write_image(f'../Ancoragem/teste_{ano:04d}{mes:02d}{dia:02d}_sac.png')
fig.show()
