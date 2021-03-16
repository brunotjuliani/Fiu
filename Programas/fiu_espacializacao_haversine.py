import pandas as pd
import glob
import math
import numpy as np

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

# 1 - Abrir pontos da grade
arquivo_grade = '../Dados/pontos_grade_fiu.csv'
grade = pd.read_csv(arquivo_grade, sep=',')

# 2 - Inicializar os DataFrames
DF_postos = pd.DataFrame()
DF_grade = pd.DataFrame()
DF_grade.index.name = 'datahora'
DF_dists = pd.DataFrame()

# 3 - Abrir os arquivos de chuva individualmente - (diretorio com todos arquivos de chuva usados)
path_pd = '../Dados/Postos_Plu/'
arquivos_pd = glob.glob(path_pd+'*.csv')
for arquivo_pd in arquivos_pd:

    # 4 - Capturar as coordenadas de cada posto
    nome_posto = arquivo_pd.split('/')[-1].split('.csv')[0]
    lat_long = pd.read_csv(arquivo_pd, skiprows=2, nrows=1, header=None).iloc[0]
    long_p  = lat_long[0]
    lat_p = lat_long[1]

    # 5 - Calcular a distancia (km) entre o posto e todos os pontos da grade
    for pi in grade.index:
        ponto_x = grade.loc[pi].x
        ponto_y = grade.loc[pi].y
        dist = haversine(long_p, lat_p, ponto_x, ponto_y)
        DF_dists.loc[pi,nome_posto] = dist

    # 6 - Coletar a serie de dados do posto e conceatenar em DF_postos
    sr_posto = pd.read_csv(arquivo_pd, skiprows=3, parse_dates=True,
                           index_col='datahora')['chuva_mm']
    sr_posto = sr_posto.rename(nome_posto)
    DF_postos = DF_postos.join(sr_posto, how='outer')

# 7 - Calcular a precipitacao interpolada para cada ponto de grade
L = len(grade)
no_postos = len(DF_postos.columns)
for i,pi in enumerate(grade.index):
    print('Iniciando ponto {}/{} da grade.'.format(i+1,L))
    D = np.array([DF_dists.loc[pi,i] for i in DF_postos.columns]) # vetor de distancias
    W = np.array([1/(di**2) for di in D]) # vetor de pesos
    for t in DF_postos.index:
        P_t = DF_postos.loc[t].values # vetor precipitacoes
        W_t = np.array([0 if np.isnan(P_t[i]) else W[i] for i in range(no_postos)])
        prec = np.sum(W_t * np.nan_to_num(P_t))/np.sum(W_t)
        DF_grade.loc[t, pi] = np.around(prec, decimals=2)
print('Espacialização finalizada.')

# 8 - Calcular a PME na grade
PME = DF_grade.mean(axis=1, skipna=True)
PME
# 9 - Exporta PME
PME.rename('chuva_mm').round(2).to_csv('../Dados/pme_fiu.csv',
                                     index_label='datahora',float_format='%.2f',
                                     date_format='%Y-%m-%dT%H:%M:%S+00:00')
