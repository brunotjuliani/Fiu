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
################################################################################

## 1 - DATAS PADRAO
#Data Ultima Rodada
att_anterior = open('../Dados/disparo.txt')
data0 = att_anterior.readline().strip()
att_anterior.close()
#Data Rodada Atual
hoje = dt.date.today()
dispara = dt.datetime(hoje.year, hoje.month, hoje.day,  00, tzinfo=dt.timezone.utc)
ano = dispara.year
mes = dispara.month
dia = dispara.day
d_prev = dispara.isoformat()
#Atualiza arquivo com data da rodada atual
arq_disparo = open("../Dados/disparo.txt", "w")
arq_disparo.write(d_prev)
arq_disparo.close()
#Gera lista de datas a atualizar - closed right para nao incluir data da ultima atualizacao
lista_att = pd.date_range(start=data0,end=d_prev,freq='d', closed = 'right').to_series()

################################################################################
################################################################################

## 2 - ATUALIZA SÉRIE DE CHUVA OBSERVADA PARA BACIA
print('Atualizando dados históricos observados - Precipitação')
#Se serie já atualizada no mesmo dia, passa.
if data0 == d_prev:
    pass
else:
    ## 2.1 - ATUALIZA SÉRIE DE CADA POSTO
    # Lista postos de precipitacao com as seguintes informacoes
    # Nome : [codigo simepar, codigo ANA, latitude, longitute, altitude]
    postos_precip = {
        'Apucaraninha_Montante':['23735103', '2351079', '-23.73056', '-51.03778', '688'],
        'Barragem_PCH_Apucaraninha':['23745090', '2350015', '-23.75001', '-50.90772', '611'],
        'Reservatorio_Fiu':['23745094', '2350016', '-23.74906', '-50.94049', '430']
        }
    # Data para atualizar
    t_ini = pd.Timestamp(data0) - dt.timedelta(days = 5)
    t_fim = dispara

    ############################################################################
    ## ATUALIZACAO PARA ESPACIALIZACAO POR ESTACOES
    #leitura grade da bacia
    arquivo_grade = '../Dados/pontos_grade_fiu.csv'
    grade = pd.read_csv(arquivo_grade, sep=',')
    #Inicializa dfs de espacializacao
    df_postos_pme = pd.DataFrame()
    df_grade_pme = pd.DataFrame()
    df_grade_pme.index.name = 'datahora'
    df_dists_pme = pd.DataFrame()
    ############################################################################

    #Realiza coleta
    # Atualiza serie de cada posto
    for posto_nome, posto_informacoes in postos_precip.items():
        print('Atualizando ', posto_nome)
        posto_codigo = posto_informacoes[0]
        posto_ana = posto_informacoes[1]
        posto_lat = float(posto_informacoes[2])
        posto_long = float(posto_informacoes[3])
        posto_alt = float(posto_informacoes[4])

        #Coleta dados 15 min
        dados = coletar_dados(t_ini,t_fim, posto_codigo, '(7)')
        dados.columns = ['chuva_mm', 'sensor']
        dados = dados.drop('sensor', 1)
        dados.index = pd.to_datetime(dados.index, utc=True).rename('datahora')
        dados["chuva_mm"] = pd.to_numeric(dados["chuva_mm"], downcast = "float")
        #Trata serie 15 min
        dados['flag'] = np.where(dados['chuva_mm'].isnull(), 1, 0)
        #Cria DFs padrão de data, para serem preenchidas com os dados baixados
        t_ini_15min = dados.index[0]
        t_fim_15min = dados.index[-1]
        date_rng_15min = pd.date_range(start=t_ini_15min, end=t_fim_15min,
                                       freq='15min',tz="UTC")
        table_15min = pd.DataFrame(date_rng_15min, columns=['datahora'])
        table_15min['datahora']= pd.to_datetime(table_15min['datahora'])
        table_15min = table_15min.set_index('datahora')
        df_15min = pd.merge(table_15min, dados, how='left',
                            left_index=True, right_index=True)
        df_15min = df_15min[~df_15min.index.duplicated(keep='first')]
        #Data sem registro na serie
        df_15min['flag'] = np.where(df_15min['flag'].isnull(), 2, df_15min['flag'])
        #Valores negativos e acumulados de 15min superiores a 45mm
        df_15min['flag'] = np.where((df_15min['chuva_mm'] < 0), 3, df_15min['flag'])
        df_15min['chuva_mm'] = np.where((df_15min['chuva_mm'] < 0
                                         ), np.nan, df_15min['chuva_mm'])
        df_15min['flag'] = np.where((df_15min['chuva_mm'] >45), 3, df_15min['flag'])
        df_15min['chuva_mm'] = np.where((df_15min['chuva_mm'] > 45
                                         ), np.nan, df_15min['chuva_mm'])
        #Persistencia de valores não nulos
        # H <= 2MM <- 6 HORAS = 24 REGISTROS
        # H > 2MM <- 1 HORA = 4 REGISTROS
        dados2 = df_15min.groupby((df_15min['chuva_mm'].
                                   shift()!=df_15min['chuva_mm']).cumsum()
                                  ).filter(lambda x: len(x) >= 24)
        dados2 = dados2[dados2['chuva_mm']>0]
        dados2 = dados2[dados2['chuva_mm']<=2]
        dados3 = df_15min.groupby((df_15min['chuva_mm'].
                                   shift()!=df_15min['chuva_mm']).cumsum()
                                  ).filter(lambda x: len(x) >= 4)
        dados3 = dados3[dados3['chuva_mm']>0]
        dados3 = dados3[dados3['chuva_mm']>2]
        df_15min['flag'] = np.where(df_15min.index.isin(dados2.index),
                                    4, df_15min['flag'])
        df_15min['flag'] = np.where(df_15min.index.isin(dados3.index),
                                    4, df_15min['flag'])
        df_15min['chuva_mm'] = np.where(df_15min.index.isin(dados2.index),
                                    np.nan, df_15min['chuva_mm'])
        df_15min['chuva_mm'] = np.where(df_15min.index.isin(dados3.index),
                                    np.nan, df_15min['chuva_mm'])
        df_15min.drop(['flag'], axis=1, inplace = True)
        #Transforma em serie horaria
        t_ini_h = df_15min.index[0].round('1h')
        t_fim_h = df_15min.index[-1]
        date_rng_horario =pd.date_range(start=t_ini_h,end=t_fim_h,freq='H',tz="UTC")
        table_hor = pd.DataFrame(date_rng_horario, columns=['date'])
        table_hor['datahora']= pd.to_datetime(table_hor['date'])
        table_hor = table_hor.set_index('datahora')
        table_hor.drop(['date'], axis=1, inplace = True)
        # agrupa em dados horarios, com intervalo fechado à direita (acumulado/media da 0:01 a 1:00);
        df_15min['count'] = np.where(df_15min['chuva_mm'].notnull(), 1, 0)
        df_horario = (df_15min.resample("H", closed='right', label='right').
                      agg({'count' : np.sum, 'chuva_mm' : np.sum}))
        #Remove valores horarios superiores a 90mm
        df_horario['chuva_mm'] = np.where((df_horario['chuva_mm'] > 90
                                             ), np.nan, df_horario['chuva_mm'])
        #remove colunas 'count' dos dataframes e agrupa com data padrao
        df_horario.drop('count', axis=1, inplace=True)
        table_hor = pd.merge(table_hor, df_horario, left_index = True,
                             right_index = True, how = 'left')
        table_hor = table_hor[~table_hor.index.duplicated(keep='first')]
        table_hor = table_hor[['chuva_mm']]
        #remove primeira linha do dataframe (hora incompleta)
        table_hor = table_hor[1:]

        ########################################################################
        ## ATUALIZACAO PARA ESPACIALIZACAO PELAS ESTACOES
        #Concatena serie do posto em DF_postos
        sr_posto_pme = table_hor['chuva_mm']
        sr_posto_pme = sr_posto_pme.rename(posto_nome)
        df_postos_pme = df_postos_pme.join(sr_posto_pme, how='outer')

        #Calcula a distancia (km) entre o posto e todos os pontos da grade
        for pi in grade.index:
            ponto_x = grade.loc[pi].x
            ponto_y = grade.loc[pi].y
            dist = haversine(posto_long, posto_lat, ponto_x, ponto_y)
            df_dists_pme.loc[pi,posto_nome] = dist
        ########################################################################


        #le serie historica antiga
        sr_antiga = pd.read_csv('../Dados/Postos_Plu/'+posto_nome+'.csv', skiprows=3,
                                parse_dates=True, index_col='datahora')
        #atualiza serie da estacao
        serie_att = pd.concat([sr_antiga, table_hor])
        serie_att = serie_att[~serie_att.index.duplicated(keep='last')]
        #exporta serie atualizada
        with open('../Dados/Postos_Plu/'+posto_nome+'.csv','w',newline='') as file:
            writer = csv.writer(file)
            writer.writerow([posto_ana])
            writer.writerow([posto_nome])
            writer.writerow([posto_long, posto_lat, posto_alt])
        serie_att.to_csv('../Dados/Postos_Plu/'+posto_nome+'.csv', mode = 'a', sep = ",",
                         date_format='%Y-%m-%dT%H:%M:%S+00:00', float_format='%.2f')
        #converte para diario e exporta serie diaria (serie diária indexada a esquerda)
        serie_diaria = serie_att.resample("D", closed='right', label = 'left').sum()
        #remove primeira linha do dataframe (dia incompleto)
        serie_diaria = serie_diaria[1:]
        serie_diaria.to_csv('../Dados/Postos_Plu/diario_'+posto_nome+'.csv', sep = ",",
                            date_format='%Y-%m-%d', float_format='%.2f', index_label='data')

    ############################################################################
    ## ATUALIZACAO PARA ESPACIALIZACAO PELAS ESTACOES
    ## Realiza espacialização pelas estações e armazena caso nao tenha dados SIPREC
    L = len(grade)
    no_postos = len(df_postos_pme.columns)
    for i,pi in enumerate(grade.index):
        D = np.array([df_dists_pme.loc[pi,i] for i in df_postos_pme.columns]) # vetor de distancias
        W = np.array([1/(di**2) for di in D]) # vetor de pesos
        for t in df_postos_pme.index:
            P_t = df_postos_pme.loc[t].values # vetor precipitacoes
            W_t = np.array([0 if np.isnan(P_t[i]) else W[i] for i in range(no_postos)])
            prec = np.sum(W_t * np.nan_to_num(P_t))/np.sum(W_t)
            df_grade_pme.loc[t, pi] = np.around(prec, decimals=2)
    PME = df_grade_pme.mean(axis=1, skipna=True)
    pme_att = pd.DataFrame(PME.rename('chuva_mm').round(2))
    ## Atualização da série histórica por espacializacao
    pme_hist_esp = pd.read_csv('../Dados/pme_fiu.csv', index_col='datahora')
    pme_hist_esp.index = pd.to_datetime(pme_hist_esp.index, utc=True)
    pme_final = pd.concat([pme_hist_esp, pme_att])
    pme_hist_esp = pme_final[~pme_final.index.duplicated(keep='last')]
    ############################################################################

################################################################################
################################################################################

## 2.2 - ATUALIZA SERIE ESPACIALIZADA PELO SIPREC
# Le Historico de chuva
pme_hist = pd.read_csv('../Dados/pme_fiu.csv', index_col='datahora')
pme_hist.index = pd.to_datetime(pme_hist.index, utc=True)

################################################################################
#Se serie já atualizada no mesmo dia, apenas lê variável.
if data0 == d_prev:
    pass
else:
    #tenta ler arquivos do siprec. Se falhar, espacializa com dados das estacoes
    try:
        pme_hist_sip = pd.read_csv('../Dados/pme_fiu.csv', index_col='datahora')
        pme_hist_sip.index = pd.to_datetime(pme_hist_sip.index, utc=True)
        #Loop para dias a atualizar
        for d in lista_att:
            ano_att = lista_att[d].year
            mes_att = lista_att[d].month
            dia_att = lista_att[d].day
            # Le arquivo SIPREC+ (CONFIRMAR SE ESTA EM UTC OU BRT)
            siprec = pd.read_csv(f'~/infohidro/hidrologia_operacional/estimativas_chuva/fiu/siprec_mais_fiu_{ano_att:04d}{mes_att:02d}{dia_att:02d}00.csv', index_col = 0, header=None).T
            siprec.index = pd.to_datetime(siprec['FID'], format='%Y%m%d%H%M', utc=True).rename('datahora')
            siprec = siprec.drop('FID',1)
            siprec.columns = ['chuva_mm']
            # Atualiza serie historica com arquivos do SIPREC
            pme_att = pd.concat([pme_hist_sip, siprec])
            pme_att = pme_att[~pme_att.index.duplicated(keep='last')]
            pme_hist_sip = pme_att
        # Exporta serie historica Atualizada
        print('Atualizando chuva espacializada - Siprec+')
        pme_hist_sip.to_csv('../Dados/pme_fiu.csv', index_label='datahora',
                        float_format='%.2f', date_format='%Y-%m-%dT%H:%M:%S+00:00')
        pme_hist = pme_hist_sip
    except:
        print('Dados do Siprec+ não encontrados')
        print('Atualizando chuva espacializada com dados das estacoes')
        pme_hist_esp.to_csv('../Dados/pme_fiu.csv', index_label='datahora',
                        float_format='%.2f', date_format='%Y-%m-%dT%H:%M:%S+00:00')
        pme_hist = pme_hist_esp
################################################################################

#converte para diario e exporta serie diaria (serie diária indexada a esquerda)
pme_diaria = pme_hist.resample("D", closed='right', label = 'left').sum()
#remove primeira linha do dataframe (dia incompleto)
pme_diaria = pme_diaria[1:]
pme_diaria.to_csv('../Dados/diario_pme_fiu.csv', sep = ",",
                    date_format='%Y-%m-%d', float_format='%.2f', index_label='data')
# Agrupa em dt = 6 horas
pme_6h = pme_hist.resample("6H", closed='right', label = 'right').sum()
# Recorta periodo de aquecimento - 2 anos
chuva_recorte = pme_6h.loc[dispara-dt.timedelta(days=730):dispara]


################################################################################
################################################################################

## 3 - COLETA DA PREVISAO DE CHUVA WRF E ECMWF
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
    grbfile = f"/simepar/modelos/simepar/wrf/SSE/5km/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/WRFPOS_DASSE5km.op05_{ano:04d}-{mes:02d}-{dia:02d}T00:00:00_{prev_ano:04d}-{prev_mes:02d}-{prev_dia:02d}T{prev_hora:02d}:00:00.grib2"
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


## 3.1 - PREVISAO ECMWF
print('Coletando ensemble ECMWF')
# Define coordenadas maximas e minimas para coleta (folga adotada p/ ECMWF 20k)
minx20k = min(grade['x']) +360 - 0.2
maxx20k = max(grade['x']) +360 + 0.2
miny20k = min(grade['y']) - 0.2
maxy20k = max(grade['y']) + 0.2
ens_n = 0
while ens_n <= 50:
    print('Iniciando membro ECMWF ', ens_n+1)
    # Inicia dataframe p/ diferentes membros
    df_previsao = pd.DataFrame()

    # Loop para range de horizontes (horas a frente de previsao)
    horizonte = 1
    while horizonte <= 168:
        previsao = dispara + dt.timedelta(hours = (horizonte))
        prev_mes = previsao.month
        prev_dia = previsao.day
        prev_hora = previsao.hour
        df_previsao.loc[horizonte,'datahora'] = previsao.isoformat()

        ## LEITURA DO ARQUIVO GRIB - 1 HORIZONTE DE PREVISÃO - ENSEMBLE COM N DADOS
        ## Atualização do endereço do arquivo - 30/03
        grbfile = f"/simepar/modelos/ecmwf/ens/SSE/0p2/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/D1E{mes:02d}{dia:02d}0000{prev_mes:02d}{prev_dia:02d}{prev_hora:02d}001.grib2"
        try:
            grbs = pygrib.open(grbfile)
        except:
            grbfile = f"/simepar/modelos/ecmwf/ens/SSE/0p2/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/D1X{mes:02d}{dia:02d}0000{prev_mes:02d}{prev_dia:02d}{prev_hora:02d}001.grib2"
            try:
                grbs = pygrib.open(grbfile)
                pass
            except:
                horizonte +=1
                continue

        # Seleciona membro do ensemble e le variaveis
        membro = grbs.select(perturbationNumber=ens_n)
        data, lats, lons = membro[0].data(lat1=miny20k, lat2=maxy20k, lon1=minx20k, lon2=maxx20k)
        data2 = np.hstack(data)

        # Divide dataframe para os pontos estudados
        ponto = 0
        while ponto < len(data2):
            df_previsao.loc[horizonte,ponto] = data2[ponto]
            ponto += 1
        horizonte += 1

    # Datetime index
    df_previsao['datahora']= pd.to_datetime(df_previsao['datahora'])
    df_previsao = df_previsao.set_index('datahora')
    # Remove linhas sem previsao
    df_previsao = df_previsao.dropna(axis = 0, how = 'all')
    # Separa chuva por passo de tempo do acumulado - fillna para lidar com primeira linha
    df_discreto = df_previsao.diff().fillna(df_previsao.iloc[0])
    # Acumula para passo de tempo de 6 horas
    df_6hrs = df_discreto.resample("6H", closed='right', label = 'right').sum()

    # Inicializa DataFrames de espacialização
    DF_postos = df_6hrs
    DF_grade = pd.DataFrame()
    DF_grade.index.name = 'datahora'
    DF_dists = pd.DataFrame()

    # Capturar as coordenadas de cada ponto de previsao e comparar com grade da bacia
    lats2 = np.hstack(lats)
    lons2 = np.hstack(lons)
    ponto = 0
    while ponto < len(lats2):
        long_p  = lons2[ponto] - 360 #para deixar no mesmo formato da grade base
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
    PME = DF_grade.mean(axis=1, skipna=True)
    pme_prev = pd.DataFrame(PME.rename('chuva_mm').round(2))
    pme_prev.index = pme_prev.index

    # Inclui previsao
    chuva_comb = pd.concat([chuva_recorte, pme_prev])
    chuva_comb = chuva_comb[~chuva_comb.index.duplicated(keep='last')]
    chuva_comb = chuva_comb.rename(columns={'chuva_mm':'pme'})

    # Encerra loop e insere no DF
    dados_peq['pme_'+str(ens_n)] = chuva_comb['pme']
    ens_n += 1


################################################################################
################################################################################

## 4 - ATUALIZA SÉRIE DE VAZÃO OBSERVADA
print('Atualizando dados históricos observados - Vazão')
q_hist = pd.read_csv('../Dados/vazao_fiu.csv', index_col='datahora')
q_hist.index = pd.to_datetime(q_hist.index, utc=True)
#Se serie já atualizada no mesmo dia, apenas lê variável.
if data0 == q_hist.index[-1]:
    pass
else:
    # Coleta dados atualizados por API - atualiza 7 dias previos para possiveis nans recuperados
    # Ponto relativo a Fiu no banco = 57
    ponto = 57
    datahoraf = dispara
    datahorai = datahoraf - dt.timedelta(days=7)
    url = "http://produtos.simepar.br/telemetry-copel/monhid?datahorai={:%Y-%m-%dT%H:%M:%S}&datahoraf={:%Y-%m-%dT%H:%M:%S}&ids={}&tipos=R".format(datahorai, datahoraf, ponto)
    response = requests.get(url=url)
    data = response.json()
    df = pd.DataFrame.from_dict(data)
    df = df.set_index(pd.to_datetime(df.datahora, utc=True))
    df2 = pd.DataFrame()
    for row in df.itertuples():
        try:
            df2.loc[row[0],'qjus'] = row[3]['vazaoAfluente']
        except:
            df2.loc[row[0],'qjus'] = np.nan
    df2[df2['qjus'] < 0] = np.nan
    df2 = df2.sort_index()
    # Atualiza serie historica com dados da API
    q_att = pd.concat([q_hist, df2])
    q_att = q_att[~q_att.index.duplicated(keep='last')]
    q_hist = q_att
    # Exporta serie historica Atualizada
    q_hist.to_csv('../Dados/vazao_fiu.csv', index_label='datahora',
                 float_format='%.2f', date_format='%Y-%m-%dT%H:%M:%S+00:00')
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
Path(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00').mkdir(parents=True,exist_ok=True)

# 6.1 - EXPORTA DADOS OBSERVADOS
dados_obs = dados_peq[['pme_wrf', 'etp', 'qjus']]
dados_obs.columns = ['chuva_mm', 'etp_mm', 'q_m3s']
dados_obs = dados_obs.loc[:dispara]
dados_obs.to_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/obs_{ano:04d}{mes:02d}{dia:02d}00.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')
#registra vazao atual p/ ancoragem
q_atual_obs = dados_obs.loc[dispara,'q_m3s']

# 6.1 - EXPORTA DADOS DE PREVISAO
dados_prev = dados_peq.loc[dispara:]
dados_prev = dados_prev.iloc[1:]
dados_prev = dados_prev.drop(['qjus'], axis=1)
dados_prev.to_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/prev_{ano:04d}{mes:02d}{dia:02d}00.csv',
                 index_label='datahora', float_format='%.3f',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00')


################################################################################
################################################################################

## 7 - FORÇANTES MODELAGEM

# Leitura
ETP = dados_peq['etp'].to_numpy()
Qjus = dados_peq['qjus'].to_numpy()
dados_peq['qmon'] = 0
Qmon = dados_peq['qmon'].to_numpy()
dados_precip = dados_peq.drop(['etp', 'qjus', 'qmon'], axis=1)


#Observado para figuras
ini_obs = dispara-dt.timedelta(days=5)
ini_obs = ini_obs.isoformat()
obs_fig = dados_obs.loc[ini_obs:]

################################################################################
################################################################################

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
    print('Chuva incremental p/ Sacramento = ', incremento, ' mm')

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
QsimsS = QsimsS.loc[d_prev:]
q_atual_sac = QsimsS.loc[d_prev,'Qsac_wrf']
QsimsS = QsimsS * q_atual_obs/q_atual_sac

#Exporta série ancorada
QsimsS.to_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/sim_sac_mod_{ano:04d}{mes:02d}{dia:02d}00.csv',
              index_label='datahora', float_format='%.3f',
              date_format='%Y-%m-%dT%H:%M:%S+00:00')

# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
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
fig.add_trace(go.Scatter(x=obs_fig.index, y=obs_fig['q_m3s'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo Sacramento')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
try:
    fig.write_image(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_sac_mod_{ano:04d}{mes:02d}{dia:02d}00.png')
except Exception as e:
    print('Falha ao salvar a figura de simulacao Sacramento em .png')
    print(e)
    print('Será exportado figura em HTML. Deve ser exportada com configuracoes .png, mantendo o nome.')
    fig.write_html(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_sac_mod_{ano:04d}{mes:02d}{dia:02d}00.html')
    fig.show()

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
        if dif_gr < 0:
            taxa = taxa/2
        else:
            inc_0 = incremento
    print('Chuva incremental p/ GR5i = ', incremento, ' mm')

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
QsimsGR = QsimsGR.loc[d_prev:]
q_atual_gr5 = QsimsGR.loc[d_prev,'Qgr5_wrf']
QsimsGR = QsimsGR * q_atual_obs/q_atual_gr5

#Exporta série ancorada
QsimsGR.to_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/sim_gr5_mod_{ano:04d}{mes:02d}{dia:02d}00.csv',
              index_label='datahora', float_format='%.3f',
              date_format='%Y-%m-%dT%H:%M:%S+00:00')

# Plotagem
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Bar(x=obs_fig.index, y=obs_fig['chuva_mm'], name="PME (mm)", marker=dict(color='black',line=dict(color='black', width=3))), row=1, col=1)
fig.add_trace(go.Bar(x=dados_prev.index, y=dados_prev['pme_wrf'], name="Previsão WRF (mm)", marker=dict(color='blue',line=dict(color='darkblue', width=1))), row=1, col=1)
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
fig.add_trace(go.Scatter(x=obs_fig.index, y=obs_fig['q_m3s'], name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_xaxes(tickformat="%Y-%m-%dT%H")
fig.update_layout(legend_title_text='Modelo GR5i')
fig.update_layout(autosize=False,width=1200,height=675,margin=dict(l=30,r=30,b=10,t=10))
try:
    fig.write_image(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_gr5i_mod_{ano:04d}{mes:02d}{dia:02d}00.png')
except Exception as e:
    print('Falha ao salvar a figura de simulacao GR5i em .png')
    print(e)
    print('Será exportado figura em HTML. Deve ser exportada com configuracoes .png, mantendo o nome.')
    fig.write_html(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_gr5i_mod_{ano:04d}{mes:02d}{dia:02d}00.html')
    fig.show()

################################################################################
################################################################################
