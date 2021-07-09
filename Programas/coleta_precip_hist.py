import pandas as pd
import numpy as np
import datetime as dt
import psycopg2, psycopg2.extras
import csv


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

posto_nome = 'Barragem_PCH_Apucaraninha'
posto_informacoes = ['23745090', '2350015', '-23.75001', '-50.90772', '611']
print('Atualizando ', posto_nome)
posto_codigo = posto_informacoes[0]
posto_ana = posto_informacoes[1]
posto_lat = float(posto_informacoes[2])
posto_long = float(posto_informacoes[3])
posto_alt = float(posto_informacoes[4])

data0 = '2013-11-01T00:00:00+00:00'
data1 = '2021-07-03T00:00:00+00:00'
t_ini = pd.Timestamp(data0)
t_fim = pd.Timestamp(data1)

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

table_hor

#exporta serie atualizada
with open('../Dados/Postos_Plu/'+posto_nome+'.csv','w',newline='') as file:
    writer = csv.writer(file)
    writer.writerow([posto_ana])
    writer.writerow([posto_nome])
    writer.writerow([posto_long, posto_lat, posto_alt])
table_hor.to_csv('../Dados/Postos_Plu/'+posto_nome+'.csv', mode = 'a', sep = ",",
                 date_format='%Y-%m-%dT%H:%M:%S+00:00', float_format='%.2f')
