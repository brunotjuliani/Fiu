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

def haversine(lon1, lat1, lon2, lat2):
    rad = math.pi / 180  # degree to radian
    R = 6378.1  # earth average radius at equador (km)
    dlon = (lon2 - lon1) * rad
    dlat = (lat2 - lat1) * rad
    a = (math.sin(dlat / 2)) ** 2 + math.cos(lat1 * rad) * \
        math.cos(lat2 * rad) * (math.sin(dlon / 2)) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c #retorna distancia em km
    return(d)

def coletar_dados(t_ini,t_fim,posto_codigo,sensores):
        # Montagem do texto
    t_ini_string = t_ini.strftime('%Y-%m-%d %H:%M')
    t_fim_string = t_fim.strftime('%Y-%m-%d %H:%M')
    texto_psql = "select hordatahora at time zone 'UTC' as hordatahora, \
                  horleitura, horsensor \
                  from horaria where hordatahora >= '{}' and hordatahora <= '{}' \
                  and horestacao in ({}) \
                  and horsensor in {} \
                  order by horestacao, horsensor, hordatahora; \
                  ".format(t_ini_string, t_fim_string, posto_codigo,sensores)
    # Execução da consulta no banco do Simepar
    conn = psycopg2.connect(dbname='clim', user='hidro', password='hidrologia',
                            host='tornado', port='5432')
    consulta = conn.cursor(cursor_factory = psycopg2.extras.DictCursor)
    consulta.execute(texto_psql)
    consulta_lista = consulta.fetchall()
    df_consulta =pd.DataFrame(consulta_lista,columns=['tempo','valor','sensor'])
    df_consulta.set_index('tempo', inplace=True)
    return df_consulta


################################################################################

## É NECESSARIO VERIFICAR O NOME DO ARQUIVO WRF!!!!!!!!!!!

################################################################################

## 1 - DATAS PADRAO
# Data do disparo
dispara = dt.datetime(2019, 5, 26,  00, tzinfo=dt.timezone.utc)
ano = dispara.year
mes = dispara.month
dia = dispara.day
d_prev = dispara.isoformat()
ini_obs = dispara-dt.timedelta(days=5)
ini_obs = ini_obs.isoformat()

################################################################################
################################################################################

## 2 - LEITURA SERIE HISTORICA DE PRECIPITACAO
print('Leitura historico de precipitacao')
pme_hist = pd.read_csv('../Dados/pme_fiu.csv', index_col='datahora')
pme_hist.index = pd.to_datetime(pme_hist.index, utc=True)
# Agrupa em dt = 6 horas
pme_6h = pme_hist.resample("6H", closed='right', label = 'right').sum()
# Recorta periodo de aquecimento - 2 anos
chuva_recorte = pme_6h.loc[dispara-dt.timedelta(days=730):dispara]

################################################################################
################################################################################

## 3 - COLETA DA PREVISAO DE CHUVA WRF
# Leitura Grade Bacia
area = 534
arquivo_grade = '../Dados/pontos_grade_fiu.csv'
grade = pd.read_csv(arquivo_grade, sep=',')
# Inicia dataframe
dados_peq = pd.DataFrame()

## 3.1 - PREVISAO WRF
print('Coletando previsao WRF')
# Define coordenadas maximas e minimas para coleta (folga adotada p/ ECMWF 20k)
minx5k = min(grade['x']) - 0.05
maxx5k = max(grade['x']) + 0.05
miny5k = min(grade['y']) - 0.05
maxy5k = max(grade['y']) + 0.05
#Inicia df para wrf
df_wrf = pd.DataFrame()
# Loop para range de horizontes (horas a frente de previsao)
horizonte = 1
while horizonte <= 168:
    previsao = dispara + dt.timedelta(hours = (horizonte))
    prev_ano = previsao.year
    prev_mes = previsao.month
    prev_dia = previsao.day
    prev_hora = previsao.hour
    df_wrf.loc[horizonte,'datahora'] = previsao.isoformat()
    #Leitura do arquivo GRIB - 1 horizonte de previsao
    grbfile = f"/simepar/modelos/simepar/wrf/SSE/5km/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/WRFPOS_SSE5km.op05_{ano:04d}-{mes:02d}-{dia:02d}T00:00:00_{prev_ano:04d}-{prev_mes:02d}-{prev_dia:02d}T{prev_hora:02d}:00:00.grib2"
    try:
        grbs = pygrib.open(grbfile)
        pass
    except:
        horizonte +=1
        continue
    # Seleciona precipitacao wrf e le variaveis
    wrf = grbs.select(name = 'Total Precipitation')
    data, lats, lons = wrf[0].data(lat1=miny5k, lat2=maxy5k, lon1=minx5k, lon2=maxx5k)
    data2 = np.hstack(data)
    # Divide dataframe para os pontos estudados
    ponto = 0
    while ponto < len(data2):
        df_wrf.loc[horizonte,ponto] = data2[ponto]
        ponto += 1
    horizonte += 1
# Datetime index
df_wrf['datahora']= pd.to_datetime(df_wrf['datahora'])
df_wrf = df_wrf.set_index('datahora')
# Remove linhas sem previsao
df_wrf = df_wrf.dropna(axis = 0, how = 'all')
# Separa chuva por passo de tempo do acumulado - fillna para lidar com primeira linha
df_wrf_discreto = df_wrf.diff().fillna(df_wrf.iloc[0])
# Acumula para passo de tempo de 6 horas
df_wrf6hrs = df_wrf_discreto.resample("6H", closed='right', label = 'right').sum()

# Inicializa DataFrames de espacialização
print('Espacializando previsao WRF')
DF_postos = df_wrf6hrs
DF_grade = pd.DataFrame()
DF_grade.index.name = 'datahora'
DF_dists = pd.DataFrame()
# Capturar as coordenadas de cada ponto de previsao e comparar com grade da bacia
lats2 = np.hstack(lats)
lons2 = np.hstack(lons)
ponto = 0
while ponto < len(lats2):
    long_p  = lons2[ponto]
    lat_p = lats2[ponto]
    # Calcular a distancia (km) entre os pontos de previsao e grade da bacia
    for pi in grade.index:
        ponto_x = grade.loc[pi].x
        ponto_y = grade.loc[pi].y
        dist = haversine(long_p, lat_p, ponto_x, ponto_y)
        DF_dists.loc[pi,ponto] = dist
    ponto +=1
# Calcular a precipitacao interpolada para cada ponto de grade
L = len(grade)
no_postos = len(DF_postos.columns)
for i,pi in enumerate(grade.index):
    D = np.array([DF_dists.loc[pi,i] for i in DF_postos.columns]) # vetor de distancias
    W = np.array([1/(di**2) for di in D]) # vetor de pesos
    for t in DF_postos.index:
        P_t = DF_postos.loc[t].values # vetor precipitacoes
        W_t = np.array([0 if np.isnan(P_t[i]) else W[i] for i in range(no_postos)])
        prec = np.sum(W_t * np.nan_to_num(P_t))/np.sum(W_t)
        DF_grade.loc[t, pi] = np.around(prec, decimals=2)
# Calcular a espacialização da previsao
PME_wrf = DF_grade.mean(axis=1, skipna=True)
wrf_prev = pd.DataFrame(PME_wrf.rename('chuva_mm').round(2))
wrf_prev.index = wrf_prev.index

# Inclui previsao
chuva_comb = pd.concat([chuva_recorte, wrf_prev])
chuva_comb = chuva_comb[~chuva_comb.index.duplicated(keep='last')]
chuva_comb = chuva_comb.rename(columns={'chuva_mm':'pme'})
# Encerra loop e insere no DF
dados_peq['pme_wrf'] = chuva_comb['pme']

################################################################################
################################################################################

## 4 - ATUALIZA SÉRIE DE VAZÃO OBSERVADA
print('Leitura historico de vazao')
q_hist = pd.read_csv('../Dados/vazao_fiu.csv', index_col='datahora')
q_hist.index = pd.to_datetime(q_hist.index, utc=True)
# Agrupa em dt = 6 horas
q_6h = q_hist.resample("6H", closed='right', label = 'right').mean()
# Combina no df de dados
dados_peq = pd.merge(dados_peq, q_6h, how = 'left',
                 left_index = True, right_index = True)


################################################################################
################################################################################

## 5 - CARREGA DADOS DE EVAPOTRANSPIRAÇÃO PADRÃO P/ BACIA
print('Indexando Evapotranspiração')
etp = pd.read_csv('../Dados/etp_londrina_padrao.csv', sep = ',')
etp.index = (etp['Mes'].map('{:02}'.format) + '-' +
             etp['Dia'].map('{:02}'.format) + '-' +
             etp['Hora'].map('{:02}'.format))
# Cria DFs padrao horario para ser preenchido com ETP horarios
t_ini = dados_peq.index[0].round('1d')
t_fim = dados_peq.index[-1]
date_rng_horario = pd.date_range(start=t_ini, end=t_fim, freq='H', tz = "UTC")
etp_hor = pd.DataFrame(date_rng_horario, columns=['date'])
etp_hor.index = etp_hor['date']
etp_hor['datahora'] = etp_hor.index.strftime('%m-%d-%H')
etp_hor['etp'] = etp_hor['datahora'].map(etp['etp'])
etp_hor = etp_hor.drop(['date', 'datahora'], axis=1)
etp = etp_hor.resample("6H", closed='right', label = 'right').sum()
# Combina no df de dados
dados_peq = pd.merge(dados_peq, etp, how = 'left',
                 left_index = True, right_index = True)


################################################################################
################################################################################

## 6 - EXPORTA DADOS DE CADA RODADA

#Cria pasta para exportar resultados de simulacao
Path(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00').mkdir(parents=True,exist_ok=True)

# 6.1 - EXPORTA DADOS OBSERVADOS
dados_obs = dados_peq[['pme_wrf', 'etp', 'qjus']]
dados_obs.columns = ['chuva_mm', 'etp_mm', 'q_m3s']
dados_obs = dados_obs.loc[:dispara]
dados_obs.to_csv(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/obs_{ano:04d}{mes:02d}{dia:02d}00.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')
obs_fig = dados_obs.loc[ini_obs:]
#registra vazao atual p/ ancoragem
q_atual_obs = dados_obs.loc[dispara,'q_m3s']

# 6.1 - EXPORTA DADOS DE PREVISAO
dados_prev = dados_peq.loc[dispara:]
dados_prev = dados_prev.iloc[1:]
dados_prev = dados_prev.drop(['qjus'], axis=1)
dados_prev.to_csv(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/prev_{ano:04d}{mes:02d}{dia:02d}00.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')
fim_prev = dados_prev.index[-1]


################################################################################
################################################################################

## 7 - AVALIACAO DA SIMULACAO

# Valores observados
vazao_obs = q_6h.loc[ini_obs:fim_prev]
chuva_obs = pme_6h.loc[ini_obs:fim_prev]

# Chuva acumulada observada e prevista
chuva_obs['chuva_wrf'] = pd.concat([chuva_obs.loc[:d_prev,'chuva_mm'], dados_prev['pme_wrf']])
chuva_obs['obs_acum'] = chuva_obs['chuva_mm'].cumsum()
chuva_obs['wrf_acum'] = chuva_obs['chuva_wrf'].cumsum()
chuva_acum_atual = chuva_obs.loc[d_prev,'obs_acum']

# Forcantes
ETP = dados_peq['etp'].to_numpy()
dados_peq['qmon'] = 0
Qmon = dados_peq['qmon'].to_numpy()
dados_precip = dados_peq.drop(['etp', 'qmon'], axis=1)


###############################################################################
####----- SIMULACAO COM INCLUSAO DE CHUVA E PROPORCIONALIDADE -- ##############
###############################################################################

## 8 - SIMULACAO SACRAMENTO p/ verificar ancoragem
print('Iniciando Sacramento')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S = pd.read_csv('par_sacsma_fiu_antigo.csv', index_col='parNome')['parValor']
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
#Simulacao sem Ancoragem
QsimsS_B = QsimsS.copy().loc[ini_obs:]
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
    incremento = inc_0
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
PAR_S = pd.read_csv('par_sacsma_fiu_antigo.csv', index_col='parNome')['parValor']
QsimsS = pd.DataFrame()
#Simula para WRF
PME = dados_perturb['pme_wrf'].to_numpy()
QsimsS['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S['parUZTWM'], PAR_S['parUZFWM'], PAR_S['parLZTWM'],
            PAR_S['parLZFPM'], PAR_S['parLZFSM'], PAR_S['parADIMP'],
            PAR_S['parPCTIM'], PAR_S['parPFREE'], PAR_S['parUZK'],
            PAR_S['parLZPK'], PAR_S['parLZSK'], PAR_S['parZPERC'],
            PAR_S['parREXP'], PAR_S['parK_HU'], PAR_S['parN_HU'])
QsimsS.index = dados_peq.index
QsimsS = QsimsS.loc[ini_obs:]
q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
QsimsS = QsimsS * q_atual_obs/q_atual_sac

# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsS_B.index, y=QsimsS_B['Qsac_wrf'], name="Simulação Bruta (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS.index, y=QsimsS['Qsac_wrf'], name="Simulação Ancorada (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo Sacramento - Em operação')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/teste_{ano:04d}{mes:02d}{dia:02d}_sac.png')
#fig.show()

################################################################################
################################################################################

## 8.1 - SIMULACAO SACRAMENTO com nova calibracao
print('Iniciando Sacramento - Nova Calibracao')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S_2 = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS_2 = pd.DataFrame()
#Simula para WRF
PME = dados_precip['pme_wrf'].to_numpy()
QsimsS_2['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S_2['parUZTWM'], PAR_S_2['parUZFWM'], PAR_S_2['parLZTWM'],
            PAR_S_2['parLZFPM'], PAR_S_2['parLZFSM'], PAR_S_2['parADIMP'],
            PAR_S_2['parPCTIM'], PAR_S_2['parPFREE'], PAR_S_2['parUZK'],
            PAR_S_2['parLZPK'], PAR_S_2['parLZSK'], PAR_S_2['parZPERC'],
            PAR_S_2['parREXP'], PAR_S_2['parK_HU'], PAR_S_2['parN_HU'])
QsimsS_2.index = dados_precip.index
#Simulacao sem Ancoragem
QsimsS_B_2 = QsimsS_2.copy().loc[ini_obs:]
#Recorta para período de previsao
QsimsS_2 = QsimsS_2.loc[d_prev:]
#Taxa Proporcao
q_atual_sac_2 = QsimsS_2.loc[d_prev,'Qsac_wrf']
dif_sac_2 = (q_atual_obs - q_atual_sac_2)/q_atual_obs #taxa de relacao

#Se simulado for menor que observado, modifica estados iniciais de chuva
#Apos ajustar chuva p/ simulação com diferença < 5%, faz proporcionalidade
#Se simulado for maior que observado, faz apenas proprocionalidade
dados_perturb_2 = dados_precip.copy()
if dif_sac_2 > 0:
    print('Modificando chuva aquecimento - Sacramento')
    inc_0 = 0
    taxa = 1
    incremento = inc_0
    while abs(dif_sac_2) > 0.05:
        incremento = inc_0 + taxa
        print('Tentativa - incremento = ', str(incremento))
        dados_perturb_2 = dados_precip.copy()
        dados_perturb_2.loc[:dispara] += incremento
        QsimsS_2 = pd.DataFrame()
        #Simula para WRF
        PME = dados_perturb_2['pme_wrf'].to_numpy()
        QsimsS_2['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
                    PAR_S_2['parUZTWM'], PAR_S_2['parUZFWM'], PAR_S_2['parLZTWM'],
                    PAR_S_2['parLZFPM'], PAR_S_2['parLZFSM'], PAR_S_2['parADIMP'],
                    PAR_S_2['parPCTIM'], PAR_S_2['parPFREE'], PAR_S_2['parUZK'],
                    PAR_S_2['parLZPK'], PAR_S_2['parLZSK'], PAR_S_2['parZPERC'],
                    PAR_S_2['parREXP'], PAR_S_2['parK_HU'], PAR_S_2['parN_HU'])
        QsimsS_2.index = dados_perturb_2.index
        #Recorta para período de previsao
        QsimsS_2 = QsimsS_2.loc[d_prev:]
        #Taxa Proporcao
        q_atual_sac_2 = QsimsS_2.loc[d_prev,'Qsac_wrf']
        dif_sac_2 = (q_atual_obs - q_atual_sac_2)/q_atual_obs #taxa de relacao
        #Se simulado for maior que observado, reduz taxa de incremento
        #Se simulado for menor que observado, adciona-se a taxa ao incremento base
        if dif_sac_2 < 0:
            taxa = taxa/2
        else:
            inc_0 = incremento
    print('Chuva incremental p/ Sacramento = ', str(incremento), ' mm')

## 8.1 - SIMULACAO SACRAMENTO com proporcionalidade
print('Simulação Sacramento - Nova Calibracao')
dt = 0.25
fconv = area/(dt*86.4) # mm -> m3/s
PAR_S_2 = pd.read_csv('par_sacsma_fiu.csv', index_col='parNome')['parValor']
QsimsS_2 = pd.DataFrame()
#Simula para WRF
PME = dados_perturb_2['pme_wrf'].to_numpy()
QsimsS_2['Qsac_wrf']=sacsma.simulacao(area, dt, PME, ETP,
            PAR_S_2['parUZTWM'], PAR_S_2['parUZFWM'], PAR_S_2['parLZTWM'],
            PAR_S_2['parLZFPM'], PAR_S_2['parLZFSM'], PAR_S_2['parADIMP'],
            PAR_S_2['parPCTIM'], PAR_S_2['parPFREE'], PAR_S_2['parUZK'],
            PAR_S_2['parLZPK'], PAR_S_2['parLZSK'], PAR_S_2['parZPERC'],
            PAR_S_2['parREXP'], PAR_S_2['parK_HU'], PAR_S_2['parN_HU'])
QsimsS_2.index = dados_peq.index
QsimsS_2 = QsimsS_2.loc[ini_obs:]
q_atual_sac_2 = QsimsS_2.loc[d_prev,'Qsac_wrf']
QsimsS_2 = QsimsS_2 * q_atual_obs/q_atual_sac_2

# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsS_B_2.index, y=QsimsS_B_2['Qsac_wrf'], name="Sim. Bruta (Nova Calib.) (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsS_2.index, y=QsimsS_2['Qsac_wrf'], name="Sim. Ancorada (Nova Calib.) (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo Sacramento - Nova Calibração')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/teste_{ano:04d}{mes:02d}{dia:02d}_sac_novo.png')
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
#Simulacao sem Ancoragem
QsimsGR_B = QsimsGR.copy().loc[ini_obs:]
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
    incremento = inc_0
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
#Simula para WRF
PME = dados_perturb['pme_wrf'].to_numpy()
QsimsGR['Qgr5_wrf']= gr5i.simulacao(PAR_GR['dt'], area, PME, ETP, Qmon,
                                        PAR_GR['x1'], PAR_GR['x2'],
                                        PAR_GR['x3'], PAR_GR['x4'],
                                        PAR_GR['x5'])
QsimsGR.index = dados_peq.index
QsimsGR = QsimsGR.loc[ini_obs:]
q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
QsimsGR = QsimsGR * q_atual_obs/q_atual_gr5


# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['wrf_acum'], name='Chuva Prevista WRF Acumulada (mm)', marker_color = 'lightgreen'), row=1, col=1)
fig.add_trace(go.Scatter(x=chuva_obs.index, y=chuva_obs['obs_acum'], name="Chuva Acumulada Registrada (mm)", marker_color='gray'), row=1, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[chuva_acum_atual], marker=dict(color="gold", size=10), showlegend=False), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
fig.layout['bargap']=0
fig.add_trace(go.Scatter(x=QsimsGR_B.index, y=QsimsGR_B['Qgr5_wrf'], name="Simulação Bruta (m3/s)", marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=QsimsGR.index, y=QsimsGR['Qgr5_wrf'], name="Simulação WRF (m3/s)", marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=vazao_obs.index, y=vazao_obs['qjus'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=[d_prev], y=[q_atual_obs], marker=dict(color="gold", size=10), name='Disparo Previsão'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo GR5i')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
fig.write_image(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/teste_{ano:04d}{mes:02d}{dia:02d}_gr5i.png')


################################################################################
################################################################################

## 10 - EXPORTA DATAFRAME COM RESULTADOS
chuva_obs['qsac_bru'] = QsimsS_B['Qsac_wrf']
chuva_obs['qsac_anc'] = QsimsS['Qsac_wrf']
chuva_obs['qsac_bru_novo'] = QsimsS_B_2['Qsac_wrf']
chuva_obs['qsac_anc_novo'] = QsimsS_2['Qsac_wrf']
chuva_obs['qgr5_bru'] = QsimsGR_B['Qgr5_wrf']
chuva_obs['qgr5_anc'] = QsimsGR['Qgr5_wrf']
chuva_obs.to_csv(f'../Simulacoes/Retroativo_WRF/{ano:04d}_{mes:02d}_{dia:02d}_00/aval_{ano:04d}{mes:02d}{dia:02d}00.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')
