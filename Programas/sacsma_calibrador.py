import pandas as pd
from spotpy.analyser import *
from spotpy.algorithms import sceua
import sacsma2021
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# FORCANTES
area = float(pd.read_csv('peq_jaguari_buenopolis.csv', nrows=0).columns[0])
dt = 1
PEQ = pd.read_csv('peq_jaguari_buenopolis.csv', skiprows=1, index_col='datahora', parse_dates=True)
idx = PEQ.index
PME  = PEQ['pme']
ETP  = PEQ['etp']
Qjus = PEQ['qjus']
Qmon = PEQ['qmon']

# CALIBRACAO
t1_cal = pd.Timestamp('2015-01-01', tz='UTC')
idx_cal = idx[idx >= t1_cal]
spot_setup = sacsma2021.spotpy(area, dt, PME, ETP, Qjus, idx, idx_cal, Qmon=Qmon, fobj='LOG')
sampler = sceua(spot_setup)
# sampler.sample(100)
sampler.sample(8000, ngs=15, kstop=1, peps=0.1, pcento=5)
results = sampler.getdata()
params = get_best_parameterset(results, maximize=False)
params_nomes = list(params.dtype.names)
params_valores = list(params[0])
DF_params = pd.DataFrame(data=params_valores, index=params_nomes, columns=['valor'])
DF_params.to_csv('resultados/par_jaguari_buenopolis.csv')
bestindex, bestobjf = get_minlikeindex(results)
simulation_fields = get_simulation_fields(results)
Qsim = list(results[simulation_fields][bestindex][0])
# Plot dos resultados
Qsim = pd.Series(index=idx, data=Qsim)
Qjus.plot(color='black')
Qsim.plot(color='red')
plt.show()

#
# fig = make_subplots(rows=3, cols=1, shared_xaxes=True, \
# specs=[[{'rowspan': 1, 'colspan': 1}],[{'rowspan': 2, 'colspan': 1}],[{'rowspan': 0, 'colspan': 0}]])
# fig.add_trace(go.Scatter(x=PEQ.index, y=PEQ['pme'], name="pme"), row=1, col=1)
# fig['layout']['yaxis']['autorange'] = "reversed"
# fig.add_trace(go.Scatter(x=PEQ.index, y=ETP, name="etp"), row=1, col=1)
# fig.add_trace(go.Scatter(x=PEQ.index, y=Qjus, name="qjus"), row=2, col=1)
# fig.add_trace(go.Scatter(x=PEQ.index, y=Qmon, name="Qmon"), row=2, col=1)
# fig.show()
