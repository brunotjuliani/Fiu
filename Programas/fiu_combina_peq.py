import pandas as pd
import numpy as np
import csv
import sys
import datetime
import pytz


bacia = 'XX'
nome = 'Fiu'
area = 534

precip = pd.read_csv('../Dados/pme_fiu.csv', index_col = 0, sep = ',')
precip.index = pd.to_datetime(precip.index)
precip.columns = ['pme']
data_inicial = precip.index[0]
data_final = precip.index[-1]


vazao = pd.read_excel('../Dados/Fiu_CAV_2013_2021.xlsx')
vazao.index = (pd.to_datetime(vazao.Data) + pd.to_timedelta(vazao.Hora, unit = 'h'))
vazao.index = vazao.index.tz_localize('UTC')
vazao['qjus'] = np.where((vazao['VAZAO AFLUENTE'] == 'S/L'), np.nan, vazao['VAZAO AFLUENTE'])
vazao = vazao[['qjus']]
vazao2 = pd.DataFrame()
vazao2['qjus'] = pd.to_numeric(vazao.loc[:,'qjus'])
vazao2['qjus'] = np.where((vazao2['qjus'] < 0), np.nan, vazao2['qjus'])
#vazao2['qjus'] = vazao2['qjus'].rolling(window=4, min_periods=1).mean()


if vazao2.index[0] > data_inicial:
    data_inicial = vazao.index[0]
if vazao2.index[-1] < data_final:
    data_final = vazao2.index[-1]

dados_peq = pd.merge(precip, vazao2, how = 'outer',
                 left_index = True, right_index = True)

etp = pd.read_csv('../Dados/etp_londrina_padrao.csv', sep = ',')
etp.index = (etp['Mes'].map('{:02}'.format) + '-' +
             etp['Dia'].map('{:02}'.format) + '-' +
             etp['Hora'].map('{:02}'.format))
dados_peq['data'] = dados_peq.index.strftime('%m-%d-%H')
dados_peq['etp'] = dados_peq['data'].map(etp['etp'])
dados_peq = dados_peq.drop(['data'], axis=1)

dados_peq = dados_peq.loc[data_inicial:data_final]
dados_6hrs = (dados_peq.resample("6H", closed='right', label = 'right').
              agg({'pme' : np.sum, 'etp' : np.sum, 'qjus' : np.mean}))
dados_6hrs = dados_6hrs.rename(columns={'qjus':'M_6'})
dados_6hrs['M_12'] = dados_6hrs['M_6'].rolling(window=2, min_periods=1).mean()
dados_6hrs['M_24'] = dados_6hrs['M_6'].rolling(window=4, min_periods=1).mean()

with open('../Dados/Fiu_peq.csv', 'w', newline = '') as file:
    writer = csv.writer(file)
    writer.writerow([area])
dados_6hrs.to_csv('../Dados/Fiu_peq.csv', mode = 'a',
                 index_label='datahora', float_format = '%.3f')
