'''
--------------------------------------------------------------------------------
Modelo Sacramento Soil Moisture Accounting (SAC-SMA)
+ Muskingum para progacao de Qmon
--------------------------------------------------------------------------------
Implementacao - Arlan Scortegagna, fev/2021
Ultima atualizacao - Arlan Scortegagna, abr/2021
--------------------------------------------------------------------------------
'''

import pandas as pd
import numpy as np
from scipy import stats
from collections import OrderedDict


# Limites dos parametros (a ordem nao importa, se manter essa estrutura com os nomes)
X = (
        ('UZTWM', 10, 300),
        ('UZFWM', 5, 150),
        ('LZTWM', 10, 500),
        ('LZFPM', 10, 1000),
        ('LZFSM', 5, 400),
        ('UZK', 0.1, 0.75),
        ('LZPK', 0.001, 0.05),
        ('LZSK', 0.01, 0.35),
        ('ADIMP', 0, 0.2),
        ('PCTIM', 0, 0.2),
        ('ZPERC', 1, 350),
        ('REXP', 1, 5),
        ('PFREE', 0, 0.8),
        ('NUH', 0.5, 4),
        ('KUH', 1, 6),
        ('NMSK', 1, 3),
        ('KMSK', 0.5, 3),
        ('XMSK', 0.05, 0.49))
Xnomes = [i[0] for i in X]
Xmin = [i[1] for i in X]
Xmax = [i[2] for i in X]


# [OrderedDict((k, d[k](v)) for (k, v) in l.iteritems()) for l in L]
def ordenadas_UH(N, K, dt):
    '''
    Calcula as ordenadas do HU de Nash
    '''
    # u - Impulse Response Function - Instantaneous Unit Hydrograph (HUI)
    u = stats.gamma(N, loc=0, scale=K)
    # g - Step Response Function
    cdf = 0
    i = 0
    g = []
    while cdf <= 0.995:
        cdf = u.cdf(i*dt)
        i += 1
        g.append(cdf)
    # h - Ordenadas do HU
    h = np.diff(g)
    n = len(h)
    return h, n


def simulacao(area, dt, PME, ETP, params, Qmon=None):

    # No modo de calibracao, params eh um np.array...
    if type(params) is np.ndarray:
        params = dict(zip(Xnomes, params))

    # Parametros SAC-SMA
    UZTWM = params['UZTWM'] # mm
    UZFWM = params['UZFWM'] # mm
    LZTWM = params['LZTWM'] # mm
    LZFPM = params['LZFPM'] # mm
    LZFSM = params['LZFSM'] # mm
    UZK   = params['UZK']   # 1/dia
    LZPK  = params['LZPK']  # 1/dia
    LZSK  = params['LZSK']  # 1/dia
    ADIMP = params['ADIMP'] # mm
    PCTIM = params['PCTIM'] # fracao decimal
    ZPERC = params['ZPERC'] # adimensional
    REXP  = params['REXP']  # adimensional
    PFREE = params['PFREE'] # fracao decimal
    NUH   = params['NUH']   # numero de reservatorios / par de forma da pdf Gama
    KUH   = params['KUH']   # dias / par de escala da pdf Gama
    if Qmon is not None:
        # Parametros Muskingum
        NMSK = params['NMSK'] # inteiro
        KMSK = params['KMSK'] # dias
        XMSK = params['XMSK'] # adimensional

    # Calcula as ordenadas do HU
    OrdUH, n = ordenadas_UH(NUH, KUH, dt)

    # Parametros fixos
    RIVA  = 0.0  # fracao decimal
    SIDE  = 0.0  # adimensional
    RSERV = 0.3  # fracao decimal

    #  !!!
    # # Atribui os estados iniciais - FALTA IMPLEMENTAR O SALVAMENTO DE ESTADOS COM MSK
    # if estados is None:
    #     estados = {} # Cria dicionario para atualizar ao fim do loop nas forcantes
    #     UZTWC = UZTWM*0.5
    #     UZFWC = UZFWM*0.2
    #     LZTWC = LZTWM*0.5
    #     LZFPC = LZFPM*0.5
    #     LZFSC = LZFSM*0.5
    #     ADIMC = UZTWC + LZTWC
    #     StUH = np.zeros(n)
    # else:
    #     UZTWC = estados['UZTWC']
    #     UZFWC = estados['UZFWC']
    #     LZTWC = estados['LZTWC']
    #     LZFPC = estados['LZFPC']
    #     LZFSC = estados['LZFSC']
    #     ADIMC = estados['ADIMC']
    #     StUH  = np.asarray(estados['HU'])
    # !!!

    # Atribui os estados iniciais
    UZTWC = UZTWM*0.5
    UZFWC = UZFWM*0.2
    LZTWC = LZTWM*0.5
    LZFPC = LZFPM*0.5
    LZFSC = LZFSM*0.5
    ADIMC = UZTWC + LZTWC
    StUH = np.zeros(n)

    # Fator de conversao mm -> m3/s
    fconv = area/(dt*86.4)

    # Definicoes para o SAC-SMA
    thres_zero = 0.0001
    SAVED = RSERV*(LZFPM+LZFSM)
    PAREA = 1 - ADIMP - PCTIM

    # Inicializacao das vazoes finais
    Qbfp = np.array([]) # baseflow - primary
    Qbfs = np.array([]) # baseflow - supplemental
    Qtci = np.array([]) # total channel inflow
    Qtco = np.array([]) # total channel outflow
    Qmsk = np.array([]) # vazao propagada a partir de Qmon
    Qsim = np.array([]) # vazao total no exutorio

    # Passa as forcantes para np.array, por se acaso
    PME = np.asarray(PME)
    ETP = np.asarray(ETP)
    # if Qmon is None:
    #     Qmon = np.zeros(len(PME))
    # else:
    #     Qmon = np.asarray(Qmon)

    ############################################################################
    # Inicio do loop externo - itera no passo de tempo basico (dt)
    ############################################################################
    for PXV, EDMND in np.nditer([PME, ETP]):
        # Evapotranspiracao - Zona Superior
        E1 = EDMND*(UZTWC/UZTWM)
        RED = EDMND - E1
        UZTWC = UZTWC - E1
        E2 = 0.0
        if UZTWC < thres_zero:
            E1 = E1 + UZTWC
            UZTWC = 0.0
            RED = EDMND - E1
            if UZFWC < RED:
                E2 = UZFWC
                UZFWC = 0.0
                RED = RED - E2
            else:
                E2 = RED
                UZFWC = UZFWC - E2
                RED = 0.0
        if (UZTWC/UZTWM) < (UZFWC/UZFWM): # Notar que, se UZFWC = 0.0, essa condicao nao se verifica
            UZRAT = (UZTWC + UZFWC)/(UZTWM + UZFWM)
            UZTWC = UZTWM*UZRAT
            UZFWC = UZFWM*UZRAT
        E5 = E1 + (RED+E2)*((ADIMC-E1-UZTWC)/(UZTWM+LZTWM))

        # Evapotranspiracao - Zona Inferior
        E3 = RED*(LZTWC/(UZTWM+LZTWM))
        LZTWC = LZTWC - E3
        if LZTWC < thres_zero:
            E3 = E3 + LZTWC
            LZTWC = 0.0
        RATLZT = LZTWC/LZTWM
        RATLZ = (LZTWC+LZFPC+LZFSC-SAVED)/(LZTWM+LZFPM+LZFSM-SAVED)
        if RATLZT < RATLZ:
            DEL = (RATLZ - RATLZT)*LZTWM
            LZTWC = LZTWC + DEL
            LZFSC = LZFSC - DEL
            if LZFSC < thres_zero:
                LZFPC = LZFPC + LZFSC
                LZFSC = 0.0

        # Evapotranspiracao - Zona Impermeavel Adicional (variavel - ADIMC/ADIMP)
        ADIMC = ADIMC - E5
        if ADIMC < 0.0:
            E5 = E5 + ADIMC # E5 = ADIMC
            ADIMC = 0.0
        E5 = E5*ADIMP

        # Infiltracao
        PAV = PXV + UZTWC - UZTWM
        if PAV < 0:
            UZTWC = UZTWC + PXV
            PAV = 0.0
        else:
            UZTWC = UZTWM
        ADIMC = ADIMC + PXV - PAV

        # Escoamento da Zona Impermeavel Permanente (PCTIM)
        ROIMP = PXV*PCTIM

        # Inicializacao dos somatorios para os escoamentos gerados em dt
        SBF = 0.0
        SSUR = 0.0
        SIF = 0.0
        SPERC = 0.0
        SDRO = 0.0
        SPBF = 0.0

        # Determinacao dos incrementos computacionais do passo de tempo basico
        NINC = int(np.floor(1.0 + 0.2*(UZFWC + PAV)))
        DINC = (1.0/NINC)*dt
        PINC = PAV/NINC
        DUZ = 1.0 - ((1.0-UZK)**DINC)
        DLZP = 1.0 - ((1.0-LZPK)**DINC)
        DLZS = 1.0 - ((1.0-LZSK)**DINC)

        ########################################################################
        # Inicio do loop interno - itera nos incrementos de infiltracao (ninc)
        ########################################################################
        for i in range(NINC):

            PAV = PINC
            # Escoamento direto 2 - zona impermeavel adicional (variavel)
            ADSUR = 0.0
            RATIO = (ADIMC-UZTWC)/LZTWM
            if RATIO < thres_zero:
                RATIO = 0.0
            ADDRO = PINC*(RATIO**2)

            # Antes de percolar, retira agua da Zona Inferior
            BF = LZFPC*DLZP
            LZFPC = LZFPC - BF
            if LZFPC < thres_zero:
                BF = BF + LZFPC
                LZFPC = 0.0
            SBF = SBF + BF
            SPBF = SPBF + BF
            BF = LZFSC*DLZS
            LZFSC = LZFSC - BF
            if LZFSC < thres_zero:
                BF = BF + LZFSC
                LZFSC = 0.0
            SBF = SBF + BF

            # Percolacao
            if (PINC+UZFWC) > 0.01:
                PERCM = LZFPM*DLZP + LZFSM*DLZS
                PERC = PERCM*(UZFWC/UZFWM)
                DEFR = 1.0 - ((LZTWC+LZFPC+LZFSC)/(LZTWM+LZFPM+LZFSM))
                PERC = PERC*(1.0 + ZPERC*(DEFR**REXP))
                if PERC >= UZFWC:
                    PERC = UZFWC
                    UZFWC = 0.0
                else:
                    UZFWC = UZFWC - PERC
                    CHECK = LZTWC + LZFPC + LZFSC + PERC - LZTWM - LZFPM - LZFSM # CHECK tem que ser negativo!
                    if CHECK > 0.0:
                        PERC = PERC - CHECK
                        UZFWC = UZFWC + CHECK
                    SPERC = SPERC + PERC
                    # Escoamento subsuperficial (interflow)
                    DEL = UZFWC*DUZ
                    SIF = SIF + DEL
                    UZFWC = UZFWC - DEL
                VPERC = PERC
                PERC = PERC*(1.0 - PFREE)
                if (PERC+LZTWC) <= LZTWM:
                    LZTWC = LZTWC + PERC
                    PERC = 0.0
                else:
                    PERC = PERC + LZTWC - LZTWM
                    LZTWC = LZTWM
                PERC = PERC + VPERC*PFREE
                if PERC != 0.0:
                    HPL = LZFPM/(LZFPM + LZFSM)
                    RATLP = LZFPC/LZFPM
                    RATLS = LZFSC/LZFSM
                    PERCP = PERC*(HPL*2.0*(1.0-RATLP))/((1.0-RATLP)+(1.0-RATLS))
                    PERCS = PERC - PERCP
                    LZFSC = LZFSC + PERCS
                    if (LZFSC > LZFSM):
                        PERCS = PERCS - LZFSC + LZFSM
                        LZFSC = LZFSM
                    LZFPC = LZFPC + (PERC-PERCS)
                if PAV != 0.0: # 245
                    if (PAV+UZFWC) <= UZFWM:
                        UZFWC = UZFWC + PAV
                    else:
                        # Escoamento superficial
                        PAV = PAV + UZFWC - UZFWM
                        UZFWC = UZFWM
                        SSUR = SSUR + PAV*PAREA
                        ADUSR = PAV*(1.0 - ADDRO/PINC)
                        SSUR = SSUR + ADSUR*ADIMP
            else:
                UZFWC = UZFWC + PINC

            # Balanco na area ADIMP (nao estava no Peck, 1976)
            ADIMC = ADIMC + PINC - ADDRO - ADSUR
            if ADIMC > (UZTWM + LZTWM):
                ADDRO = ADDRO + (ADIMC - (UZTWM+LZTWM))
                ADIMC = UZTWM + LZTWM
            SDRO = SDRO + ADDRO*ADIMP
            if ADIMC < thres_zero:
                ADIMC = 0.0
        ########################################################################
        # Fim do loop interno de percolacao
        ########################################################################

        EUSED = E1 + E2 + E3
        SIF = SIF*PAREA

        # Escoamentos da Zona Inferior
        TBF = SBF*PAREA
        BFCC = TBF*(1.0/(1.0+SIDE))
        BFP = SPBF*PAREA/(1.0+SIDE)
        BFS = BFCC - BFP
        if BFS < thres_zero:
            BFS = 0.0
        BFNCC = TBF - BFCC
        Qbfp = np.append(Qbfp, BFP * fconv)
        Qbfs = np.append(Qbfs, BFS * fconv)

        # Vai para o HU apenas o escoamento da Zona Superior
        TCI = ROIMP + SDRO + SSUR + SIF
        Qtci = np.append(Qtci, TCI * fconv)

        # Evapotranspracao da Zina Riparia
        E4 = (EDMND - EUSED)*RIVA
        TCI = TCI - E4
        if TCI < thres_zero:
            E4 = E4 + TCI
            TCI = 0.0
        EUSED = EUSED*PAREA
        TET = EUSED + E5 + E4

        # Evapotranspiracao Total
        TET = EUSED + E5 + E4

        # Confere se ADIMC >= UZTWC
        if ADIMC < UZTWC:
            ADIMC = UZTWC

        # Convolucao do HU
        StUH += OrdUH*TCI
        Qtco = np.append(Qtco, StUH[0] * fconv)
        StUH = np.roll(StUH, -1)
        StUH[-1] = 0.
    ############################################################################
    # Fim do loop externo
    ############################################################################

    ############################################################################
    # Propagacao - Muskingum
    ############################################################################
    if Qmon is not None:
        C1 = (-KMSK*XMSK + 0.5*dt) / (KMSK - KMSK*XMSK + 0.5*dt)
        C2 = (KMSK*XMSK + 0.5*dt) / (KMSK - KMSK*XMSK + 0.5*dt)
        C3 = (KMSK - KMSK*XMSK - 0.5*dt) / (KMSK - KMSK*XMSK + 0.5*dt)
        Qmsk = np.empty(len(Qmon))
        Qmsk[0] = Qmon[0]
        for i in range(1, len(Qmon)):
            Qmsk[i] = C1*Qmon[i] + C2*Qmon[i-1] + C3*Qmsk[i-1]
    ############################################################################
    # Propagacao - Muskingum
    ############################################################################

    # # Atualizacao dos estados
    # estados['UZTWC'] = UZTWC
    # estados['UZFWC'] = UZFWC
    # estados['LZTWC'] = LZTWC
    # estados['LZFPC'] = LZFPC
    # estados['LZFSC'] = LZFSC
    # estados['ADIMC'] = ADIMC
    # estados['UH'] = StUH
    if Qmon is not None:
        Qsim = Qbfp + Qbfs + Qtco + Qmsk
    else:
        Qsim = Qbfp + Qbfs + Qtco
    return Qsim
