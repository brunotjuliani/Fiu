import pandas as pd
import numpy as np

vazao = pd.read_csv('Fiu_dados_op_2021.txt', skiprows=5, header=None)

vazao['data'] = vazao[0].str.slice(0,8)
vazao['hora'] = vazao[0].str.slice(10,12)
vazao['qjus'] = vazao[0].str.slice(48,53)
vazao['qjus'] = pd.to_numeric(vazao['qjus'])
vazao['datas'] = pd.to_datetime(vazao['data'], dayfirst=True)
vazao['horas'] = pd.to_numeric(vazao['hora'])
vazao.index = (pd.to_datetime(vazao.datas) + pd.to_timedelta(vazao.horas, unit = 'h'))
vazao.index = vazao.index.tz_localize('UTC')
vazao.drop([0, 'data', 'hora','datas','horas'], axis=1, inplace=True)
vazao['qjus'] = np.where((vazao['qjus'] < 0), np.nan, vazao['qjus'])
vazao
q_hist = pd.read_csv('../Dados/vazao_fiu.csv', index_col='datahora')
q_hist.index = pd.to_datetime(q_hist.index, utc=True)
q_hist.columns = ['qjus']
q_hist

q_att = pd.concat([q_hist, vazao])
q_att = q_att[~q_att.index.duplicated(keep='last')]

q_att
q_att.to_csv('../Dados/vazao_fiu.csv', index_label='datahora',float_format='%.2f',date_format='%Y-%m-%dT%H:%M:%S+00:00')
