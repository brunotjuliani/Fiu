import pygrib
import numpy as np
import pandas as pd
import datetime as dt
import psycopg2, psycopg2.extras
import requests
import math
import csv
import sacsma
import gr5i
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path


################################################################################

## É NECESSARIO VERIFICAR O NOME DO ARQUIVO WRF!!!!!!!!!!!

################################################################################

## 1 - DATAS PADRAO
# Data do disparo
dispara = dt.datetime(2019, 5, 25,  00, tzinfo=dt.timezone.utc)
ano = dispara.year
mes = dispara.month
dia = dispara.day
d_prev = dispara.isoformat()
ini_obs = dispara-dt.timedelta(days=5)
ini_obs = ini_obs.isoformat()

################################################################################
################################################################################

df = pd.read_csv(f'../Simulacoes/Retroativo_WRF/{ano}_{mes:02d}_{dia:02d}_00/aval_{ano}{mes:02d}{dia:02d}00.csv',
                 index_col='datahora', parse_dates=True)
chuva_acum_atual = df.loc[dispara,'obs_acum']

q_hist = pd.read_csv('../Dados/vazao_fiu.csv', index_col='datahora')
q_hist.index = pd.to_datetime(q_hist.index, utc=True)
q_6h = q_hist.resample("6H", closed='right', label = 'right').mean()
q_6h = q_6h.loc[df.index[0]:df.index[-1]]
q_atual_obs = q_6h.loc[dispara,'qjus']

###############################################################################

# Plotagem Sacramento
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
#fig.add_trace(go.Bar(x=df.index, y=df['chuva_mm'], name="Chuva Registrada (mm)", marker=dict(color='dodgerblue',line=dict(color='darkblue', width=1))), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
#fig.add_trace(go.Scatter(x=[dispara], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=q_6h.index, y=q_6h['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.loc[dispara:].index, y=df.loc[dispara:,'qsac_anc_novo'], name="Sacramento c/ Anc.(m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['qsac_bru_novo'], name="Sacramento s/ Anc. (m3/s)", marker_color='blue'), row=2, col=1)
#fig.add_trace(go.Scatter(x=df.loc[dispara:].index, y=df.loc[dispara:,'qgr5_anc'], name="Simulação GR5i(m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=[dispara], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Simulações Hidrológicas')
fig.update_layout(autosize=False,width=900,height=500,margin=dict(l=30,r=30,b=10,t=10))
#fig.write_image(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/reuniao2_{ano:04d}{mes:02d}{dia:02d}.png')
#fig.show()


# ################################################################################
# ################################################################################
#
# # Plotagem GR5i
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Scatter(x=df.index, y=df['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
# fig.add_trace(go.Scatter(x=df.index, y=df['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
# fig.add_trace(go.Scatter(x=[dispara], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=q_6h.index, y=q_6h['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=df.loc[dispara:].index, y=df.loc[dispara:,'qgr5_anc'], name="Simulação (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[dispara], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo GR5i')
# fig.update_layout(autosize=False,width=900,height=500,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/reuniao_{ano:04d}{mes:02d}{dia:02d}_gr5i_reuniao.png')
# fig.show()


df2 = df[['chuva_mm', 'chuva_wrf', 'qsac_anc_novo', 'qgr5_anc']]

df3 = pd.merge(df2, q_6h, how = 'left', left_index = True, right_index = True)

df3.columns = ['chuva_obs', 'chuva_prev', 'simul_sac', 'simul_gr5', 'q_obs']

df3.loc[:dispara, 'chuva_prev'] = np.nan

df3.to_csv(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/dados_{ano:04d}{mes:02d}{dia:02d}.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')
