import numpy as np
import pandas as pd
import datetime as dt
import os

#Data Boletim
disparo = open('../Dados/disparo.txt')
data_bol = disparo.readline().strip()
disparo.close()
data_boletim = data_bol[0:10]
data_detalhe = dt.datetime.strptime(data_boletim, '%Y-%m-%d')
ano = data_detalhe.year
mes = data_detalhe.month
dia = data_detalhe.day

#TABELA 1 - Chuva Diária Observada
#Dados diários observados - 7 dias atrás
data_0 = pd.Timestamp(data_bol) - dt.timedelta(days=7)
datas_obs = pd.date_range(start=data_0,end=data_bol,freq='d', closed = 'left').to_series()
df_obs= pd.DataFrame(index=datas_obs)
df_obs.index = df_obs.index.strftime('%Y-%m-%d')
#Dados estacoes
postos_precip = {
    'Apucaraninha_Montante':['23735103', '2351079', '-23.73056', '-51.03778', '688'],
    'Barragem_PCH_Apucaraninha':['23745090', '2350015', '-23.75001', '-50.90772', '611'],
    'Reservatorio_Fiu':['23745094', '2350016', '-23.74906', '-50.94049', '430']
    }
for posto_nome, posto_informacoes in postos_precip.items():
    sr_posto = pd.read_csv('../Dados/Postos_Plu/diario_'+posto_nome+'.csv',
                           parse_dates=True, index_col='data')
    sr_posto = sr_posto['chuva_mm'].rename(posto_nome)
    df_obs = df_obs.join(sr_posto, how='left')
#Dados chuva integrada na bacia
sr_pme = pd.read_csv('../Dados/diario_pme_fiu.csv', parse_dates=True, index_col='data')
sr_pme = sr_pme['chuva_mm'].rename('Chuva_Integrada')
df_obs = df_obs.join(sr_pme, how='left')
df_obs = df_obs.round(1)
df_obs.index = df_obs.index.strftime('%Y-%m-%d')

#TABELA 2 - Previsao Sacramento
df_sac = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/sim_sac_{ano:04d}{mes:02d}{dia:02d}00.csv',
                     parse_dates=True, index_col='datahora')
df_sac = df_sac[['Qmin', 'Q25', 'Qmed', 'Q75', 'Qmax', 'Qsac_wrf']]
df_sac = df_sac.round(2)
df_sac.index = df_sac.index.strftime('%Y-%m-%dT%H')

#TABELA 3 - Previsao GR5i
df_gr5 = pd.read_csv(f'../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/sim_gr5_{ano:04d}{mes:02d}{dia:02d}00.csv',
                     parse_dates=True, index_col='datahora')
df_gr5 = df_gr5[['Qmin', 'Q25', 'Qmed', 'Q75', 'Qmax', 'Qgr5_wrf']]
df_gr5 = df_gr5.round(2)
df_gr5.index = df_gr5.index.strftime('%Y-%m-%dT%H')

## LATEX BOLETIM
script = open('../Boletim/boletim.tex','w')
script.write(f'''
% Papel A4, fonte Times tamanho 12
\\documentclass[a4paper,12pt]{{article}}
% Determinando tamanhos de margens
\\usepackage[left=2cm, right=2cm, top=3cm, bottom=1cm]{{geometry}}
% Preâmbulo para documentos em português
\\usepackage[brazil]{{babel}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[pdftex]{{graphicx}}
\\usepackage{{color}}
\\usepackage{{fancyhdr}}
\\usepackage{{multirow}}
\\usepackage{{hhline}}
\\usepackage[skip=0pt]{{caption}}

\\begin{{document}}

\\pagestyle{{fancy}}
\\fancyhead[R]{{\includegraphics[width = 4cm]{{logo_simepar.png}}}}
\\renewcommand{{\headrulewidth}}{{1pt}}
\\begin{{center}}
\\vspace{{10pt}}
\\Large{{\\textbf{{Previsão de Afluência - Reservatório de Fiu}}}}\\\\
\\Large{{\\textbf{{{data_boletim}}}}}
\\noindent
\\rule{{\\textwidth}}{{1pt}}
\\end{{center}}

\\vspace{{6pt}}
\\textbf{{\\large{{Localização das estações}}}}

\\begin{{figure}}[ht]
    \\centering
    \\includegraphics[height=300pt]{{area_fiu.jpeg}}
    \\vspace{{6pt}}
    \\caption{{Bacia de Fiu}}
\\end{{figure}}

\\vspace{{6pt}}
\\textbf{{\\large{{Chuva Observada}}}}

\\begin{{table}}[ht]
    \\centering
    \\caption{{Dados de chuva observada na bacia}}
    \\vspace{{6pt}}
    \\begin{{tabular}}{{|c|c|c|c|c|}}
        \\hline
        & \\multicolumn{{3}}{{|c|}}{{Estação}} & \\\\
        \\hhline{{~---~}}
        & Apucaraninha & Barragem PCH & & \\\\
        & Montante & Apucaraninha & Reservatório Fiu & Chuva Integrada \\\\
        \\hhline{{~----}}
        Dia & \\multicolumn{{4}}{{|c|}}{{Precipitação (mm)}} \\\\
        \\hline
        {df_obs.index[-7]} & {df_obs.iloc[-7,0]} & {df_obs.iloc[-7,1]} & {df_obs.iloc[-7,2]} & {df_obs.iloc[-7,3]} \\\\
        \\hline
        {df_obs.index[-6]} & {df_obs.iloc[-6,0]} & {df_obs.iloc[-6,1]} & {df_obs.iloc[-6,2]} & {df_obs.iloc[-6,3]} \\\\
        \\hline
        {df_obs.index[-5]} & {df_obs.iloc[-5,0]} & {df_obs.iloc[-5,1]} & {df_obs.iloc[-5,2]} & {df_obs.iloc[-5,3]} \\\\
        \\hline
        {df_obs.index[-4]} & {df_obs.iloc[-4,0]} & {df_obs.iloc[-4,1]} & {df_obs.iloc[-4,2]} & {df_obs.iloc[-4,3]} \\\\
        \\hline
        {df_obs.index[-3]} & {df_obs.iloc[-3,0]} & {df_obs.iloc[-3,1]} & {df_obs.iloc[-3,2]} & {df_obs.iloc[-3,3]} \\\\
        \\hline
        {df_obs.index[-2]} & {df_obs.iloc[-2,0]} & {df_obs.iloc[-2,1]} & {df_obs.iloc[-2,2]} & {df_obs.iloc[-2,3]} \\\\
        \\hline
        {df_obs.index[-1]} & {df_obs.iloc[-1,0]} & {df_obs.iloc[-1,1]} & {df_obs.iloc[-1,2]} & {df_obs.iloc[-1,3]} \\\\
        \\hline
    \\end{{tabular}}
\\end{{table}}

\\newpage
\\textbf{{\\large{{Previsão Hidrometeorológica}}}}
\\smallbreak
\\textbf{{\\small{{Modelo Sacramento}}}}\\\\
\\begin{{figure}}[ht]
    \\centering
    \\vspace{{-24pt}}
    \\includegraphics[width=\\textwidth]{{fig_sac_{ano:04d}{mes:02d}{dia:02d}00.png}}
    \\caption{{Previsão de afluência para o reservatório - Modelo Sacramento}}
\\end{{figure}}

\\textbf{{\\small{{Modelo GR5i}}}}\\\\
\\begin{{figure}}[ht]
    \\centering
    \\vspace{{-24pt}}
    \\includegraphics[width=\\textwidth]{{fig_gr5i_{ano:04d}{mes:02d}{dia:02d}00.png}}
    \\caption{{Previsão de afluência para o reservatório - Modelo GR5i}}
\\end{{figure}}

\\newpage
\\textbf{{\\large{{Detalhamento Previsões}}}}
\\begin{{table}}[ht]
    \\centering
    \\caption{{Valores de vazão afluente média prevista - Modelo Sacramento}}
    \\vspace{{6pt}}
    \\begin{{tabular}}{{|c|c|c|c|c|c|c|}}
        \\hline
        & \\multicolumn{{5}}{{|c|}}{{Simulação com chuva ECMWF}} & Simulação com \\\\
        \\hhline{{~-----~}}
        & Mínimo & Quantil 25 & Mediana & Quantil 75 & Máximo & chuva WRF \\\\
        \\hhline{{~------}}
        Hora & \\multicolumn{{6}}{{|c|}}{{Vazão Média Prevista (m3s-1)}} \\\\
        \\hline
        {df_sac.index[0]} & {df_sac.iloc[0,0]} & {df_sac.iloc[0,1]} & {df_sac.iloc[0,2]} & {df_sac.iloc[0,3]} & {df_sac.iloc[0,4]} & {df_sac.iloc[0,5]} \\\\
        \\hline
        {df_sac.index[1]} & {df_sac.iloc[1,0]} & {df_sac.iloc[1,1]} & {df_sac.iloc[1,2]} & {df_sac.iloc[1,3]} & {df_sac.iloc[1,4]} & {df_sac.iloc[1,5]} \\\\
        \\hline
        {df_sac.index[2]} & {df_sac.iloc[2,0]} & {df_sac.iloc[2,1]} & {df_sac.iloc[2,2]} & {df_sac.iloc[2,3]} & {df_sac.iloc[2,4]} & {df_sac.iloc[2,5]} \\\\
        \\hline
        {df_sac.index[3]} & {df_sac.iloc[3,0]} & {df_sac.iloc[3,1]} & {df_sac.iloc[3,2]} & {df_sac.iloc[3,3]} & {df_sac.iloc[3,4]} & {df_sac.iloc[3,5]} \\\\
        \\hline
        {df_sac.index[4]} & {df_sac.iloc[4,0]} & {df_sac.iloc[4,1]} & {df_sac.iloc[4,2]} & {df_sac.iloc[4,3]} & {df_sac.iloc[4,4]} & {df_sac.iloc[4,5]} \\\\
        \\hline
        {df_sac.index[5]} & {df_sac.iloc[5,0]} & {df_sac.iloc[5,1]} & {df_sac.iloc[5,2]} & {df_sac.iloc[5,3]} & {df_sac.iloc[5,4]} & {df_sac.iloc[5,5]} \\\\
        \\hline
        {df_sac.index[6]} & {df_sac.iloc[6,0]} & {df_sac.iloc[6,1]} & {df_sac.iloc[6,2]} & {df_sac.iloc[6,3]} & {df_sac.iloc[6,4]} & {df_sac.iloc[6,5]} \\\\
        \\hline
        {df_sac.index[7]} & {df_sac.iloc[7,0]} & {df_sac.iloc[7,1]} & {df_sac.iloc[7,2]} & {df_sac.iloc[7,3]} & {df_sac.iloc[7,4]} & {df_sac.iloc[7,5]} \\\\
        \\hline
        {df_sac.index[8]} & {df_sac.iloc[8,0]} & {df_sac.iloc[8,1]} & {df_sac.iloc[8,2]} & {df_sac.iloc[8,3]} & {df_sac.iloc[8,4]} & {df_sac.iloc[8,5]} \\\\
        \\hline
        {df_sac.index[9]} & {df_sac.iloc[9,0]} & {df_sac.iloc[9,1]} & {df_sac.iloc[9,2]} & {df_sac.iloc[9,3]} & {df_sac.iloc[9,4]} & {df_sac.iloc[9,5]} \\\\
        \\hline
        {df_sac.index[10]} & {df_sac.iloc[10,0]} & {df_sac.iloc[10,1]} & {df_sac.iloc[10,2]} & {df_sac.iloc[10,3]} & {df_sac.iloc[10,4]} & {df_sac.iloc[10,5]} \\\\
        \\hline
        {df_sac.index[11]} & {df_sac.iloc[11,0]} & {df_sac.iloc[11,1]} & {df_sac.iloc[11,2]} & {df_sac.iloc[11,3]} & {df_sac.iloc[11,4]} & {df_sac.iloc[11,5]} \\\\
        \\hline
        {df_sac.index[12]} & {df_sac.iloc[12,0]} & {df_sac.iloc[12,1]} & {df_sac.iloc[12,2]} & {df_sac.iloc[12,3]} & {df_sac.iloc[12,4]} & {df_sac.iloc[12,5]} \\\\
        \\hline
        {df_sac.index[13]} & {df_sac.iloc[13,0]} & {df_sac.iloc[13,1]} & {df_sac.iloc[13,2]} & {df_sac.iloc[13,3]} & {df_sac.iloc[13,4]} & {df_sac.iloc[13,5]} \\\\
        \\hline
        {df_sac.index[14]} & {df_sac.iloc[14,0]} & {df_sac.iloc[14,1]} & {df_sac.iloc[14,2]} & {df_sac.iloc[14,3]} & {df_sac.iloc[14,4]} & {df_sac.iloc[14,5]} \\\\
        \\hline
        {df_sac.index[15]} & {df_sac.iloc[15,0]} & {df_sac.iloc[15,1]} & {df_sac.iloc[15,2]} & {df_sac.iloc[15,3]} & {df_sac.iloc[15,4]} & {df_sac.iloc[15,5]} \\\\
        \\hline
        {df_sac.index[16]} & {df_sac.iloc[16,0]} & {df_sac.iloc[16,1]} & {df_sac.iloc[16,2]} & {df_sac.iloc[16,3]} & {df_sac.iloc[16,4]} & {df_sac.iloc[16,5]} \\\\
        \\hline
        {df_sac.index[17]} & {df_sac.iloc[17,0]} & {df_sac.iloc[17,1]} & {df_sac.iloc[17,2]} & {df_sac.iloc[17,3]} & {df_sac.iloc[17,4]} & {df_sac.iloc[17,5]} \\\\
        \\hline
        {df_sac.index[18]} & {df_sac.iloc[18,0]} & {df_sac.iloc[18,1]} & {df_sac.iloc[18,2]} & {df_sac.iloc[18,3]} & {df_sac.iloc[18,4]} & {df_sac.iloc[18,5]} \\\\
        \\hline
        {df_sac.index[19]} & {df_sac.iloc[19,0]} & {df_sac.iloc[19,1]} & {df_sac.iloc[19,2]} & {df_sac.iloc[19,3]} & {df_sac.iloc[19,4]} & {df_sac.iloc[19,5]} \\\\
        \\hline
        {df_sac.index[20]} & {df_sac.iloc[20,0]} & {df_sac.iloc[20,1]} & {df_sac.iloc[20,2]} & {df_sac.iloc[20,3]} & {df_sac.iloc[20,4]} & {df_sac.iloc[20,5]} \\\\
        \\hline
        {df_sac.index[21]} & {df_sac.iloc[21,0]} & {df_sac.iloc[21,1]} & {df_sac.iloc[21,2]} & {df_sac.iloc[21,3]} & {df_sac.iloc[21,4]} & {df_sac.iloc[21,5]} \\\\
        \\hline
        {df_sac.index[22]} & {df_sac.iloc[22,0]} & {df_sac.iloc[22,1]} & {df_sac.iloc[22,2]} & {df_sac.iloc[22,3]} & {df_sac.iloc[22,4]} & {df_sac.iloc[22,5]} \\\\
        \\hline
        {df_sac.index[23]} & {df_sac.iloc[23,0]} & {df_sac.iloc[23,1]} & {df_sac.iloc[23,2]} & {df_sac.iloc[23,3]} & {df_sac.iloc[23,4]} & {df_sac.iloc[23,5]} \\\\
        \\hline
        {df_sac.index[24]} & {df_sac.iloc[24,0]} & {df_sac.iloc[24,1]} & {df_sac.iloc[24,2]} & {df_sac.iloc[24,3]} & {df_sac.iloc[24,4]} & {df_sac.iloc[24,5]} \\\\
        \\hline
        {df_sac.index[25]} & {df_sac.iloc[25,0]} & {df_sac.iloc[25,1]} & {df_sac.iloc[25,2]} & {df_sac.iloc[25,3]} & {df_sac.iloc[25,4]} & {df_sac.iloc[25,5]} \\\\
        \\hline
        {df_sac.index[26]} & {df_sac.iloc[26,0]} & {df_sac.iloc[26,1]} & {df_sac.iloc[26,2]} & {df_sac.iloc[26,3]} & {df_sac.iloc[26,4]} & {df_sac.iloc[26,5]} \\\\
        \\hline
        {df_sac.index[27]} & {df_sac.iloc[27,0]} & {df_sac.iloc[27,1]} & {df_sac.iloc[27,2]} & {df_sac.iloc[27,3]} & {df_sac.iloc[27,4]} & {df_sac.iloc[27,5]} \\\\
        \\hline
        {df_sac.index[28]} & {df_sac.iloc[28,0]} & {df_sac.iloc[28,1]} & {df_sac.iloc[28,2]} & {df_sac.iloc[28,3]} & {df_sac.iloc[28,4]} & {df_sac.iloc[28,5]} \\\\
        \\hline
    \\end{{tabular}}
    \\vspace{{-12pt}}
\\end{{table}}

\\begin{{itemize}}
    \\item Horário de disparo da previsão: 2021-03-04T00:00 (UTC).
    \\item Horários registrados pelo Tempo Coordenado Universal (UTC) / Hora Mundial.
    \\item Dados indexados no limite superior de tempo. Ex: Registro de 06:00 contém previsões de vazão média para período 00:01 a 06:00.
    \\item Simulações com Ensemble ECMWF - Conjunto de 51 forçantes.
\\end{{itemize}}

\\newpage
\\begin{{table}}[ht]
    \\centering
    \\caption{{Valores de vazão afluente média prevista - Modelo GR5i}}
    \\vspace{{6pt}}
    \\begin{{tabular}}{{|c|c|c|c|c|c|c|}}
        \\hline
        & \\multicolumn{{5}}{{|c|}}{{Simulação com chuva ECMWF}} & Simulação com \\\\
        \\hhline{{~-----~}}
        & Mínimo & Quantil 25 & Mediana & Quantil 75 & Máximo & chuva WRF \\\\
        \\hhline{{~------}}
        Hora & \\multicolumn{{6}}{{|c|}}{{Vazão Média Prevista (m3s-1)}} \\\\
        \\hline
        {df_gr5.index[0]} & {df_gr5.iloc[0,0]} & {df_gr5.iloc[0,1]} & {df_gr5.iloc[0,2]} & {df_gr5.iloc[0,3]} & {df_gr5.iloc[0,4]} & {df_gr5.iloc[0,5]} \\\\
        \\hline
        {df_gr5.index[1]} & {df_gr5.iloc[1,0]} & {df_gr5.iloc[1,1]} & {df_gr5.iloc[1,2]} & {df_gr5.iloc[1,3]} & {df_gr5.iloc[1,4]} & {df_gr5.iloc[1,5]} \\\\
        \\hline
        {df_gr5.index[2]} & {df_gr5.iloc[2,0]} & {df_gr5.iloc[2,1]} & {df_gr5.iloc[2,2]} & {df_gr5.iloc[2,3]} & {df_gr5.iloc[2,4]} & {df_gr5.iloc[2,5]} \\\\
        \\hline
        {df_gr5.index[3]} & {df_gr5.iloc[3,0]} & {df_gr5.iloc[3,1]} & {df_gr5.iloc[3,2]} & {df_gr5.iloc[3,3]} & {df_gr5.iloc[3,4]} & {df_gr5.iloc[3,5]} \\\\
        \\hline
        {df_gr5.index[4]} & {df_gr5.iloc[4,0]} & {df_gr5.iloc[4,1]} & {df_gr5.iloc[4,2]} & {df_gr5.iloc[4,3]} & {df_gr5.iloc[4,4]} & {df_gr5.iloc[4,5]} \\\\
        \\hline
        {df_gr5.index[5]} & {df_gr5.iloc[5,0]} & {df_gr5.iloc[5,1]} & {df_gr5.iloc[5,2]} & {df_gr5.iloc[5,3]} & {df_gr5.iloc[5,4]} & {df_gr5.iloc[5,5]} \\\\
        \\hline
        {df_gr5.index[6]} & {df_gr5.iloc[6,0]} & {df_gr5.iloc[6,1]} & {df_gr5.iloc[6,2]} & {df_gr5.iloc[6,3]} & {df_gr5.iloc[6,4]} & {df_gr5.iloc[6,5]} \\\\
        \\hline
        {df_gr5.index[7]} & {df_gr5.iloc[7,0]} & {df_gr5.iloc[7,1]} & {df_gr5.iloc[7,2]} & {df_gr5.iloc[7,3]} & {df_gr5.iloc[7,4]} & {df_gr5.iloc[7,5]} \\\\
        \\hline
        {df_gr5.index[8]} & {df_gr5.iloc[8,0]} & {df_gr5.iloc[8,1]} & {df_gr5.iloc[8,2]} & {df_gr5.iloc[8,3]} & {df_gr5.iloc[8,4]} & {df_gr5.iloc[8,5]} \\\\
        \\hline
        {df_gr5.index[9]} & {df_gr5.iloc[9,0]} & {df_gr5.iloc[9,1]} & {df_gr5.iloc[9,2]} & {df_gr5.iloc[9,3]} & {df_gr5.iloc[9,4]} & {df_gr5.iloc[9,5]} \\\\
        \\hline
        {df_gr5.index[10]} & {df_gr5.iloc[10,0]} & {df_gr5.iloc[10,1]} & {df_gr5.iloc[10,2]} & {df_gr5.iloc[10,3]} & {df_gr5.iloc[10,4]} & {df_gr5.iloc[10,5]} \\\\
        \\hline
        {df_gr5.index[11]} & {df_gr5.iloc[11,0]} & {df_gr5.iloc[11,1]} & {df_gr5.iloc[11,2]} & {df_gr5.iloc[11,3]} & {df_gr5.iloc[11,4]} & {df_gr5.iloc[11,5]} \\\\
        \\hline
        {df_gr5.index[12]} & {df_gr5.iloc[12,0]} & {df_gr5.iloc[12,1]} & {df_gr5.iloc[12,2]} & {df_gr5.iloc[12,3]} & {df_gr5.iloc[12,4]} & {df_gr5.iloc[12,5]} \\\\
        \\hline
        {df_gr5.index[13]} & {df_gr5.iloc[13,0]} & {df_gr5.iloc[13,1]} & {df_gr5.iloc[13,2]} & {df_gr5.iloc[13,3]} & {df_gr5.iloc[13,4]} & {df_gr5.iloc[13,5]} \\\\
        \\hline
        {df_gr5.index[14]} & {df_gr5.iloc[14,0]} & {df_gr5.iloc[14,1]} & {df_gr5.iloc[14,2]} & {df_gr5.iloc[14,3]} & {df_gr5.iloc[14,4]} & {df_gr5.iloc[14,5]} \\\\
        \\hline
        {df_gr5.index[15]} & {df_gr5.iloc[15,0]} & {df_gr5.iloc[15,1]} & {df_gr5.iloc[15,2]} & {df_gr5.iloc[15,3]} & {df_gr5.iloc[15,4]} & {df_gr5.iloc[15,5]} \\\\
        \\hline
        {df_gr5.index[16]} & {df_gr5.iloc[16,0]} & {df_gr5.iloc[16,1]} & {df_gr5.iloc[16,2]} & {df_gr5.iloc[16,3]} & {df_gr5.iloc[16,4]} & {df_gr5.iloc[16,5]} \\\\
        \\hline
        {df_gr5.index[17]} & {df_gr5.iloc[17,0]} & {df_gr5.iloc[17,1]} & {df_gr5.iloc[17,2]} & {df_gr5.iloc[17,3]} & {df_gr5.iloc[17,4]} & {df_gr5.iloc[17,5]} \\\\
        \\hline
        {df_gr5.index[18]} & {df_gr5.iloc[18,0]} & {df_gr5.iloc[18,1]} & {df_gr5.iloc[18,2]} & {df_gr5.iloc[18,3]} & {df_gr5.iloc[18,4]} & {df_gr5.iloc[18,5]} \\\\
        \\hline
        {df_gr5.index[19]} & {df_gr5.iloc[19,0]} & {df_gr5.iloc[19,1]} & {df_gr5.iloc[19,2]} & {df_gr5.iloc[19,3]} & {df_gr5.iloc[19,4]} & {df_gr5.iloc[19,5]} \\\\
        \\hline
        {df_gr5.index[20]} & {df_gr5.iloc[20,0]} & {df_gr5.iloc[20,1]} & {df_gr5.iloc[20,2]} & {df_gr5.iloc[20,3]} & {df_gr5.iloc[20,4]} & {df_gr5.iloc[20,5]} \\\\
        \\hline
        {df_gr5.index[21]} & {df_gr5.iloc[21,0]} & {df_gr5.iloc[21,1]} & {df_gr5.iloc[21,2]} & {df_gr5.iloc[21,3]} & {df_gr5.iloc[21,4]} & {df_gr5.iloc[21,5]} \\\\
        \\hline
        {df_gr5.index[22]} & {df_gr5.iloc[22,0]} & {df_gr5.iloc[22,1]} & {df_gr5.iloc[22,2]} & {df_gr5.iloc[22,3]} & {df_gr5.iloc[22,4]} & {df_gr5.iloc[22,5]} \\\\
        \\hline
        {df_gr5.index[23]} & {df_gr5.iloc[23,0]} & {df_gr5.iloc[23,1]} & {df_gr5.iloc[23,2]} & {df_gr5.iloc[23,3]} & {df_gr5.iloc[23,4]} & {df_gr5.iloc[23,5]} \\\\
        \\hline
        {df_gr5.index[24]} & {df_gr5.iloc[24,0]} & {df_gr5.iloc[24,1]} & {df_gr5.iloc[24,2]} & {df_gr5.iloc[24,3]} & {df_gr5.iloc[24,4]} & {df_gr5.iloc[24,5]} \\\\
        \\hline
        {df_gr5.index[25]} & {df_gr5.iloc[25,0]} & {df_gr5.iloc[25,1]} & {df_gr5.iloc[25,2]} & {df_gr5.iloc[25,3]} & {df_gr5.iloc[25,4]} & {df_gr5.iloc[25,5]} \\\\
        \\hline
        {df_gr5.index[26]} & {df_gr5.iloc[26,0]} & {df_gr5.iloc[26,1]} & {df_gr5.iloc[26,2]} & {df_gr5.iloc[26,3]} & {df_gr5.iloc[26,4]} & {df_gr5.iloc[26,5]} \\\\
        \\hline
        {df_gr5.index[27]} & {df_gr5.iloc[27,0]} & {df_gr5.iloc[27,1]} & {df_gr5.iloc[27,2]} & {df_gr5.iloc[27,3]} & {df_gr5.iloc[27,4]} & {df_gr5.iloc[27,5]} \\\\
        \\hline
        {df_gr5.index[28]} & {df_gr5.iloc[28,0]} & {df_gr5.iloc[28,1]} & {df_gr5.iloc[28,2]} & {df_gr5.iloc[28,3]} & {df_gr5.iloc[28,4]} & {df_gr5.iloc[28,5]} \\\\
        \\hline
    \\end{{tabular}}
    \\vspace{{-12pt}}
\\end{{table}}

\\begin{{itemize}}
    \\item Horário de disparo da previsão: 2021-03-04T00:00 (UTC).
    \\item Horários registrados pelo Tempo Coordenado Universal (UTC) / Hora Mundial.
    \\item Dados indexados no limite superior de tempo. Ex: Registro de 06:00 contém previsões de vazão média para período 00:01 a 06:00.
    \\item Simulações com Ensemble ECMWF - Conjunto de 51 forçantes.
\\end{{itemize}}

\\end{{document}}
''')
script.close()

## PREPARA PDF
os.chdir("../Boletim")
os.system(f'scp -r ../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_sac_{ano:04d}{mes:02d}{dia:02d}00.png .')
os.system(f'scp -r ../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/fig_gr5i_{ano:04d}{mes:02d}{dia:02d}00.png .')
os.system('pdflatex boletim.tex') ##essa parte do lixo nao tenho certeza
os.system(f'mv boletim.pdf ../Simulacoes/{ano:04d}_{mes:02d}_{dia:02d}_00/bol_{ano:04d}{mes:02d}{dia:02d}.pdf')
os.system(f'rm -r fig_sac_{ano:04d}{mes:02d}{dia:02d}00.png')
os.system(f'rm -r fig_gr5i_{ano:04d}{mes:02d}{dia:02d}00.png')
os.system('rm -r  boletim.log')
os.system('rm -r  boletim.aux')
