'''
--------------------------------------------------------------------------------
Modelo Hidrológico Sacramento Soil Moisture Accounting (SAC-SMA)
--------------------------------------------------------------------------------
Implementacao - Arlan Scortegagna, fev/2021
Revisao -
Ultima atualizacao -
--------------------------------------------------------------------------------
Essa versao foi desenvolvida especialmente para a assimilacao de dados.
As principais modificacoes sao:
    - a funcao de simulacao retorna os estados finais;
    - e o modulo de propagacao possui apenas 3 estados conforme descrito abaixo.
Desta vez, o modulo de SMA foi traduzido para o Python a partir do codigo Fortan
disponivel em Peck (1976).
O modulo de propagacao foi implementado na forma de 3 reservatorios lineares de
Nash em cascata. Apenas os fluxos da Zona Superior sao propagados. Essa configu-
racao tem por objetivo impedir a limitacao teorica imposta pelo "lag error" do
HU e eh recomendada por Vrugt (2006) e Vrugt & Beven (2018).


Alem do modulo de SMA, ha duas componentes de propagacao: uma para as vazoes de
montante e outra para os escoamentos rapidos gerados na propria bacia.
--------------------------------------------------------------------------------
'''

import pandas as pd
import numpy as np
from scipy import stats # SUBSTITUIR POR ALGO ALTERNATIVO QUE SOH USE NUMPY


def simulacao(area, dt, PME, ETP, params, Qmon=None, estados=None):
    '''
    Notar que:
        area - area da bacia em km2
        dt - passo de tempo do modelo em dias (dt=0.25 para 6 horas)
        PME e ETP - numpy.array
        params - dicionario contendo nomes e valores dos parametros
        estados - dicionario contendo nomes e valores dos estados iniciais
    Retorna vazoes simuladas (numpy.array) e estados atualizados
    '''

    # Parametros livres
    UZTWM = params['UZTWM']  # mm
    UZFWM = params['UZFWM']  # mm
    LZTWM = params['LZTWM']  # mm
    LZFPM = params['LZFPM']  # mm
    LZFSM = params['LZFSM']  # mm
    ADIMP = params['ADIMP']  # mm
    UZK   = params['UZK']    # 1/dia
    LZPK  = params['LZPK']   # 1/dia
    LZSK  = params['LZSK']   # 1/dia
    ZPERC = params['ZPERC']  # adimensional
    REXP  = params['REXP']   # adimensional
    PCTIM = params['PCTIM']  # fracao decimal
    PFREE = params['PFREE']  # fracao decimal
    K     = params['K']      # dias
    N     = int(params['N']) # numero de reservatorios

    # Parametros fixos
    RIVA  = 0.0  # fracao decimal
    SIDE  = 0.0  # adimensional
    RSERV = 0.3  # fracao decimal

    # Estados iniciais
    if estados is None:
        estados = {}
        UZTWC = UZTWM*0.5
        UZFWC = UZFWM*0.2
        LZTWC = LZTWM*0.5
        LZFPC = LZFPM*0.5
        LZFSC = LZFSM*0.5
        ADIMC = UZTWC + LZTWC
        QIN  = [0]*N
        QOUT = [0]*N
    else:
        UZTWC = estados['UZTWC']
        UZFWC = estados['UZFWC']
        LZTWC = estados['LZTWC']
        LZFPC = estados['LZFPC']
        LZFSC = estados['LZFSC']
        ADIMC = estados['ADIMC']
        QIN   = estados['QIN']
        QOUT  = estados['QOUT']

    # Fator de conversao mm -> m3/s
    fconv = area/(dt*86.4)

    # Definicoes para o SAC-SMA
    thres_zero = 0.0001
    SAVED = RSERV*(LZFPM+LZFSM)
    PAREA = 1 - ADIMP - PCTIM

    # Inicializacao das vazoes de simulacao
    Qbfp = np.array([]) # baseflow - primary
    Qbfs = np.array([]) # baseflow - supplemental
    Qtci = np.array([]) # total channel inflow
    Qtco = np.array([]) # total channel outflow

    ############################################################################
    # Inicio do loop externo
    ############################################################################
    PME = np.asarray(PME)
    ETP = np.asarray(ETP)
    if Qmon is None:
        Qmon = np.zeros(len(PME))
    else:
        Qmon = np.asarray(Qmon)
    for PXV, EDMND, qmon in np.nditer([PME, ETP, Qmon]):

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
        # Inicio do loop de infiltracao/percolacao
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

        TBF = SBF*PAREA
        BFCC = TBF*(1.0/(1.0+SIDE))
        BFP = SPBF*PAREA/(1.0+SIDE)
        BFS = BFCC - BFP
        if BFS < thres_zero:
            BFS = 0.0
        BFNCC = TBF - BFCC

        # Vai para o canal apenas o escoamento da Zona Superior
        TCI = ROIMP + SDRO + SSUR + SIF

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

        # Escoamentos da Zona Inferior
        Qbfp = np.append(Qbfp, BFP * fconv)
        Qbfs = np.append(Qbfs, BFS * fconv)
        Qtci = np.append(Qtci, TCI * fconv)

        ########################################################################
        # Propagacao de TCI - Cascata de Nash
        ########################################################################
        # Esquema numerico centrado em t+dt/2
        # QIN - vazoes afluentes dos reservatorios em t
        # QOUT - vazoes defluentes dos reservatorios em t

        # Cada reservatorio recebe a vazao defluente do anterior + qbac_rsv
        qbac_rsv = (TCI * fconv)/N

        # No passo atual, t+dt, o primeiro reservatorio recebe tb qmon
        qin = qmon + qbac_rsv

        # Itera nos N reservatorios
        for n in range(N):
            # Vazao defluente do reservatorio em t+dt
            qout = (2*K - dt)/(2*K + dt)*QOUT[n] + dt/(2*K + dt)*(QIN[n] + qin)
            # Atualiza os estados deste reservatorio com t+dt para usar no proximo passo
            QIN[n] = qin
            QOUT[n] = qout
            # A vazao afluente do proximo reservatorio em t corresponde a...
            qin = qout + qbac_rsv

        # Vazao propagada: equivale a vazao defluente do ultimo reservatorio da cascata
        Qtco = np.append(Qtco, QOUT[-1])
        ########################################################################
        # Propagacao de TCI - Cascata de Nash
        ########################################################################

    ############################################################################
    # Fim do loop externo
    ############################################################################

    # Salva os estados atualizados
    estados['UZTWC'] = UZTWC
    estados['UZFWC'] = UZFWC
    estados['LZTWC'] = LZTWC
    estados['LZFPC'] = LZFPC
    estados['LZFSC'] = LZFSC
    estados['ADIMC'] = ADIMC
    estados['QIN']   = QIN
    estados['QOUT']  = QOUT

    Qsim = Qbfp + Qbfs + Qtco
    return Qsim, Qbfp, Qbfs, Qtci, Qtco


class spotpy(object):

    from spotpy.parameter import Uniform
    UZTWM = Uniform(low=10, high=150)
    UZFWM = Uniform(low=10, high=75)
    LZTWM = Uniform(low=75, high=400)
    LZFPM = Uniform(low=50, high=1000)
    LZFSM = Uniform(low=10, high=300)
    ADIMP = Uniform(low=0, high=0.2)
    UZK   = Uniform(low=0.2, high=0.4)
    LZPK  = Uniform(low=0.001, high=0.02)
    LZSK  = Uniform(low=0.020, high=0.250)
    ZPERC = Uniform(low=5, high=250)
    REXP  = Uniform(low=1.1, high=4)
    PCTIM = Uniform(low=0, high=0.1)
    PFREE = Uniform(low=0, high=0.6)
    K     = Uniform(low=0.5, high=3)
    N     = Uniform(low=1, high=5)

    def __init__(self, area, dt, PME, ETP, Qjus, idx, idx_cal, Qmon=None, fobj='LOG'):
        self.area = area
        self.dt = dt
        self.PME = PME
        self.ETP = ETP
        self.Qjus = Qjus
        self.idx = idx
        self.idx_cal = idx_cal
        self.Qmon = Qmon
        self.fobj = fobj

    def simulation(self, x):
        params = {}
        params['UZTWM'] = x.UZTWM
        params['UZFWM'] = x.UZFWM
        params['LZTWM'] = x.LZTWM
        params['LZFPM'] = x.LZFPM
        params['LZFSM'] = x.LZFSM
        params['ADIMP'] = x.ADIMP
        params['UZK']   = x.UZK
        params['LZPK']  = x.LZPK
        params['LZSK']  = x.LZSK
        params['ZPERC'] = x.ZPERC
        params['REXP']  = x.REXP
        params['PCTIM'] = x.PCTIM
        params['PFREE'] = x.PFREE
        params['K']     = x.K
        params['N']     = x.N
        Qsim, Qbfp, Qbfs, Qtci, Qtco = simulacao(self.area, self.dt, self.PME, self.ETP, params, self.Qmon)
        Qsim = pd.Series(index=self.idx, data=Qsim)
        return Qsim

    def evaluation(self):
        return self.Qjus

    def objectivefunction(self, simulation, evaluation):

        Qsim = simulation.rename('qsim')
        Qobs = evaluation.rename('qobs')
        df = pd.concat([Qsim, Qobs], axis=1)
        df_cal = df.loc[self.idx_cal]
        df_cal = df_cal.dropna()

        # LOG
        if self.fobj == 'LOG':
            df_cal['fmin'] = df_cal.apply(lambda x: (np.log(x['qsim']) - np.log(x['qobs']))**2, axis=1)
            fmin = df_cal['fmin'].sum()

        #NSE
        if self.fobj == 'NSE':
            NSE = 1 - np.sum((df_cal['qsim']-df_cal['qobs'])**2)/np.sum((df_cal['qobs']-np.mean(df_cal['qobs']))**2)
            fmin = 1 - NSE

        else:
            print('Sem funcao objetivo definida???')

        return fmin


if __name__ == '__main__':

    import matplotlib.pyplot as plt
    area = pd.read_csv('peq_fiu.csv', nrows=1, header=None).to_numpy()[0][0]
    dt = 0.25
    PEQ = pd.read_csv('peq_fiu.csv', skiprows=1, parse_dates=True, index_col='datahora_UTC')
    PME = PEQ['pme']
    ETP = PEQ['etp']
    params = pd.read_csv('par_fiu.csv', index_col='nome')['valor'].to_dict()
    Qsim, Qbfp, Qbfs, Qtci1, Qtco1 = simulacao(area, dt, PME, ETP, params)
    Qjus = PEQ['qjus']
    Qjus.plot(color='black')
    Qsim = pd.Series(index=PEQ.index, data=Qsim)
    Qsim.plot()
    plt.legend()
    plt.show()
