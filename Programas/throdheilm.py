#!/usr/bin/python2
# -*- coding: utf-8 -*-

""" Este programa reúne as diversas informações que devem ser apresentadas no boletim diário do SPAupc, elabora o
gráfico de previsão de vazão e gera o arquivo .tex que dará origem ao boletim final em PDF. """
from sys import path as locais
locais.append('/simepar/hidro/SPAupc/Python/')
from sys import argv
from os import system, putenv, listdir
from datetime import date, timedelta
from informacoes_PC import info_bacia
from funcoes_PC import DataReferencia, xdate

#system('export GDFONTPATH=/usr/share/fonts/truetype/msttcorefonts')
putenv('GDFONTPATH','/usr/share/fonts/truetype/msttcorefonts')



# 0 - Argumentos OPCIONAIS de entrada
#-----------------------------------------------------------------------------------------------------------------------
# Inicializando valores padrões das variáveis de opção
OpcPlot = True        # Opção de plotagem: O programa irá se encarregar de gerar a figura com o gráfico de previsão
if '-p' in argv: OpcPlot = False    # A figura do gráfico deverá ser gerada antes da execução deste programa
#-----------------------------------------------------------------------------------------------------------------------




# 1 - Data de referência (dia até onde devem haver dados observados às 7 e 17 horas) e dicionário com todos os dados
#para o gráfico
#-----------------------------------------------------------------------------------------------------------------------
dRef = DataReferencia()
dados = {}
for i in range(-5,6):
    dados[dRef+timedelta(days=i)] = [-999.99 for j in range(5)]
datas = dados.keys();    datas.sort()
#-----------------------------------------------------------------------------------------------------------------------




# 2 - Dados de cota e vazão nos postos de afluência direta
#-----------------------------------------------------------------------------------------------------------------------
""" Os dados de cota e vazão média diária são obtidos dos arquivos gerados no diretório Dados2, sendo armazenado apenas
os valores para a data de referência, e para os três postos utilizados na contabilidade da vazão afluente para o reser-
-vatório."""
postos = [ ['Ponte Rio Branco',   3, -99.99, -999.99],
           ['Ponte Rio Paratigi', 4, -99.99, -999.99],
           ['Argoim',             8, -99.99, -999.99] ]
           #['Ponte Paraguaçu',    8, -99.99, -999.99] ]

print ('\n     __________POSTO_____  ____COTA ___VAZAO')
for i in range(3):

    # Arquivo de dados de cota e vazão média diária.
    arq = open(str('/simepar/hidro/SPAupc/Operacao/Dados2/cotavazao_%.1i.txt' % postos[i][1]), 'r')
    ctd = arq.readlines()
    arq.close()

    # Armazenando dados na data de referência.
    for j in range(len(ctd)-1,-1,-1):
        if len(ctd[j]) <= 1:
            continue

        dt = xdate(ctd[j])
        if dt == dRef:
            postos[i][2] = float(ctd[j].split()[-2])
            postos[i][3] = float(ctd[j].split()[-1])

    print ('     %20s %8.2f %8.2f' % (postos[i][0], postos[i][2], postos[i][3]))
print ('     --------------------  -------- --------')
#-----------------------------------------------------------------------------------------------------------------------




# 3 - Dados observados nos últimos de vazão afluente para o reservatório e chuva média em toda a bacia
#-----------------------------------------------------------------------------------------------------------------------
""" No arquivo ECV da sub-bacia 9 os dados na coluna de vazão de montante são o próprio registro da vazão afluente
para o reservatório. """
arq = open('/simepar/hidro/SPAupc/Operacao/ECVs/ecv9.txt', 'r')
arq.seek(-470,2)    #Supostamente irá retroceder 470 caracteres a partir do final do arquivo, o que deve cair no
                    #início da 10ª linha do arquivo, de trás para frente.
ctd = arq.readlines()
for l in ctd:
    dt = xdate(l)
    if dt in datas[:6]:
        dados[dt][0] = float(l.split()[5])
        if dt == dRef:      #Na data de referência os valores de previsão recebem os valores observados
            dados[dt][1], dados[dt][2] = dados[dt][0], dados[dt][0]
arq.close()

arq = open('/simepar/hidro/SPAupc/Operacao/ECVs/hist_cmb_51.txt', 'r')
arq.seek(-190,2)    #Indo para a 10ª linha anterior à linha final do arquivo de histórico de chuva média
ctd = arq.readlines()
for l in ctd:
    dt = xdate(l)
    if dt in datas[:6]:
        dados[dt][3] = float(l.split()[3])
        if dt == dRef:      #Na data de referência os valores de previsão recebem os valores observados
            dados[dt][4] = dados[dt][3]
arq.close()
#-----------------------------------------------------------------------------------------------------------------------





# 4 - Chuva média prevista nas sub-bacias
#-----------------------------------------------------------------------------------------------------------------------
""" Os dados de chuva média prevista para as 9 sub-bacias do SPAupc são obtidas nos arquivos presentes no diretório
Prev_CMB. Será assumido um valor nulo para dados faltantes de chuva prevista. """
prch = [[0.0,0.0,0.0,0.0,0.0] for i in range(9)]

# Laço para executar a leitura dos dados das sub-bacias 1 a 9.
for bac in range(1,10):

    # Arquivo de dados de previsão de cmb
    arq = open(str('/simepar/hidro/SPAupc/Operacao/Prev_CMB/prevcmb_%1i.txt' % bac), 'r')

    for line in arq.readlines():
        dt = xdate(line)
        if dt in datas[6:]:
            prch[bac-1][datas.index(dt)-6] = float(line.split()[-1])

    arq.close()

# Acompanhado resultados na tela
print ('\n     #BAC _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i' % (\
    datas[6].day, datas[6].month, datas[7].day, datas[7].month, datas[8].day, datas[8].month, \
    datas[9].day, datas[9].month, datas[10].day, datas[10].month) )
for bac in range(1,10):
    print ('     %4.1i %6.2f %6.2f %6.2f %6.2f %6.2f' % (bac, prch[bac-1][0], prch[bac-1][1], \
        prch[bac-1][2], prch[bac-1][3], prch[bac-1][4]) )
print ('     ---- ------ ------ ------ ------ ------')
#-----------------------------------------------------------------------------------------------------------------------




# 5 - Previsão de vazão afluente média diária e chuva média em toda a bacia
#-----------------------------------------------------------------------------------------------------------------------
""" Os dados de vazão afluente prevista para o reservatório da UHEPC são obtidas no arquivo de resultados da simulação
presentes no diretório Result2bol, tal como as médias de chuva para toda a bacia contribuinte para o reservatório. Devem
haver dados de previsão para os cinco dias posteriores ao dia de referência."""
# Arquivo de dados de previsão de vazão afluente
arq = open('/simepar/hidro/SPAupc/Operacao/Boletim/Result2bol/' + \
    str('%4i%2.2i%2.2i_PR9.txt' % (dRef.year,dRef.month,dRef.day)), 'r')

for line in arq.readlines():
    if line[0] == '#' or len(line) < 10: continue

    dt = xdate(line)
    if dt in datas[6:]:
        line = line.split()
        dados[dt][1], dados[dt][2], dados[dt][4] = float(line[1]), float(line[2]), float(line[3])

arq.close()

# Acompanhado resultados na tela
print ('\n     #CENARIO _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i _%2.2i/%2.2i' % (\
    datas[6].day, datas[6].month, datas[7].day, datas[7].month, datas[8].day, datas[8].month, \
    datas[9].day, datas[9].month, datas[10].day, datas[10].month) )
print '      S/Chuva',
print ('%6.2f %6.2f %6.2f %6.2f %6.2f' % tuple(dados[dt][1] for dt in datas[6:]))
print '      C/Chuva',
print ('%6.2f %6.2f %6.2f %6.2f %6.2f' % tuple(dados[dt][2] for dt in datas[6:]))
print ('     -------- ------ ------ ------ ------ ------')
#-----------------------------------------------------------------------------------------------------------------------




# 6 - Gravando dados que serão utilizados no gráfico da previsão
#-----------------------------------------------------------------------------------------------------------------------
arq = open('dados.txt', 'w')
for dt in datas:
    arq.write('%s' % dt)
    for i in range(5):
        if i <= 2:
            var = round(dados[dt][i],1)
            if var < -900: var = -999.99
        else:
            var = dados[dt][i]
        arq.write(' %7.2f' % var)
    arq.write('\n')
arq.close()
#-----------------------------------------------------------------------------------------------------------------------




# 7 - Gráfico da previsão de vazão afluente e chuva média em toda a bacia contribuinte
#-----------------------------------------------------------------------------------------------------------------------
if OpcPlot:
    """ Primeiro é preciso encontrar os maiores registros de chuva e vazão, observada ou prevista, para determinar o
    range dos eixos Y dos gráficos de chuva e vazão. """
    Vmax = max([max(dados[dt][0:3]) for dt in datas]) * 1.1
    Cmax = max([max(dados[dt][3:5]) for dt in datas]) * 1.1
    if Cmax < 2.0:
	Cmax = 2.0
    if Vmax < 5.0:
        Vmax = 5.0

    # Arquivo com o script GnuPlot
    script = open('/simepar/hidro/SPAupc/Operacao/Boletim/plot_boletim.gnu', 'w')

    # Configurações gerais do arquivo de imagem
    script.write("""
    reset
    set terminal png font times 21 size 1440, 900
    set output '/simepar/hidro/SPAupc/Operacao/Boletim/afluencias.png'

    set multiplot\n\n""")

    # Posicionamento do gráfico de vazão e especificação do eixo X para o formato de data
    script.write("""
    # Vazão
    reset
    set origin 0.0, 0.0
    set size 0.98, 0.71
    unset title

    set lmargin 10
    set key below box
    set grid
    set datafile missing '-999.99'

    set xdata time
    set timefmt '%Y-%m-%d'
    set format x '%d/%m'\n\n""")

    # Ajustando eixo X para formato de data
    script.write("""
    set xrange['%s':'%s']
    set xtics 86400 scale 1, 0
    set ylabel 'Vazão Diária Média [m3/s]'
    set yrange[0:%.0f]\n\n""" % (dRef-timedelta(days=5), dRef+timedelta(days=5), Vmax))

    # Comando plot
    script.write("""
    plot 'dados.txt' using 1:($3) title 'Prev. Zero' with line lt 1 lw 5 ,\\
    'dados.txt' using 1:($4) title 'Prev. Mod' with line lt 3 lw 5 ,\\
    'dados.txt' using 1:($2) title 'Observado' with line lt -1 lw 5
    \n\n""")

    # Ajustando parte da figura onde ficará o gráfico de chuva.
    script.write("""
    # Chuva
    set origin 0.0, 0.71
    set size 0.98, 0.31

    set format x ''
    set ylabel 'Chuva [mm]'
    set yrange[0:%.1f] reverse
    """ % Cmax)
    if int(Cmax*10) <= 25:
        script.write('set ytics 0.5')
    else:
        script.write('set ytics %.0f' % (round(Cmax*0.25,0)))
    script.write("""
    set grid xtics ytics lc rgb '#B2B2B2' lt 0 lw 1

    set boxwidth 12*3600
    set lmargin 10
    unset key\n""")

    # Dados para plotagem e opções do desenho no gráfico
    script.write("""
    plot 'dados.txt' using 1:($6) notitle with boxes fs pattern 4 lt 3 ,\\
    'dados.txt' using 1:($5) notitle with boxes fs solid 0.75 lt -1

    unset multiplot\n""")

    # Executando o script para gerar o gráfico
    script.close()
    system('gnuplot plot_boletim.gnu')

    print '\n     Gerou gráfico de previsão.'
#-----------------------------------------------------------------------------------------------------------------------




# 8 - Script LaTeX para o boletim de previsão.
#-----------------------------------------------------------------------------------------------------------------------
# Função para transformar real em string usando virgula como separador de decimal
def trsv(val):
    return str('%7.1f' % val).replace('.',',')

def trsv2(val):
    return str('%7.2f' % val).replace('.',',')

# Arquivo TEX ("e ajuste da data de referência pelo padrão da UHE PC"  <- Não mais! Mesma dRef a partir de 13/01/2011)
script = open('/simepar/hidro/SPAupc/Operacao/Boletim/LaTeX/boletim.tex','w')
#dRef   = dRef + timedelta(days = 1)

# Preâmbulo do LaTeX, Cabeçalho e data do boletim.
script.write("""%% Papel A4, fonte Times tamanho 12
\\documentclass[a4paper,12pt]{article}

%% Determinando tamanhos de margens
\\usepackage[left=2cm, right=2cm, top=3cm, bottom=0.5cm]{geometry}

%% Preâmbulo para documentos em português
\\usepackage[portuguese]{babel}     %% Idioma do texto (regras de hifenização e textos automáticos i.e. Figura, Tabela)
\\usepackage[utf8]{inputenc}     %% Codificação do texto (caracteres especiais)
\\usepackage[T1]{fontenc}          %% Operações de fontes (tipo, tamanho, etc.)

\\usepackage[pdftex]{graphicx}     %% Pacote para inclusão de imagens PNG, JPEG e PDF
\\usepackage{color}                %% Pacote para utilizar texto colorido
\\usepackage{fancyhdr}             %% Cabecário com figura



\\begin{document}

\\pagestyle{fancy}
\\fancyhead{}    %% Limpa cabeçalho
\\fancyfoot{}    %% Limpa rodapé
\\fancyhead[R]{\\includegraphics[width = 4cm]{/simepar/hidro/SPAupc/Operacao/Boletim/logo_simepar.png}}

\\begin{center}  %% Título e data do boletim
\\Large{\\textbf{\\textcolor{blue}{VOTORANTIM}}}

\\vspace{12pt}

\\begin{tabular}{| l | c |}
\\hline
 & \\textbf{\\Large{Sistema de Previsão de Afluência}} \\\\
 \\raisebox{1.2ex}[0pt][0pt] {\\textbf{\\huge{$SPA_{UPC}$}}} & \\textbf{\\Large{Usina hidrelétrica Pedra do Cavalo}} \\\\
\\hline
\\end{tabular}

\\vspace{24pt}

\\textbf{\\large{%2.2i/%2.2i/%4i}}
\\end{center}

\\vspace{24pt} %% SITUAÇÃO ATUAL

\\textbf{\\large{Situação Atual}}

\\vspace{2pt}\n""" % (dRef.day, dRef.month, dRef.year))

# Tabela 1: Dados do monitoramento fluviométrico
script.write("""
\\begin{table}[h]    % Tabela de dados observados nos postos de afluência
\\begin{center}
\\caption{Dados do monitoramento fluviométrico (média diária)}
\\begin{tabular}{l c c}
\\hline
\\multicolumn{1}{c}{\\textbf{Posto de monitoramento}} & \\textbf{Nível (m)} & \\textbf{Vazão (m$^{3}$/s)} \\\\
\\hline""")

#ms: ajusta boletim em caso de falha nos dados
#script.write('\nPonte Rio Branco                & %s & %s \\\\' % (trsv2(postos[0][2]), trsv(postos[0][3])))
#script.write('\nPonte Rio Paratigi              & %s & %s \\\\' % (trsv2(postos[1][2]), trsv(postos[1][3])))
#script.write('\nArgoim                          & %s & %s \\\\' % (trsv2(postos[2][2]), trsv(postos[2][3])))
## script.write('\nPonte Paraguaçu                 & %s & %s \\\\' % (trsv(postos[2][2]), trsv(postos[2][3])))
#aux = 1.06*postos[0][3] + 1.35*postos[1][3] + 1.02*postos[2][3]
#script.write('\nAfluência UHE Pedra do Cavalo   &         & %s \\\\' % trsv(aux))

if (postos[0][2]>=0.):
    script.write('\nPonte Rio Branco                & %s & %s \\\\' % (trsv2(postos[0][2]), trsv(postos[0][3])))
else:
    script.write('\nPonte Rio Branco                & %s & %s \\\\' % ('Sem dados', 'Sem dados'))

if (postos[1][2]>=0.):
    script.write('\nPonte Rio Paratigi              & %s & %s \\\\' % (trsv2(postos[1][2]), trsv(postos[1][3])))
else:
    script.write('\nPonte Rio Paratigi              & %s & %s \\\\' % ('Sem dados', 'Sem dados'))

if (postos[2][2]>=0.):
    script.write('\nArgoim                          & %s & %s \\\\' % (trsv2(postos[2][2]), trsv(postos[2][3])))
else:
    script.write('\nArgoim                          & %s & %s \\\\' % ('Sem dados', 'Sem dados'))

if (postos[0][2]>=0. and postos[1][2]>=0. and postos[2][2]>=0.):
    aux = 1.06*postos[0][3] + 1.35*postos[1][3] + 1.02*postos[2][3]
    script.write('\nAfluência UHE Pedra do Cavalo   &         & %s \\\\' % trsv(aux))
else:
    script.write('\nAfluência UHE Pedra do Cavalo   &         & %s \\\\' % ('Sem dados'))

script.write("""
\\hline
\\end{tabular}
\\end{center}
\\end{table}\n""")

# Figura 1: Mapa da chuva média na bacia
script.write("""
\\begin{figure}[!h]    % Figura de chuva média na bacia
\\includegraphics[angle=90, width = 1.0\\textwidth]{/simepar/hidro/SPAupc/Operacao/Mapas_De_Chuvas/mapa_cmb.pdf}
\\caption{Mapa da distribuição espacial da chuva média nas sub-bacias}
\\end{figure}\n""")

# Seção de previsão e gráfico de previsão de vazão
script.write("""
\\newpage    % Previsão Hidrometeorológica

\\pagestyle{empty}
\\voffset = 0pt
\\headheight = 0pt
\\headsep = 0pt
\\footskip = 0pt

\\textbf{\\large{Previsão Hidrometeorológica}}


\\begin{figure}[h!]    % Figura da previsão de vazão
\\includegraphics[width = 1.0\\textwidth]{/simepar/hidro/SPAupc/Operacao/Boletim/afluencias.png}
\\caption{Gráfico da previsão de afluência para o reservatório}
\\end{figure}\n""")

# Tabela 2: Valores de vazão afluente média prevista
script.write("""
\\begin{table}[h!]     % Tabela com os dados de vazão afluente prevista
\\begin{center}
\\caption{Valores de vazão afluente média prevista}
\\begin{tabular}{c c c}
\\hline
\\textbf{Data} & \\multicolumn{2}{c}{\\textbf{Vazão (m$^{3}$/s)}} \\\\
\\cline{2-3}
              & \\textbf{Chuva Zero} & \\textbf{Chuva Modelo} \\\\
\\hline""")

for dt in datas[6:]:
    script.write('\n%2.2i/%2.2i/%4i & %7s & %7s \\\\' % (dt.day, dt.month, dt.year, trsv(dados[dt][1]), trsv(dados[dt][2])))

script.write("""
\\hline
\\end{tabular}
\\end{center}
\\end{table}\n""")

# Tabela 3: Valores de chuva média prevista em cada sub-bacia (mm/dia)
script.write("""
\\vspace{-12pt}

\\begin{table}[h!]     % Tabela com os dados de chuva prevista
\\begin{center}
\\caption{Valores de chuva média prevista em cada sub-bacia (mm/dia)}
\\begin{tabular}{l c c c c c c}
\\hline
\\multicolumn{1}{c}{\\textbf{Sub-Bacia}}""")

for dt in datas[6:]:
    script.write(' & \\textbf{%2.2i/%2.2i}' % (dt.day, dt.month))
script.write(' \\\\\n\\hline')

for bac in range(1,10):
    script.write('\nB%1i - %s' % (bac, info_bacia(bac,'Nome')))
    for i in range(5):
        script.write(' & %s' % trsv(prch[bac-1][i]))
    script.write(' \\\\')

script.write("""
\\hline
\\end{tabular}
\\end{center}
\\end{table}

%\\vspace{12pt}

%\\textbf{\\large{Observações}}

%\\vspace{12pt}

%<observações>

\\end{document}\n""")

# Acionando o LaTeX para gerar o arquivo PDF do boletim
script.close()
print '\n\n', '-'*120
system('pdflatex LaTeX/boletim.tex > lixoTeX.txt')
system('pdflatex LaTeX/boletim.tex >> lixoTeX.txt')
print '-'*120, '\n'
system('mv boletim.log boletim.aux boletim.pdf LaTeX/')

print '\n     Gerou Arquivo PDF do boletim.'

# Renomeando boletim a data de referência estiver entre domingo e quinta
#if dRef.weekday() <= 3 or dRef.weekday() == 6:
system( str('mv LaTeX/boletim.pdf bol_uhepc_%s.pdf' % dRef) )
system( str('cp bol_uhepc_%s.pdf /simepar/hidro/webdocs/spaupc/pdfs/' % dRef) )
#-----------------------------------------------------------------------------------------------------------------------




# 9 - Atualizando previsão do hidrólogo e lista de boletins disponíveis no site
#-----------------------------------------------------------------------------------------------------------------------
# Atualizando resultados da previsão do hidrólogo no site do SPAupc
if '-wu' not in argv: # -wu não é utilizado na chamada do boletim (bol) -> abreBolResult.py
    system('python2 ../WebUpdate/2-previsoesAtuais.py')

# Listando boletins
lista = listdir('/simepar/hidro/webdocs/spaupc/pdfs')
lista.remove('listaboletins.json')
datasbol = []

for b in lista:
    try:
        datasbol.append(date(int(b[10:14]), int(b[15:17]), int(b[18:20])))
    except:
        pass

datasbol.sort(reverse = True)

arq = open('/simepar/hidro/webdocs/spaupc/pdfs/listaboletins.json', 'w')
for i in range(len(datasbol)):

    if i == 0:
        arq.write('["%s"' % datasbol[i])
    else:
        arq.write(',"%s"' % datasbol[i])

arq.write(']')
arq.close()



print '\n\n\nokular bol_uhepc_%s.pdf &' % dRef
print '\n./envia_boletim.py %i %i %i\n\n\n' % (dRef.year, dRef.month, dRef.day)




# The way it's gonna be
