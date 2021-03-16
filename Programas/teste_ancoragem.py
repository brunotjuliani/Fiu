import pandas as pd
import sacsma
import gr5i
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Leitura
dispara = dt.datetime(2021, 3, 8,  00, tzinfo=dt.timezone.utc)
d_prev = dispara.isoformat()
ini_obs = dispara-dt.timedelta(days=5)
ini_obs = ini_obs.isoformat()
ano = dispara.year
mes = dispara.month
dia = dispara.day
area = 534

vazao_obs = pd.read_csv(f'../Dados/vazao_fiu.csv',index_col='datahora', parse_dates=True)
vazao_obs = vazao_obs.resample("6H", closed='right', label = 'right').mean()
vazao_obs = vazao_obs.loc[ini_obs:]
dados_obs = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/obs_{ano:04d}{mes:02d}{dia:02d}00.csv',
                        index_col='datahora', parse_dates=True)
obs_fig = dados_obs.loc[ini_obs:]
q_atual_obs = dados_obs.loc[d_prev,'q_m3s']
dados_prev = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/prev_{ano:04d}{mes:02d}{dia:02d}00.csv',
                         index_col='datahora', parse_dates=True)
dados_peq = pd.DataFrame()
dados_peq['etp_mm'] = pd.concat([dados_obs['etp_mm'], dados_prev['etp']])
dados_peq['pme_wrf'] = pd.concat([dados_obs['chuva_mm'], dados_prev['pme_wrf']])
n = 0
while n <=50:
    dados_peq['pme_'+str(n)] = pd.concat([dados_obs['chuva_mm'], dados_prev['pme_'+str(n)]])
    n += 1

ETP = dados_peq['etp_mm'].to_numpy()
dados_peq['qmon'] = 0
Qmon = dados_peq['qmon'].to_numpy()


dados0 = dados_peq.iloc[-10:]
dados0

dados_peq
dados_peq.iloc[-5:] += 5
dados_peq.iloc[-10:]





################################################################################
#####----- SIMULACAO BRUTA -- ##################################################
################################################################################

# ## 8 - SIMULACAO SACRAMENTO
# print('Simulação Sacramento')
# dt = 0.25
# fconv = area/(dt*86.4) # mm -> m3/s
# PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
# QsimsS = pd.DataFrame()
# #Simula para ECMWF e faz quantis
# n = 0
# while n <=50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsS['Qsac_'+str(n)]=sacsma.simulacao(area, dt, PME, ETP,
#                 PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#                 PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#                 PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#                 PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#                 PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
#     n += 1
# QsimsS.index = dados_peq.index
# QsimsS['Qmed'] = QsimsS.median(axis=1)
# QsimsS['Q25'] = QsimsS.quantile(0.25, axis=1)
# QsimsS['Q75'] = QsimsS.quantile(0.75, axis=1)
# QsimsS['Qmax'] = QsimsS.max(axis=1)
# QsimsS['Qmin'] = QsimsS.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
#             PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#             PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#             PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#             PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#             PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
# QsimsS = QsimsS.loc[ini_obs:]
# q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo Sacramento')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/bruto_{ano:04d}{mes:02d}{dia:02d}_sac.png')
#
# ## 9 - SIMULACAO GR5i
# print('Simulação GR5')
# PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
# QsimsGR = pd.DataFrame()
# #Simula para ECMWF e tira quantis
# n=0
# while n <= 50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsGR['Qgr5_'+str(n)]= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                             PAR_GR['x1'], PAR_GR['x2'],
#                                             PAR_GR['x3'], PAR_GR['x4'],
#                                             PAR_GR['x5'])
#     n += 1
# QsimsGR.index = dados_peq.index
# QsimsGR['Qmed'] = QsimsGR.median(axis=1)
# QsimsGR['Q25'] = QsimsGR.quantile(0.25, axis=1)
# QsimsGR['Q75'] = QsimsGR.quantile(0.75, axis=1)
# QsimsGR['Qmax'] = QsimsGR.max(axis=1)
# QsimsGR['Qmin'] = QsimsGR.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                         PAR_GR['x1'], PAR_GR['x2'],
#                                         PAR_GR['x3'], PAR_GR['x4'],
#                                         PAR_GR['x5'])
# QsimsGR = QsimsGR.loc[ini_obs:]
# q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qgr5_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo GR5i')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/bruto_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')










################################################################################
#####----- TRATATIVA 1 - ANCORAGEM -- ##########################################
################################################################################

# ## 8 - SIMULACAO SACRAMENTO
# print('Simulação Sacramento')
# dt = 0.25
# fconv = area/(dt*86.4) # mm -> m3/s
# PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
# QsimsS = pd.DataFrame()
# #Simula para ECMWF e faz quantis
# n = 0
# while n <=50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsS['Qsac_'+str(n)]=sacsma.simulacao(area, dt, PME, ETP,
#                 PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#                 PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#                 PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#                 PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#                 PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
#     n += 1
# QsimsS.index = dados_peq.index
# QsimsS['Qmed'] = QsimsS.median(axis=1)
# QsimsS['Q25'] = QsimsS.quantile(0.25, axis=1)
# QsimsS['Q75'] = QsimsS.quantile(0.75, axis=1)
# QsimsS['Qmax'] = QsimsS.max(axis=1)
# QsimsS['Qmin'] = QsimsS.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
#             PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#             PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#             PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#             PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#             PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
# QsimsS = QsimsS.loc[ini_obs:]
# q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
# anc_sac = q_atual_obs - q_atual_sac
# QsimsS2 = QsimsS + anc_sac
#
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS2.index, y=QsimsS2['Qsac_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo Sacramento')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/anc1_{ano:04d}{mes:02d}{dia:02d}_sac.png')
#
# ## 9 - SIMULACAO GR5i
# print('Simulação GR5')
# PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
# QsimsGR = pd.DataFrame()
# #Simula para ECMWF e tira quantis
# n=0
# while n <= 50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsGR['Qgr5_'+str(n)]= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                             PAR_GR['x1'], PAR_GR['x2'],
#                                             PAR_GR['x3'], PAR_GR['x4'],
#                                             PAR_GR['x5'])
#     n += 1
# QsimsGR.index = dados_peq.index
# QsimsGR['Qmed'] = QsimsGR.median(axis=1)
# QsimsGR['Q25'] = QsimsGR.quantile(0.25, axis=1)
# QsimsGR['Q75'] = QsimsGR.quantile(0.75, axis=1)
# QsimsGR['Qmax'] = QsimsGR.max(axis=1)
# QsimsGR['Qmin'] = QsimsGR.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                         PAR_GR['x1'], PAR_GR['x2'],
#                                         PAR_GR['x3'], PAR_GR['x4'],
#                                         PAR_GR['x5'])
# QsimsGR = QsimsGR.loc[ini_obs:]
# q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
# anc_gr5 = q_atual_obs - q_atual_gr5
# QsimsGR2 = QsimsGR + anc_gr5
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Qgr5_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR2.index, y=QsimsGR2['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo GR5i')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/anc1_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')










################################################################################
#####----- TRATATIVA 2 - PROPORCAO -- ##########################################
################################################################################

# ## 8 - SIMULACAO SACRAMENTO
# print('Simulação Sacramento')
# dt = 0.25
# fconv = area/(dt*86.4) # mm -> m3/s
# PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
# QsimsS = pd.DataFrame()
# #Simula para ECMWF e faz quantis
# n = 0
# while n <=50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsS['Qsac_'+str(n)]=sacsma.simulacao(area, dt, PME, ETP,
#                 PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#                 PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#                 PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#                 PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#                 PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
#     n += 1
# QsimsS.index = dados_peq.index
# QsimsS['Qmed'] = QsimsS.median(axis=1)
# QsimsS['Q25'] = QsimsS.quantile(0.25, axis=1)
# QsimsS['Q75'] = QsimsS.quantile(0.75, axis=1)
# QsimsS['Qmax'] = QsimsS.max(axis=1)
# QsimsS['Qmin'] = QsimsS.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
#             PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
#             PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
#             PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
#             PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
#             PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
# QsimsS = QsimsS.loc[ini_obs:]
# q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
# QsimsS3 = QsimsS * q_atual_obs/q_atual_sac
#
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsS3.index, y=QsimsS3['Qsac_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo Sacramento')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/anc2_{ano:04d}{mes:02d}{dia:02d}_sac.png')
#
# ## 9 - SIMULACAO GR5i
# print('Simulação GR5')
# PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
# QsimsGR = pd.DataFrame()
# #Simula para ECMWF e tira quantis
# n=0
# while n <= 50:
#     PME = dados_peq['pme_'+str(n)].to_numpy()
#     QsimsGR['Qgr5_'+str(n)]= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                             PAR_GR['x1'], PAR_GR['x2'],
#                                             PAR_GR['x3'], PAR_GR['x4'],
#                                             PAR_GR['x5'])
#     n += 1
# QsimsGR.index = dados_peq.index
# QsimsGR['Qmed'] = QsimsGR.median(axis=1)
# QsimsGR['Q25'] = QsimsGR.quantile(0.25, axis=1)
# QsimsGR['Q75'] = QsimsGR.quantile(0.75, axis=1)
# QsimsGR['Qmax'] = QsimsGR.max(axis=1)
# QsimsGR['Qmin'] = QsimsGR.min(axis=1)
# #Simula para WRF
# PME = dados_peq['pme_wrf'].to_numpy()
# QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
#                                         PAR_GR['x1'], PAR_GR['x2'],
#                                         PAR_GR['x3'], PAR_GR['x4'],
#                                         PAR_GR['x5'])
# QsimsGR = QsimsGR.loc[ini_obs:]
# q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
# QsimsGR3 = QsimsGR * q_atual_obs/q_atual_gr5
# # Plotagem
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
# fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.layout['bargap']=0
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
# n=0
# while n <= 50:
#     fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Qgr5_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
#     n += 1
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
# fig.add_trace(go.Scatter(x=QsimsGR3.index, y=QsimsGR3['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
# fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
# fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
# fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
# fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
# fig.update_xaxes(tickformat="%Y-%m-%dT%H")
# fig.update_layout(legend_title_text='Modelo GR5i')
# fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
# fig.write_image(f'../Ancoragem/anc2_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')










################################################################################
#####----- TRATATIVA 3 - CHUVA CONSTANTE -- ##########################################
################################################################################

dados_peq = pd.DataFrame()
dados_peq['etp_mm'] = pd.concat([dados_obs['etp_mm'], dados_prev['etp']])
#incremento de 0.5 mm
dados_obs['chuva_mm'] = dados_obs['chuva_mm'] + 0.15
dados_peq['pme_wrf'] = pd.concat([dados_obs['chuva_mm'], dados_prev['pme_wrf']])
n = 0
while n <=50:
    dados_peq['pme_'+str(n)] = pd.concat([dados_obs['chuva_mm'], dados_prev['pme_'+str(n)]])
    n += 1

ETP = dados_peq['etp_mm'].to_numpy()
dados_peq['qmon'] = 0
Qmon = dados_peq['qmon'].to_numpy()

## 8 - SIMULACAO SACRAMENTO
print('Simulação Sacramento')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS = pd.DataFrame()
#Simula para ECMWF e faz quantis
n = 0
while n <=50:
    PME = dados_peq['pme_'+str(n)].to_numpy()
    QsimsS['Qsac_'+str(n)]=sacsma.simulacao(area, dt, PME, ETP,
                PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
                PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
                PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
                PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
                PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
    n += 1
QsimsS.index = dados_peq.index
QsimsS['Qmed'] = QsimsS.median(axis=1)
QsimsS['Q25'] = QsimsS.quantile(0.25, axis=1)
QsimsS['Q75'] = QsimsS.quantile(0.75, axis=1)
QsimsS['Qmax'] = QsimsS.max(axis=1)
QsimsS['Qmin'] = QsimsS.min(axis=1)
#Simula para WRF
PME = dados_peq['pme_wrf'].to_numpy()
QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
            PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
            PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
            PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
            PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
QsimsS4 = QsimsS.loc[ini_obs:]


# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
    n += 1
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS4.index, y=QsimsS4['Qsac_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo Sacramento')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Ancoragem/anc3_{ano:04d}{mes:02d}{dia:02d}_sac.png')

## 9 - SIMULACAO GR5i
print('Simulação GR5')
PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
QsimsGR = pd.DataFrame()
#Simula para ECMWF e tira quantis
n=0
while n <= 50:
    PME = dados_peq['pme_'+str(n)].to_numpy()
    QsimsGR['Qgr5_'+str(n)]= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                            PAR_GR['x1'], PAR_GR['x2'],
                                            PAR_GR['x3'], PAR_GR['x4'],
                                            PAR_GR['x5'])
    n += 1
QsimsGR.index = dados_peq.index
QsimsGR['Qmed'] = QsimsGR.median(axis=1)
QsimsGR['Q25'] = QsimsGR.quantile(0.25, axis=1)
QsimsGR['Q75'] = QsimsGR.quantile(0.75, axis=1)
QsimsGR['Qmax'] = QsimsGR.max(axis=1)
QsimsGR['Qmin'] = QsimsGR.min(axis=1)
#Simula para WRF
PME = dados_peq['pme_wrf'].to_numpy()
QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                        PAR_GR['x1'], PAR_GR['x2'],
                                        PAR_GR['x3'], PAR_GR['x4'],
                                        PAR_GR['x5'])
QsimsGR4 = QsimsGR.loc[ini_obs:]

# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Qgr5_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
    n += 1
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR4.index, y=QsimsGR4['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo GR5i')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Ancoragem/anc3_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')
