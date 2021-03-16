import numpy as np
import pandas as pd
import datetime as dt
import csv
import psycopg2, psycopg2.extras


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


#Lista postos de precipitacao com as seguintes informacoes
# Nome : [codigo simepar, codigo ANA, latitude, longitute, altitude]
postos_precip = {
    'Apucaraninha_Montante':['23735103', '2351079', '-23.73056', '-51.03778', '688'],
#    'Barragem_PCH_Apucaraninha':['23745090', '2350015', '-23.75001', '-50.90772', '611'],
#    'Reservatorio_Fiu':['23745094', '2350016', '-23.74906', '-50.94049', '430']
    }

## COLETA DADOS PRECIPITACAO
for posto_nome, posto_informacoes in postos_precip.items():
    posto_codigo = posto_informacoes[0]
    posto_ana = posto_informacoes[1]
    posto_lat = posto_informacoes[2]
    posto_long = posto_informacoes[3]
    posto_alt = posto_informacoes[4]

    ########## SERIES 15 MIN ##########
    print('Coletando dados brutos',posto_nome)
    #t_ini = dt.datetime(1997, 1, 1,  0,  0) #AAAA, M, D, H, Min
    #t_fim = dt.datetime(2021, 2, 26,  0,  0)
    t_ini = dt.datetime(2021, 1, 1,  0,  0)
    hoje = dt.date.today()
    t_fim = dt.datetime(hoje.year, hoje.month, hoje.day,  00, tzinfo=dt.timezone.utc)

    #coleta dados de precipitacao
    dados = coletar_dados(t_ini,t_fim, posto_codigo, '(7)')
    dados.columns = ['chuva_mm', 'sensor']
    dados = dados.drop('sensor', 1)

    #converte indice para formato DATETIME ISO UTC
    dados.index = pd.to_datetime(dados.index, utc=True).rename('datahora')
    dados["chuva_mm"] = pd.to_numeric(dados["chuva_mm"], downcast = "float")

    ########## TRATA SERIES 15 MIN ##########

    #DADOS BRUTOS -> FLAG 0
    #DADO BRUTO BAIXADO SEM VALOR -> FLAG 1
    dados['flag'] = np.where(dados['chuva_mm'].isnull(), 1, 0)

    # cria DFs padrão de data, para serem preenchidas com os dados baixados
    t_ini = dados.index[0]
    t_fim = dados.index[-1]

    date_rng_15min = pd.date_range(start=t_ini, end=t_fim,freq='15min',tz="UTC")
    table_15min = pd.DataFrame(date_rng_15min, columns=['datahora'])
    table_15min['datahora']= pd.to_datetime(table_15min['datahora'])
    table_15min = table_15min.set_index('datahora')
    df_15min = pd.merge(table_15min, dados, how='left',
                        left_index=True, right_index=True)
    df_15min = df_15min[~df_15min.index.duplicated(keep='first')]

    #DATA SEM REGISTRO NA SERIE DE DADOS BRUTOS -> FLAG 2
    df_15min['flag'] = np.where(df_15min['flag'].isnull(), 2, df_15min['flag'])

    #SINALIZA A OCORRENCIA DE VALORES NEGATIVOS -> FLAG 3
    #SINALIZA A OCORRENCIA DE VALORES SUPERIORES A 45 MM -> FLAG 3
    #REMOVE VALORES DE COTA NEGATIVOS
    df_15min['flag'] = np.where((df_15min['chuva_mm'] < 0), 3, df_15min['flag'])
    df_15min['chuva_mm'] = np.where((df_15min['chuva_mm'] < 0
                                     ), np.nan, df_15min['chuva_mm'])
    df_15min['flag'] = np.where((df_15min['chuva_mm'] >45), 3, df_15min['flag'])
    df_15min['chuva_mm'] = np.where((df_15min['chuva_mm'] > 45
                                     ), np.nan, df_15min['chuva_mm'])

    #SINALIZA PERSISTENCIA DE VALORES NAO NULOS -> FLAG 4
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

    #COLUNA FLAG PARA INTEIRO
    df_15min['flag'] = df_15min['flag'].astype(int)



    ########## TRANSFORMA SERIE HORARIA ##########

    df_15min.drop(['flag'], axis=1, inplace = True)

    #cria DFs padrao horario para ser preenchido com os dados de 15 min
    t_ini = df_15min.index[0].round('1h')
    t_fim = df_15min.index[-1]
    date_rng_horario = pd.date_range(start=t_ini, end=t_fim, freq='H', tz="UTC")
    table_hor = pd.DataFrame(date_rng_horario, columns=['date'])
    table_hor['datahora']= pd.to_datetime(table_hor['date'])
    table_hor = table_hor.set_index('datahora')
    table_hor.drop(['date'], axis=1, inplace = True)

    # agrupa em dados horarios, com intervalo fechado à direita (acumulado/media da 0:01 a 1:00);
    # coluna count resulta a soma (contagem) dos "1", coluna valor resulta na media dos valores;
    # para os valores de cont < 4, substitui o dado em 'valor' por NaN:
    df_15min['count'] = np.where(df_15min['chuva_mm'].notnull(), 1, 0)
    df_horario = (df_15min.resample("H", closed='right', label='right').
                  agg({'count' : np.sum, 'chuva_mm' : np.sum}))
    #df_horario.loc[df_horario['count'] < 4, ['q_m3s']] = np.nan
    #df_horario.loc[df_horario['count'] < 4, ['m']] = np.nan

    #REMOVE A OCORRENCIA DE VALORES HORARIOS SUPERIORES A 90 MM
    df_horario['chuva_mm'] = np.where((df_horario['chuva_mm'] > 90
                                         ), np.nan, df_horario['chuva_mm'])

    # remove colunas 'count' dos dataframes e agrupa com data padrao
    df_horario.drop('count', axis=1, inplace=True)
    table_hor = pd.merge(table_hor, df_horario, left_index = True,
                         right_index = True, how = 'left')
    table_hor = table_hor[~table_hor.index.duplicated(keep='first')]

    serie_diaria = table_hor.resample("D", closed='right', label = 'left').sum()

    serie_diaria.to_csv('../Dados/Postos_Plu/'+posto_nome+'_diario.csv',
                        sep = ",", date_format='%Y-%m-%d', float_format='%.2f')
    # #exporta dados horarios para csv
    # with open('../Dados/Postos_Plu/'+posto_nome+'.csv','w',newline='') as file:
    #     writer = csv.writer(file)
    #     writer.writerow([posto_ana])
    #     writer.writerow([posto_nome])
    #     writer.writerow([posto_long, posto_lat, posto_alt])
    # table_hor.to_csv('../Dados/Postos_Plu/'+posto_nome+'.csv', mode = 'a', sep = ",",
    #                  date_format='%Y-%m-%dT%H:%M:%S+00:00', float_format='%.2f')

    print(posto_nome, ' acabou - ', list(postos_precip).index(posto_nome)+1,"/",
          len(postos_precip))
table_hor
serie_diaria
serie_diaria
