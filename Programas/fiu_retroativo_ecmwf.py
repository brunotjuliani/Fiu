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

dispara = dt.datetime(2021, 5, 14,  00, tzinfo=dt.timezone.utc)
ano = dispara.year
mes = dispara.month
dia = dispara.day
d_prev = dispara.isoformat()

arquivo_grade = '../Dados/pontos_grade_fiu.csv'
grade = pd.read_csv(arquivo_grade, sep=',')
minx20k = min(grade['x']) - 0.2
maxx20k = max(grade['x']) + 0.2
miny20k = min(grade['y']) - 0.2
maxy20k = max(grade['y']) + 0.2

grbfile = f"../Dados/ECMWF_Grib/ECMWF_SSE05p01_SFC{ano:04d}{mes:02d}{dia:02d}_00.grib2"
grbs = pygrib.open(grbfile)

# Inicia dataframe p/ diferentes membros
dados_peq = pd.DataFrame()

ens_n = 1
while ens_n <= 50:
    df_previsao = pd.DataFrame()
    horizonte = 1
    while horizonte <= 168:
        previsao = dispara + dt.timedelta(hours = (horizonte))
        prev_mes = previsao.month
        prev_dia = previsao.day
        prev_hora = previsao.hour
        df_previsao.loc[horizonte,'datahora'] = previsao.isoformat()

        try:
            membro = grbs.select(perturbationNumber=ens_n, step=horizonte)
            print(horizonte, ens_n)
            pass
        except:
            horizonte +=1
            continue

        # Seleciona membro do ensemble e le variaveis
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

    # Encerra loop e insere no DF
    dados_peq['pme_'+str(ens_n)] = pme_prev['chuva_mm']
    ens_n += 1

dados_peq.to_csv(f'../fiu_ECMWF_{ano:04d}{mes:02d}{dia:02d}.csv',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00', sep = ",")

# ens_n = 0
# while ens_n <= 50:
#     print('Iniciando membro ECMWF ', ens_n+1)
#     # Inicia dataframe p/ diferentes membros
#     df_previsao = pd.DataFrame()
#
#     # Loop para range de horizontes (horas a frente de previsao)
#     horizonte = 1
#     while horizonte <= 168:
#         previsao = dispara + dt.timedelta(hours = (horizonte))
#         prev_mes = previsao.month
#         prev_dia = previsao.day
#         prev_hora = previsao.hour
#         df_previsao.loc[horizonte,'datahora'] = previsao.isoformat()
#
#         ## LEITURA DO ARQUIVO GRIB - 1 HORIZONTE DE PREVISÃO - ENSEMBLE COM N DADOS
#         ## Atualização do endereço do arquivo - 30/03
#         grbfile = f"/simepar/modelos/ecmwf/ens/SSE/0p2/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/D1E{mes:02d}{dia:02d}0000{prev_mes:02d}{prev_dia:02d}{prev_hora:02d}001.grib2"
#         try:
#             grbs = pygrib.open(grbfile)
#         except:
#             grbfile = f"/simepar/modelos/ecmwf/ens/SSE/0p2/pos/{ano:04d}/{mes:02d}/{dia:02d}/00/D1X{mes:02d}{dia:02d}0000{prev_mes:02d}{prev_dia:02d}{prev_hora:02d}001.grib2"
#             try:
#                 grbs = pygrib.open(grbfile)
#                 pass
#             except:
#                 horizonte +=1
#                 continue
#
#         # Seleciona membro do ensemble e le variaveis
#         membro = grbs.select(perturbationNumber=ens_n)
#         data, lats, lons = membro[0].data(lat1=miny20k, lat2=maxy20k, lon1=minx20k, lon2=maxx20k)
#         data2 = np.hstack(data)
#
#         # Divide dataframe para os pontos estudados
#         ponto = 0
#         while ponto < len(data2):
#             df_previsao.loc[horizonte,ponto] = data2[ponto]
#             ponto += 1
#         horizonte += 1
#
#
#     # Datetime index
#     df_previsao['datahora']= pd.to_datetime(df_previsao['datahora'])
#     df_previsao = df_previsao.set_index('datahora')
#     # Remove linhas sem previsao
#     df_previsao = df_previsao.dropna(axis = 0, how = 'all')
#     # Separa chuva por passo de tempo do acumulado - fillna para lidar com primeira linha
#     df_discreto = df_previsao.diff().fillna(df_previsao.iloc[0])
#     # Acumula para passo de tempo de 6 horas
#     df_6hrs = df_discreto.resample("6H", closed='right', label = 'right').sum()
#
#     # Inicializa DataFrames de espacialização
#     DF_postos = df_6hrs
#     DF_grade = pd.DataFrame()
#     DF_grade.index.name = 'datahora'
#     DF_dists = pd.DataFrame()
#
#     # Capturar as coordenadas de cada ponto de previsao e comparar com grade da bacia
#     lats2 = np.hstack(lats)
#     lons2 = np.hstack(lons)
#     ponto = 0
#     while ponto < len(lats2):
#         long_p  = lons2[ponto] - 360 #para deixar no mesmo formato da grade base
#         lat_p = lats2[ponto]
#         # Calcular a distancia (km) entre os pontos de previsao e grade da bacia
#         for pi in grade.index:
#             ponto_x = grade.loc[pi].x
#             ponto_y = grade.loc[pi].y
#             dist = haversine(long_p, lat_p, ponto_x, ponto_y)
#             DF_dists.loc[pi,ponto] = dist
#         ponto +=1
#
#     # Calcular a precipitacao interpolada para cada ponto de grade
#     L = len(grade)
#     no_postos = len(DF_postos.columns)
#     for i,pi in enumerate(grade.index):
#         D = np.array([DF_dists.loc[pi,i] for i in DF_postos.columns]) # vetor de distancias
#         W = np.array([1/(di**2) for di in D]) # vetor de pesos
#         for t in DF_postos.index:
#             P_t = DF_postos.loc[t].values # vetor precipitacoes
#             W_t = np.array([0 if np.isnan(P_t[i]) else W[i] for i in range(no_postos)])
#             prec = np.sum(W_t * np.nan_to_num(P_t))/np.sum(W_t)
#             DF_grade.loc[t, pi] = np.around(prec, decimals=2)
#     # Calcular a espacialização da previsao
#     PME = DF_grade.mean(axis=1, skipna=True)
#     pme_prev = pd.DataFrame(PME.rename('chuva_mm').round(2))
#     pme_prev.index = pme_prev.index
#
#     # Inclui previsao
#     chuva_comb = pd.concat([chuva_recorte, pme_prev])
#     chuva_comb = chuva_comb[~chuva_comb.index.duplicated(keep='last')]
#     chuva_comb = chuva_comb.rename(columns={'chuva_mm':'pme'})
#
#     # Encerra loop e insere no DF
#     dados_peq['pme_'+str(ens_n)] = chuva_comb['pme']
#     ens_n += 1
