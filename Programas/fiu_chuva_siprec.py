from netCDF4 import Dataset
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob
from time import time
import xarray as xr


inicio='2013-01-01 00:00:00'
fim='2020-12-31 23:59:59'
periodo=pd.date_range(start=inicio,end=fim,freq='1h',closed=None)
df_resumo = pd.DataFrame(index=periodo)

arquivo_grade = '../Dados/pontos_grade_fiu.csv'
df_grade = pd.read_csv(arquivo_grade, sep=',')

for i in df_grade.index:
    df_resumo[i] = np.nan
for tempo in periodo:
    print(tempo)
    try:
        hora=tempo.hour
        ano=tempo.year
        mes=tempo.month
        dia=tempo.day
        arquivo =f'/simepar/product/siprec/simepar/r1/hourly/{ano:04d}/{mes:02d}/{dia:02d}/siprec_v2_{ano:04d}_{mes:02d}_{dia:02d}_{hora:02d}.nc'
        da=xr.open_dataset(arquivo)
        for i in df_grade.index:
            lon = df_grade.loc[i,'x']
            lat = df_grade.loc[i,'y']
            try:
                chuva_ponto=da['SIPREC'].sel(latitudes=lat,longitudes=lon,method='nearest',drop=True)[0].values
            except:
                chuva_ponto=da['SIPREC'].sel(lat_sat=lat,lon_sat=lon,method='nearest',drop=True).values
            df_resumo.loc[tempo,i] = chuva_ponto
        da.close()
    except Exception as e:
        print(e)
df_resumo['pme_mm'] = df_resumo.mean(axis=1)
df_exporta = df_resumo[['pme_mm']]
df_exporta.to_csv('../Dados/pme_fiu_siprec.csv', sep=',', index_label='datahora',
                 date_format='%Y-%m-%dT%H:%M:%S+00:00', float_format='%.2f')
