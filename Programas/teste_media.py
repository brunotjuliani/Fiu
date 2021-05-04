import pandas as pd
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import requests
import pytz
import numpy as np

vazao = pd.read_excel('../Dados/Fiu_CAV_2013_2021.xlsx')
vazao.index = (pd.to_datetime(vazao.Data) + pd.to_timedelta(vazao.Hora, unit = 'h'))
vazao.index = vazao.index.tz_localize('UTC')
vazao['qjus'] = np.where((vazao['VAZAO AFLUENTE'] == 'S/L'), np.nan, vazao['VAZAO AFLUENTE'])
vazao = vazao[['qjus']]
vazao2 = pd.DataFrame()
vazao2['qjus'] = pd.to_numeric(vazao.loc[:,'qjus'])
vazao2['qjus'] = np.where((vazao2['qjus'] < 0), np.nan, vazao2['qjus'])

# vazao = pd.read_csv('../Dados/vazao_fiu.csv', index_col='datahora')
# vazao.index = pd.to_datetime(vazao.index, utc=True)
# vazao2 = vazao.copy()


df2 = pd.DataFrame()
df2['Qobs'] = vazao2['qjus']
df2['M_24'] = df2['Qobs'].rolling(window=24, min_periods=1).mean()
df2['M_12'] = df2['Qobs'].rolling(window=12, min_periods=1).mean()
df2['M_6'] = df2['Qobs'].rolling(window=6, min_periods=1).mean()
df2['M_4'] = df2['Qobs'].rolling(window=4, min_periods=1).mean()

#df_aval = df2.loc['2021-04-01':'2021-04-14']
df_aval = df2.copy()

# Plotagem
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_aval.index, y=df_aval['Qobs'], name=f"Q afluente - novo (m3/s)", marker_color='black'))
fig.add_trace(go.Scatter(x=df_aval.index, y=df_aval['M_4'], name="Média - 4h (m3/s)", marker_color='red'))
fig.add_trace(go.Scatter(x=df_aval.index, y=df_aval['M_6'], name="Média - 6h (m3/s)", marker_color='dodgerblue'))
fig.add_trace(go.Scatter(x=df_aval.index, y=df_aval['M_12'], name="Média - 12h (m3/s)", marker_color='darkviolet'))
fig.add_trace(go.Scatter(x=df_aval.index, y=df_aval['M_24'], name="Média - 24h (m3/s)", marker_color='darkgreen'))
fig.update_yaxes(title_text='Vazão [m3s-1]')
fig.update_xaxes(tickformat="%Y-%m-%d %H")
#fig.update_layout(title={'text':f'Simulação {nome}', 'x':0.5, 'xanchor':'center', 'y':0.95})
fig.update_layout(autosize=False,width=1000,height=400,margin=dict(l=30,r=30,b=10,t=10))
fig.update_layout(legend_title='Trend')
#fig.write_image(f'./Resultados/{dispara.month:02d}_{dispara.day:02d}/{sigla}.png')
fig.show()
