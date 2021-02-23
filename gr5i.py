'''
--------------------------------------------------------------------------------
Modelo GR5i
--------------------------------------------------------------------------------
Implementacao - Bruno Juliani, jan/2021
Modificação do modelo GR4J implementado por Arlan Scortegagna
--------------------------------------------------------------------------------
Forcantes:
    PME - numpy.array 1D contendo a precipitacao medial espacial (mm)
    ETP - numpy.array 1D contendo a evapotranspiracao potencial (mm)
--------------------------------------------------------------------------------
Parametros:
    dt - passo de tempo (hrs)
    x1 - capacidade do reservatorio de producao (mm)
    x2 - coeficiente de troca de água c/ aquifero (mm/dt)
    x3 - capacidade de referência do reservatorio de propagacao (mm)
    x4 - tempo de base dos HUs (proporcional a dt)
    x5 - parâmetro relacionado a troca c/ aquifero (valor limite em que função
            de troca muda de sinal - entre 0 e 1)
--------------------------------------------------------------------------------
Variaveis de Estado :
    I - armazenamento do reservatório de interceptação (mm)
    S - armazenamento do reservatorio de producao (mm)
    R - armazenamento do reservatorio de propagacao (mm)
    HU1 - numpy.array 1D contendo os estados iniciais do HU 1 (mm)
    HU2 - numpy.array 1D contendo os estados iniciais do HU 1 (mm)
--------------------------------------------------------------------------------
Outros:
    area - area da bacia em km2 para conversao mm->m3/s (parametro constante)
    dt - passo de tempo (horas)
--------------------------------------------------------------------------------
Observações e recomendações:
    O equacionamento está de forma a possibilitar a aplicação para passos de
    tempo sub-diarios, dt.
    Para dt = 1 dia é recomendado capacidade de interceptação igual a zero.

--------------------------------------------------------------------------------

'''
import numpy as np

def ordenadas_HU1(x4, D):
    n = int(np.ceil(x4))
    SH1 = np.zeros(n+1)
    for t in range(0, n+1):
        if (t<=0):
            SH1[t] = 0
        elif (t>0) & (t<x4):
            SH1[t] = (t/x4)**D
        else:
            SH1[t] = 1
    OrdHU1 = np.diff(SH1)
    return OrdHU1, n


def ordenadas_HU2(x4, D):
    m = int(np.ceil(2*x4))
    SH2 = np.zeros(m+1)
    for t in range(0, m+1):
        if (t<=0):
            SH2[t] = 0
        elif (t>0) & (t<=x4):
            SH2[t] = (1/2)*(t/x4)**D
        elif (t>x4) & (t<2*x4):
            SH2[t] = 1 - (1/2)*(2-t/x4)**D
        else:
            SH2[t] = 1
    OrdHU2 = np.diff(SH2)
    return OrdHU2, m


def simulacao(dt,area, PME, ETP, Qmon, x1, x2, x3, x4, x5, Estados=None):
    '''
    Variaveis internas
        Imax = capacidade maxima de interceptacao
        P1 - altura de precipitacao do passo de tempo
        E  - altura de evapotranspiracao potencial do passo de tempo
        Pn - precipitacao liquida
        En - evapotranspiracao potencial liquida
        Ps - montante de precipitacao que entra no reservatorio de SMA
        Es - montante que sai por evapotranspiracao do reservatorio de SMA
        Perc - montante percolado
        Pr - 'precipitacao efetiva' (na verdade, considera tb o PERC)
    '''

    # Constantes (passiveis de analise e estudo de caso)
    power = 4
    split = 0.9
    D     = 2.50 # p/ modelos horarios, D = 1.25 (ver Ficchi, 2017, p. 51)
    beta  = 5.25*(1/dt)**0.25

    # Calcula as ordenadas do HUs
    OrdHU1, n = ordenadas_HU1(x4, D)
    OrdHU2, m = ordenadas_HU2(x4, D)

    #Cálculo Interceptacao Maxima
    I = 0
    I_list = []
    for P1, E in np.nditer([PME,ETP]):
        #Perda de interceptao
        Ei = min(E, P1 + I)
        #Capacidade de evapotranspiracao
        En = E - Ei
        #Precipitacao efetiva
        Pn = P1 - Ei
        #Atualiza Interceptacao
        I = I + (P1 - Ei - Pn)
        I_list.append(I)
    Imax = max(I_list)

    # Atribui os estados iniciais
    if Estados is None:
        Estados = {}
    S = Estados.get('S', 0.6*x1)
    R = Estados.get('R', 0.7*x3)
    I = 0
    HU1 = Estados.get('HU1', np.zeros(n))
    HU2 = Estados.get('HU2', np.zeros(m))


    # Executa o processo iterativo
    Q = np.array([], float)
    Ps = 0
    for P1, E, Qm in np.nditer([PME,ETP,Qmon]):

        #INTERCEPTACAO
        #Perda de interceptao
        Ei = min(E, P1 + I)
        #Capacidade de evapotranspiracao
        En = E - Ei
        #Precipitacao efetiva
        Pn = P1 - Ei
        Pth = max(0, P1 - (Imax - I) - Ei)
        #Atualiza Interceptacao
        I = I + (P1 - Ei - Pn)

        #VAZAO MONTANTE
        #Soma vazao de montante ao reservatorio inicial
        Qmt = Qm*((3.6*dt)/area)
        S = S + Qmt

        #PRODUCAO
        #Chuva e evapotranspiracao real
        if En > 0:
            #tangente hiperbolica tende a 1 (arredondamento p/ x > 13)
            TWS = 1 if En/x1 > 13 else np.tanh(En/x1)
            Es = S*(2 - S/x1)*TWS / (1 + (1 - S/x1)*TWS)
            S = S - Es
            Pr = 0 # (manter pq depois vai somar com o Perc)
        else:
            #tangente hiperbolica tende a 1 (arredondamento p/ x > 13)
            TWS = 1 if Pth/x1 > 13 else np.tanh(Pth/x1)
            Ps = x1*(1 - (S/x1)**2)*TWS / (1 + (S/x1)*TWS)
            S = S + Ps
            Pr = Pn - Ps

        #Percolacao
        Perc = S*(1 - (1 + (S/(beta*x1))**power)**(-1/4))
        S = S - Perc

        #Routed water amount
        Pr += Perc

        #HIDROGRAMAS UNITARIOS
        # Convolucao do HU1
        HU1 += OrdHU1*(Pr*split)
        Q9 = HU1[0]
        HU1 = np.roll(HU1, -1)
        HU1[-1] = 0

        # Convolucao do HU2
        HU2 += OrdHU2*(Pr*(1-split))
        Q1 = HU2[0]
        HU2 = np.roll(HU2, -1)
        HU2[-1] = 0

        #TROCA COM AQUIFERO
        # Troca potencial com o aquifero (ganho ou perda)
        F = x2*((R/x3) - x5)
        if F > 0:
            F = 2*F
        else:
            F = -(min(abs(F), R + Q9) + min(abs(F), Q1))

        #ROUTING STORE
        # Atualiza o reservatorio de propagacao com output do HU1 (Q9)
        # Atualiza reservatorio de propagacao com troca c aquifero
        R = max(0, R + Q9 + F)
        Qr = R*(1 - (1 + (R/x3)**power)**(-1/4))
        R = R - Qr

        #ESCOAMENTO PSEUDO-DIRETO
        # Componente de escoamento pseudo-direto provem do HU2 (Q1)
        # Atualiza escoamento com troca c aquifero
        Qd = max(0, Q1 + F)

        #VAZAO SIMULADA
        Q = np.append(Q, Qr + Qd)

    #TRANSFORMA MM EM M3/S
    Q = Q*(area/(3.6*dt))

    return Q
