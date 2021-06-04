## PARA DADOS EM NÍVEL DE SUPERFÍCIE
#imports
import pandas as pd
from datetime import datetime, timedelta
from ecmwfapi import ECMWFService
#fazendo um range para se colocar às datas selecionadas
date_range = pd.date_range(start='20190531',end='20190531', freq="D").strftime('%Y%m%d').to_list()
for dates in date_range:
    server = ECMWFService( "mars", url = "https://api.ecmwf.int/v1",
                           key = "66dc9750b0f18814d51fa8658c52d73f", email = "rafael.toshio@simepar.br")
    server.execute(
        {
            "class" :"od",
            "date" : dates, #pode remover esse range e usar dada como 20160101/to/20160102
            "expver" : "1",
            "levtype" : "sfc",
            "number" : "1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/40/41/42/43/44/45/46/47/48/49/50",
            "param" : "228.128", #Buscar parâmetro da variável no catálogo
            "grid" : "0.2/0.2", #tamanho da grade
            "step" : "all", #step de horas
            "area" : "-22.0/-55.0/-27.0/-48.0", #lat/lon
            "stream" : "enfo",
            "time" : "00",#rodada
            "type" : "pf",
            "target" : "data.grib2"
        },
        "../Dados/ECMWF_Grib/ECMWF_SSE05p01_SFC"+ dates +"_00.grib2")




#number=1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25/26/27/28/29/30/31/32/33/34/35/36/37/38/39/40/41/42/43/44/45/46/47/48/49/50,
#stream=enfo,
#type=pf,


#
#"area" : "-17.09000015258789/-36.45000076293945/-37.3699951171875/-63.6300048828125", #lat/lon


#Base times: 00
#Grid: 0.2
#Forecast time-steps: [00]: 0 to 90 by 1, 93 to 144 by 3, 150 to 360 by 6
#Areas: N: -19 W: -59 S: -34 E: -40
#Parameters: TP
