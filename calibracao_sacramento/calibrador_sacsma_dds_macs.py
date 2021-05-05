import pandas as pd
import numpy as np
import math
import sacsma2021
from sacsma2021 import Xnomes, Xmin, Xmax
import dds
from plotly.subplots import make_subplots
import plotly.graph_objects as go

### DEFINICAO FUNÇÕES OBJETIVO E SIMULAÇÃO
def fobj_nse(X):
    params = X
    Qsim = sacsma2021.simulacao(area, dt, PME, ETP, params)
    Qsim = pd.Series(index=idx, data=Qsim, name='qsim')
    df = pd.concat([Qsim, Qobs], axis=1)
    df = df.loc[idx_cal]
    df = df.dropna()
    NSE = 1 - df.apply(lambda x:(x.qsim-x.qobs)**2,axis=1).sum()/df.apply(lambda x:(x.qobs-df.qobs.mean())**2,axis=1).sum()
    fmin = 1 - NSE
    return fmin

def fobj_log(X):
    params = X
    Qsim = sacsma2021.simulacao(area, dt, PME, ETP, params)
    Qsim = pd.Series(index=idx, data=Qsim, name='qsim')
    df = pd.concat([Qsim, Qobs], axis=1)
    df = df.loc[idx_cal]
    df = df.dropna()
    df['log_min'] = df.apply(lambda x: (np.log(x['qsim']) - np.log(x['qobs']))**2, axis=1)
    fmin = df['log_min'].sum()
    return fmin

def fobj_drms(X):
    params = X
    Qsim = sacsma2021.simulacao(area, dt, PME, ETP, params)
    Qsim = pd.Series(index=idx, data=Qsim, name='qsim')
    df = pd.concat([Qsim, Qobs], axis=1)
    df = df.loc[idx_cal]
    df = df.dropna()
    df['drms_min'] = df.apply(lambda x: (x['qsim'] - x['qobs'])**2, axis=1)
    fmin = math.sqrt(df['drms_min'].sum())/len(df)
    return fmin

def sim(X):
    params = X
    Qsim = sacsma2021.simulacao(area, dt, PME, ETP, params)
    Qsim = pd.Series(index=idx, data=Qsim, name='qsim')
    return Qsim

### GUIA DE ORDEM DE PARÂMETROS
##### 'UZTWM' : 0
##### 'UZFWM' : 1
##### 'LZTWM' : 2
##### 'LZFPM' : 3
##### 'LZFSM' : 4
##### 'UZK' : 5
##### 'LZPK' : 6
##### 'LZSK' : 7
##### 'ADIMP' : 8
##### 'PCTIM' : 9
##### 'ZPERC' : 10
##### 'REXP' : 11
##### 'PFREE' : 12
##### 'NUH' : 13
##### 'KUH' : 14
##### 'NMSK' : 15
##### 'KMSK' : 16
##### 'XMSK' : 17


### LEITURA FORÇANTES
bn = 'XX'
bnome = 'Fiu'
m_hrs = 6
area = pd.read_csv(f'../Dados/{bnome}_peq.csv', nrows=1, header=None).values[0][0]
dt = 0.25 # 6 hr
PEQ = pd.read_csv(f'../Dados/{bnome}_peq.csv', skiprows=1,
                  parse_dates=True, index_col='datahora')
PME = PEQ['pme']
ETP = PEQ['etp']
Qobs = PEQ[f'M_{m_hrs}'].rename('qobs')
idx = PME.index
idx_cal = idx[idx > '2019-01-01']
Xmin = Xmin[:-3] # desconsidera os parametros de propagacao (Qmon=None)
Xmax = Xmax[:-3] # desconsidera os parametros de propagacao (Qmon=None)

### PRIMEIRA CALIBRAÇÃO -> LOG P/ TODOS OS PARAMETROS
### MAIOR PE3SO PARA LOW-FLOW, COM BOAS ESTIMAÇÕES Ṕ/ LOWER ZONE
### PARÂMETROS OBJETIVADOS:
### ['LZTWM', 'LZFPM', 'LZFSM', 'LZPK', 'LZSK', 'PFREE']
Xmin_1 = Xmin.copy()
Xmax_1 = Xmax.copy()
X1, F1 = dds.dds(Xmin_1, Xmax_1, fobj_log, r=0.2, m=1000)
Qsim_1 = sim(X1)


### SEGUNDA CALIBRAÇÃO -> DRMS P/ PARAMETROS DA UPPER ZONE
### ESTIMA PARAMETROS QUE INFLUENCIAM PICOS DE CHEIA:
### [UZTWM, UZFWM, UZK, ADIMP, ZPERC, REXP]
### PARA ISSO, SÃO FIXADOS OS DEMAIS PARÂMETROS OBTIDOS NA ETAPA 1 (LOWER ZONE)
Xmin_2 = Xmin.copy()
Xmin_2[2], Xmin_2[3], Xmin_2[4] = X1[2], X1[3], X1[4] #'LZTWM', 'LZFPM', 'LZFSM'
Xmin_2[6], Xmin_2[7], Xmin_2[12] = X1[6], X1[7], X1[12] #'LZPK', 'LZSK', 'PFREE'
Xmax_2 = Xmax.copy()
Xmax_2[2], Xmax_2[3], Xmax_2[4] = X1[2], X1[3], X1[4] #'LZTWM', 'LZFPM', 'LZFSM'
Xmax_2[6], Xmax_2[7], Xmax_2[12] = X1[6], X1[7], X1[12] #'LZPK', 'LZSK', 'PFREE'
X2, F2 = dds.dds(Xmin_2, Xmax_2, fobj_drms, r=0.2, m=1000)
Qsim_2 = sim(X2)


### TERCEIRA CALIBRAÇÃO -> LOG P/ REFINAR PARAMETROS DA LOWER ZONE:
### ['LZTWM', 'LZFPM', 'LZFSM', 'LZPK', 'LZSK', 'PFREE']
### PARA ISSO, SÃO FIXADOS OS PARÂMETROS OBTIDOS NA ETAPA 2 (UPPER ZONE)
Xmin_3 = Xmin.copy()
Xmin_3[0], Xmin_3[1], Xmin_3[5] = X2[0], X2[1], X2[5] #'UZTWM', 'UZFWM', 'UZK'
Xmin_3[8], Xmin_3[10], Xmin_3[11] = X2[8], X2[10], X2[11] #'ADIMP', 'ZPERC', 'REXP'
Xmax_3 = Xmax.copy()
Xmax_3[0], Xmax_3[1], Xmax_3[5] = X2[0], X2[1], X2[5] #'UZTWM', 'UZFWM', 'UZK'
Xmax_3[8], Xmax_3[10], Xmax_3[11] = X2[8], X2[10], X2[11] #'ADIMP', 'ZPERC', 'REXP'
X3, F3 = dds.dds(Xmin_3, Xmax_3, fobj_log, r=0.2, m=1000)
Qsim_3 = sim(X3)


# ### CALIBRAÇÃO COM NASH DIRETO
# Xmin_4 = Xmin.copy()
# Xmax_4 = Xmax.copy()
# X4, F4 = dds.dds(Xmin_4, Xmax_4, fobj_nse, r=0.2, m=1000)
# Qsim_4 = sim(X4)

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
fig.add_trace(go.Scatter(x=idx, y=PME, name="PME (mm)"), row=1, col=1)
fig['layout']['yaxis']['autorange'] = "reversed"
#fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="ETP (mm)"), row=1, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qobs, name="Qobs (m3/s)", marker_color='black'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qsim_1, name='Qsim - 1', marker_color='green'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qsim_2, name='Qsim - 2', marker_color='red'), row=2, col=1)
fig.add_trace(go.Scatter(x=idx, y=Qsim_3, name='Qsim - 3', marker_color='purple'), row=2, col=1)
# fig.add_trace(go.Scatter(x=idx, y=Qsim_4, name='Qsim - 4 (NSE)', marker_color='orange'), row=2, col=1)
fig.update_yaxes(title_text='Chuva [mm]', row=1, col=1)
fig.update_yaxes(title_text='Vazão [m3s-1]', row=2, col=1)
fig.update_layout(legend_title_text='Comparação Modelo Sacramento')
fig.update_layout(autosize=False,width=800,height=450,margin=dict(l=30,r=30,b=10,t=10))
fig.show()

df_params = pd.DataFrame()
df_params['Parametros'] = Xnomes
df_params['Par_LOG'] = np.append(X1,[None, None, None])
df_params['Par_DRMS'] = np.append(X2,[None, None, None])
df_params['Par_MACS'] = np.append(X3,[None, None, None])
# df_params['Par_NSE'] = np.append(X4,[None, None, None])

df_params.to_csv(f'./param_macs/param_macs_{bnome}_{m_hrs}.csv', index=False)
