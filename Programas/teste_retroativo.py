import pandas as pd
import sacsma
import gr5i
import datetime as dt
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Leitura
dispara = dt.datetime(2021, 7, 23,  00, tzinfo=dt.timezone.utc)
d_prev = dispara.isoformat()
ini_obs = dispara-dt.timedelta(days=5)
ini_obs = ini_obs.isoformat()
ano = dispara.year
mes = dispara.month
dia = dispara.day
area = 534

dados_obs = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/obs_{ano:04d}{mes:02d}{dia:02d}00.csv',
                        index_col='datahora', parse_dates=True)
obs_fig = dados_obs.loc[ini_obs:]
q_atual_obs = dados_obs.loc[d_prev,'q_m3s']
dados_prev = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/prev_{ano:04d}{mes:02d}{dia:02d}00.csv',
                         index_col='datahora', parse_dates=True)
fim_prev = dados_prev.index[-1]
dados_ecmwf = dados_prev.drop(['pme_wrf', 'etp'], axis=1)
dados_ecmwf['pme_med'] = dados_ecmwf.median(axis=1)
dados_ecmwf['pme_Q25'] = dados_ecmwf.quantile(0.25, axis=1)
dados_ecmwf['pme_Q75'] = dados_ecmwf.quantile(0.75, axis=1)

vazao_obs = pd.read_csv(f'../Dados/vazao_fiu.csv',index_col='datahora', parse_dates=True)
vazao_obs = vazao_obs.resample("6H", closed='right', label = 'right').mean()
vazao_obs = vazao_obs.loc[ini_obs:fim_prev]
chuva_obs = pd.read_csv(f'../Dados/pme_fiu.csv',index_col='datahora', parse_dates=True)
chuva_obs = chuva_obs.resample("6H", closed='right', label = 'right').sum()
chuva_obs = chuva_obs.loc[ini_obs:fim_prev]

#Somatorio chuvas observada e prevista
chuva_obs['chuva_wrf'] = pd.concat([chuva_obs.loc[:d_prev,'chuva_mm'], dados_prev['pme_wrf']])
chuva_obs['chuva_ecmwf_med'] = pd.concat([chuva_obs.loc[:d_prev,'chuva_mm'], dados_ecmwf['pme_med']])
chuva_obs['chuva_ecmwf_Q25'] = pd.concat([chuva_obs.loc[:d_prev,'chuva_mm'], dados_ecmwf['pme_Q25']])
chuva_obs['chuva_ecmwf_Q75'] = pd.concat([chuva_obs.loc[:d_prev,'chuva_mm'], dados_ecmwf['pme_Q75']])
chuva_obs['obs_acum'] = chuva_obs['chuva_mm'].cumsum()
chuva_obs['wrf_acum'] = chuva_obs['chuva_wrf'].cumsum()
chuva_obs['ecmwf_med_acum'] = chuva_obs['chuva_ecmwf_med'].cumsum()
chuva_obs['ecmwf_Q25_acum'] = chuva_obs['chuva_ecmwf_Q25'].cumsum()
chuva_obs['ecmwf_Q75_acum'] = chuva_obs['chuva_ecmwf_Q75'].cumsum()
chuva_acum_atual = chuva_obs.loc[d_prev,'obs_acum']


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
dados_precip = dados_peq.drop(['etp_mm', 'qmon'], axis=1)

###############################################################################
####----- SIMULACAO COM INCLUSAO DE CHUVA E PROPORCIONALIDADE -- ##############
###############################################################################

## 8 - SIMULACAO SACRAMENTO p/ verificar ancoragem
print('Iniciando Sacramento')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS = pd.DataFrame()
#Simula para WRF
PME = dados_precip['pme_wrf'].to_numpy()
QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
            PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
            PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
            PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
            PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
QsimsS.index = dados_precip.index
#Recorta para período de previsao
QsimsS = QsimsS.loc[d_prev:]
#Taxa Proporcao
q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
dif_sac = (q_atual_obs - q_atual_sac)/q_atual_obs #taxa de relacao

#Se simulado for menor que observado, modifica estados iniciais de chuva
#Apos ajustar chuva p/ simulação com diferença < 5%, faz proporcionalidade
#Se simulado for maior que observado, faz apenas proprocionalidade
dados_perturb = dados_precip.copy()
if dif_sac > 0:
    print('Modificando chuva aquecimento - Sacramento')
    inc_0 = 0
    taxa = 1
    while abs(dif_sac) > 0.05:
        incremento = inc_0 + taxa
        print('Tentativa - incremento = ', str(incremento))
        dados_perturb = dados_precip.copy()
        dados_perturb.loc[:dispara] += incremento
        QsimsS = pd.DataFrame()
        #Simula para WRF
        PME = dados_perturb['pme_wrf'].to_numpy()
        QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
                    PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
                    PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
                    PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
                    PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
                    PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
        QsimsS.index = dados_perturb.index
        #Recorta para período de previsao
        QsimsS = QsimsS.loc[d_prev:]
        #Taxa Proporcao
        q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
        dif_sac = (q_atual_obs - q_atual_sac)/q_atual_obs #taxa de relacao
        #Se simulado for maior que observado, reduz taxa de incremento
        #Se simulado for menor que observado, adciona-se a taxa ao incremento base
        if dif_sac < 0:
            taxa = taxa/2
        else:
            inc_0 = incremento
    print('Chuva incremental p/ Sacramento = ', str(incremento), ' mm')

## 8.1 - SIMULACAO SACRAMENTO com proporcionalidade
print('Simulação Sacramento')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS = pd.DataFrame()
#Simula para ECMWF e faz quantis
n = 0
while n <=50:
    PME = dados_perturb['pme_'+str(n)].to_numpy()
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
PME = dados_perturb['pme_wrf'].to_numpy()
QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
            PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
            PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
            PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
            PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
QsimsS = QsimsS.loc[ini_obs:]
q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
QsimsS = QsimsS * q_atual_obs/q_atual_sac



# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_Q25_acum'], name='Chuva Q25 ECMWF Acumulada (mm)', marker_color = 'plum'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_med_acum'], name='Chuva Mediana ECMWF Acumulada (mm)', marker_color = 'lightcoral'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_Q75_acum'], name='Chuva Q75 ECMWF Acumulada (mm)', marker_color = 'plum'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
    n += 1
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo Sacramento')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Ancoragem/teste_{ano:04d}{mes:02d}{dia:02d}_sac.png')
#fig.show()

################################################################################
################################################################################

## 9 - SIMULACAO GR5i p/ verificar ancoragem
print('Iniciando GR5')
PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
QsimsGR = pd.DataFrame()
#Simula para WRF
PME = dados_precip['pme_wrf'].to_numpy()
QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                        PAR_GR['x1'], PAR_GR['x2'],
                                        PAR_GR['x3'], PAR_GR['x4'],
                                        PAR_GR['x5'])
QsimsGR.index = dados_precip.index
#Recorta para período de previsao
QsimsGR = QsimsGR.loc[d_prev:]
#Taxa Proporção
q_atual_gr = QsimsGR.loc[d_prev,'Qgr5_wrf']
dif_gr = (q_atual_obs - q_atual_gr)/q_atual_obs #taxa de relacao

#Se simulado for menor que observado, modifica estados iniciais de chuva
#Apos ajustar chuva p/ simulação com diferença < 5%, faz proporcionalidade
#Se simulado for maior que observado, faz apenas proprocionalidade
dados_perturb = dados_precip.copy()
if dif_gr > 0:
    print('Modificando chuva aquecimento - GR5i')
    inc_0 = 0
    taxa = 1
    while abs(dif_gr) > 0.05:
        incremento = inc_0 + taxa
        print('Tentativa - incremento = ', str(incremento))
        dados_perturb = dados_precip.copy()
        dados_perturb.loc[:dispara] += incremento
        QsimsGR = pd.DataFrame()
        #Simula para WRF
        PME = dados_perturb['pme_wrf'].to_numpy()
        QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                                PAR_GR['x1'], PAR_GR['x2'],
                                                PAR_GR['x3'], PAR_GR['x4'],
                                                PAR_GR['x5'])
        QsimsGR.index = dados_perturb.index
        #Recorta para periodo de previsao
        QsimsGR = QsimsGR.loc[d_prev:]
        #Taxa Proporção
        q_atual_gr = QsimsGR.loc[d_prev,'Qgr5_wrf']
        dif_gr = (q_atual_obs - q_atual_gr)/q_atual_obs #taxa de relacao
        #Se simulado for maior que observado, reduz taxa de incremento
        #Se simulado for menor que observado, adciona-se a taxa ao incremento base
        if q_atual_gr > q_atual_obs:
            taxa = taxa/2
        else:
            inc_0 = incremento
    print('Chuva incremental p/ GR5i = ', str(incremento), ' mm')

## 9.1 - SIMULACAO GR5i com proporcionalidade
print('Simulação GR5')
PAR_GR = pd.read_csv('par_gr5i_fiu.csv', index_col='parNome')['parValor']
QsimsGR = pd.DataFrame()
#Simula para ECMWF e tira quantis
n=0
while n <= 50:
    PME = dados_perturb['pme_'+str(n)].to_numpy()
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
PME = dados_perturb['pme_wrf'].to_numpy()
QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                        PAR_GR['x1'], PAR_GR['x2'],
                                        PAR_GR['x3'], PAR_GR['x4'],
                                        PAR_GR['x5'])
QsimsGR = QsimsGR.loc[ini_obs:]
q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
QsimsGR = QsimsGR * q_atual_obs/q_atual_gr5


# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_Q25_acum'], name='Chuva Q25 ECMWF Acumulada (mm)', marker_color = 'plum'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_med_acum'], name='Chuva Mediana ECMWF Acumulada (mm)', marker_color = 'lightcoral'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['ecmwf_Q75_acum'], name='Chuva Q75 ECMWF Acumulada (mm)', marker_color = 'plum'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)

fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], showlegend=False, marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], showlegend=False, marker_color='blue', fill='tonexty'), row=2, col=1)
n=0
while n <= 50:
    fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qgr5_'+str(n)], showlegend=False, marker_color='darkgray'), row=2, col=1)
    n += 1
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q75'], name="Quantil 75 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qmed'], name="Mediana (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Q25'], name="Quantil 25 (m3/s)", marker_color='blue'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo GR5i')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Ancoragem/teste_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')
