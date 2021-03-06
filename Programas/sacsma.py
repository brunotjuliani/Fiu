'''
--------------------------------------------------------------------------------
Modelo Hidrológico Sacramento Soil Moisture Accounting (SAC-SMA)
--------------------------------------------------------------------------------
Implementacao - Arlan Scortegagna, ago/2020
Ultima atualizacao - Arlan Scortegagna, nov/2020
Revisoes - Louise Kuana, set/2020, Bruno Toná Juliani ???
--------------------------------------------------------------------------------
Descricao
    Realiza o balanco de umidade do solo (SMA) seguindo o modelo conceitual
    Sacramento, utilizado pelo National Weather Service River Forecast System
    (NWSRFS)
    Esse modelo foi traduzido a partir da funcao "fland1.f" obtida no repositorio
    de Dan Bronman, Eng. Hidrólogo do Bureau of Reclamation, no link abaixo
    << https://github.com/danbroman/NWS_SacSMA_source >>
    O codigo fonte de fland1.f encontra-se na pasta de miscelaneas
    A versao atualizada em nov/2020 considera a aplicacao de um hidrograma uni-
    tario a precipitacao efetiva, produzida na zona superior, e a propagacao por
    meio do metodo de Muskingum das vazoes de montante.
--------------------------------------------------------------------------------
'''

import numpy as np
from scipy import stats
from spotpy.parameter import Uniform

import pandas as pd


def simulacao(area, dt, PME, ETP,
                UZTWM, UZFWM, LZTWM, LZFPM, LZFSM,
                ADIMP, PCTIM, PFREE,
                UZK, LZPK, LZSK,
                ZPERC, REXP,
                K_HU, N_HU,
                RIVA=0, SIDE=0, RSERV=0.3):

    # Valores iniciais das Variaveis de Estado
    UZTWC = UZTWM*0.5
    UZFWC = UZFWM*0.5
    LZTWC = LZTWM*0.5
    LZFPC = LZFPM*0.5
    LZFSC = LZFSM*0.5
    ADIMC = UZTWC + LZTWC

    # AREA PEARMEAVEL PERMANENTE (PAREA)
    # O Sac-SMA considera 3 areas superficiais:
    # PAREA - permeavel de tamanho constante;
    # PCTIM - impermeavel de tamanho constante;
    # ADIMC - permeavel de tamanho variavel, limitada a ADIMP.
    # Sao fracoes e, portanto, PAREA + PCTIM + ADIMP = 1.
    PAREA = 1 - ADIMP - PCTIM

    # PROPAGACAO - DEFINICOES DO HIDROGRAMA UNITARIO (HU) DE NASH
    # u(t) - Hidrograma Unitario Instantaneo (HUI)
    u = stats.gamma(N_HU, loc=0, scale=K_HU)
    # h(t) - Ordenadas do HU
    H = []
    i = 0
    while sum(H) <= 0.995:
        ord = u.cdf((i+1)*dt) - u.cdf(i*dt)
        H.append(ord)
        i += 1
    H = np.array(H) # Ordenadas do Hidrograma Unitario (HU)

    # cols = ['QUZ'] + [f'h{i}' for i in range(0, len(H))]
    # df_HU = pd.DataFrame(columns=cols)

    # O SAC-SMA opera com um loop externo, que itera para cada passo de tempo,
    # e com um loop interno, que itera para incrementos de precipitacao na etapa
    # de infiltracao
    ############################################################################
    # INICIO DO LOOP EXTERNO
    ############################################################################
    QUZ = []
    HU = np.zeros(len(H))
    QUZ_prop = []
    QLZP = []
    QLZS = []
    LZFPC_lista = []

    ii = 0
    for PXV, EP in np.nditer([PME,ETP]):
        # Siglas:
        # UZ - Zona Superior (Upper Zone)
        # LZ - Zona Inferior (Lower Zone)
        # UTZW - Reservatorio de agua de tensao da Zona Superior
        # UZFW - Reservatorio de agua livre da Zona Superior
        # LZTW - Reservatorio de agua de tensao da Zona Inferior
        # LZPW - Reservatorio primario de agua livre da Zona Inferior
        # LZSW - Reservatorio suplementar de agua livre da Zona Inferior

        # EVAPOTRANSPIRACAO
        # Existem algumas premissas relativas a evapotranspiracao:
        #   1 - a evapotranspiracao potencial nos reservatorios de agua de
        #   tensao eh proporcional a disponibilidade relativa de umidade nos
        #   mesmos, o que nao ocorre nos reservatorios de agua livre;
        #   2 - a evapotranspiracao consome prioritariamente agua de tensao,
        #   consumindo agua livre somente de forma indireta, por meio das
        #   demandas residuais ou de transferencia de agua livre para fins de
        #   equilibrio dos armazenamentos);
        #   3 - em decorrencia da 2a premissa, se houver consumo parcial do UZTW
        #   a demanda restante vai para o LZTW, sem passar pelo UZFW.
        # Significados das variaveis:
        #   EP     - evapotranspiracao potencial global
        #   EP1    - evapotranspiracao potencial no UZTW
        #   E1     - evapotranspiracao real do UZTW
        #   EP2    - evapotranspiracao potencial no UZFW (remanescente)
        #   E2     - evapotranspiracao real do UZFW
        #   RED    - evapotranspiracao potencial residual, passa p/ a LZ
        #   UZRAT  - disponibilidade relativa de agua da UZ, para o equilibrio
        #   EP3    - evapotranspiracao potencial no LZTW
        #   E3     - evapotranspiracao real do LZTW
        #   SAVED  - agua livre reservada, nao sujeita a evapotranspiracao
        #   RATLZT - Relacao conteudo/capacidade de agua de tensao na LZ
        #   RATLZ  - Relacao conteudo/capacidade de umidade total na LZ
        EP1 = EP*(UZTWC/UZTWM)
        if UZTWC >= EP1:
            E1 = EP1
            E2 = 0
        else:
            E1 = UZTWC
            EP2 = EP - E1
            if UZFWC >= EP2:
                E2 = EP2
            else:
                E2 = UZFWC
        UZTWC = UZTWC - E1
        UZFWC = UZFWC - E2
        if UZTWC <= 0.00001 : UZTWC = 0
        if UZFWC <= 0.00001 : UZFWC = 0
        RED = EP - E1 - E2
        if (UZTWC/UZTWM) < (UZFWC/UZFWM):
            UZRAT = (UZTWC + UZFWC)/(UZTWM + UZFWM)
            UZTWC = UZTWM*UZRAT
            UZFWC = UZFWM*UZRAT
        EP3 = RED*(LZTWC/(UZTWM + LZTWM))
        if LZTWC >= EP3:
            E3 = EP3
        else:
            E3 = LZTWC
        LZTWC = LZTWC - E3
        if LZTWC <= 0.00001 : LZTWC = 0
        SAVED = RSERV*(LZFPM + LZFSM)
        RATLZT = LZTWC / LZTWM
        RATLZ  = (LZTWC + LZFPC + LZFSC - SAVED)/(LZTWM + LZFPM + LZFSM - SAVED)
        if (RATLZT < RATLZ):
            DEL = (RATLZ - RATLZT)*LZTWM
            LZTWC = LZTWC + DEL # DEL < LZFSC+LZFPC, sempre (ver anexos)
            if LZFSC >= DEL:
                LZFSC = LZFSC - DEL
            else:
                DEL = DEL - LZFSC
                LZFSC = 0
                LZFPC = LZFPC - DEL
        EP5 = E1 + (RED + E2)*((ADIMC - E1 - UZTWC)/(UZTWM + LZTWM))
        if ADIMC >= EP5:
            E5 = EP5
            ADIMC = ADIMC - E5
        else:
            E5 = ADIMC
            ADIMC = 0
        E5 = E5*ADIMP # (ajusta de acordo com a area impermeavel adicional)
        # PERCOLACAO (a)
        # A percolacao representa a transferencia de agua livre do UZFW p/ a LZ.
        # Primeiramente, calcula-se a altura pluviometrica superavitaria da UZ,
        # ou seja, a quantidade de precipitacao que supera o deficit de agua de
        # tensao e que eh passivel de percolar junto com a agua livre do UZFW.
        # Significados das variaveis:
        #   PXV - altura pluviometrica global
        #   TWX - altura pluviometrica superavitaria
        if PXV >= (UZTWM - UZTWC):
            TWX = PXV - (UZTWM - UZTWC)
            UZTWC = UZTWM
        else:
            TWX = 0
            UZTWC = UZTWC + PXV

        # AREA IMPERMEAVEL ADICIONAL
        # ADIMC eh uma altura pluviometrica que representa a area saturada
        # da bacia. Essa area eh variavel, limitada e proprocional a umidade
        # relativa dos UZTW, ou seja, quanto mais saturado estiver de agua de
        # tensao, maior eh essa area impermeavel adicional.
        # Quando o UZTW esta na capacidade maxima, ou seja, UZTWC = UZTWM,
        # presume-se que a area sataurada tb esteja em seu limite maximo.
        # Considerando que ADIMC = ADIMC + (PXV - TWX), temos:
        #   1 - se o UZTW ja estava cheio, UZTWC = UZTWM acima, TWX = PXV e
        #   PXV - TWX = 0 (max), logo nao ocorre aumento de ADIMC;
        #   2 - se o UZTW estava vazio, UZTWC = 0, TWX = 0 e PXV - TWX = PXV
        # (max), logo toda a precipitacao vai incrementar ADIMC.
        ADIMC = ADIMC + PXV - TWX

        # ROIMP RUNOFF DA ÁREA IMPERMEAVEL PERMANENTE
        ROIMP = PXV * PCTIM
        # SIMPVT = SIMPVT + ROIMP (redundante?)

        # Variaveis do loop interno
        SSUR  = 0 # Somatorio do escoamento superficial
        SIF   = 0 # Somatorio do escoamento subsuperficial (interflow)
        SPERC = 0 # Somatorio da percolacao
        SDRO  = 0 # Somatorio do escoamento superficial direto (direct runoff)
        SPBF  = 0 # Somatorio do escoamento de base primario
        SSBF  = 0 # Somatorio do escoamento de base suplementar
        NINC = int(1 + 0.2*(UZFWC + TWX)) # Numero de incrementos/iteracoes
        DINC = (1/NINC) * dt              # Duracao dos incrementos
        PINC = TWX/NINC                   # Altura incremental
        DUZ  = 1 - ((1-UZK)**DINC)  # Fracao de deplecionamento do UZFW
        DLZP = 1 - ((1-LZPK)**DINC) # Fracao de deplecionamento do LZFP
        DLZS = 1 - ((1-LZSK)**DINC) # Fracao de deplecionamento do LZFS
        # Observacoes:
        #   1 - DINC possui dimensao de tempo igual a DT (dias)
        #   2 - PINC maximo = 5 mm (ver anexos)
        #   3 - As fracoes de deplecionamento servem para calcular as retiradas
        #   dos reservatorios a cada incremento e equivalem a
        #   (-1)*(S[t+dt]-S[t])/S[t] = 1-exp(1-k*dt) ~= 1-(1-k)^dt (ver anexos)

        ########################################################################
        # INICIO DO LOOP INTERNO
        ########################################################################
        for i in range(NINC):

            ADSUR = 0 # Escoamento superficial "a priori" gerado na area ADIMP

            # ESCOAMENTO DIRETO DA AREA ADIMP
            # A fracao de ADIMP
            RATIO = (ADIMC - UZTWC) / LZTWM #
            if RATIO < 0 : RATIO = 0
            # ADDRO eh a quantidade de escoamento direto da ADIMP
            ADDRO = PINC*(RATIO**2)

            # PERCOLACAO (b)
            # Retira agua livre do LZFP e LZFS, liberando volume desses reserva-
            # torios para receber a percolacao.
            # Significado das variaveis:
            #   DEL_PBF - agua livre que escoa do rsv primario
            #   DEL_SBF - agua livre que escoa do rsv suplementar
            DEL_PBF = LZFPC * DLZP
            if LZFPC < DEL_PBF:
                DEL_PBF = LZFPC
            DEL_SBF = LZFSC * DLZS
            if LZFSC < DEL_SBF:
                DEL_SBF = LZFSC
            LZFPC = LZFPC - DEL_PBF
            if LZFPC < 0.0001 : LZFPC = 0
            LZFSC = LZFSC - DEL_SBF
            if LZFSC < 0.0001 : LZFSC = 0
            SPBF = SPBF + DEL_PBF
            SSBF = SSBF + DEL_SBF


            if (PINC + UZFWC) > 0.01:
                # HA agua livre disponivel na UZ; a percolacao eh efetivada

                # PERCOLACAO (c)
                # Transfere agua livre da UZ para a LZ, antes de adicionar o
                # PINC no UZFW.
                # Significado das variaveis:
                #   PERCM - Limite min de percolacao com rsvs da LZ saturados
                #   DEFR  - Deficit relativo combinado de umidade da LZ
                #   PERC  - Volume de percolacao potencial
                #   DEFA  - Deficit absoluto combinado de umidade da LZ
                # Observacao: no livro do Singh, PERCM = PBASE e DEFR = DEWET
                PERCM = LZFPM*DLZP + LZFSM*DLZS
                DEFR  = 1 - (LZTWC + LZFPC + LZFSC)/(LZTWM + LZFPM + LZFSM)
                PERC  = PERCM*(1 + ZPERC*(DEFR**REXP))*(UZFWC/UZFWM)

                # PERCOLACAO (d) - Calcula a percolacao real de acordo com as
                # disponibilidades em UZFW e nos rsvs da LZ.
                if PERC > UZFWC:
                    PERC = UZFWC
                DEFA = LZTWM + LZFPM + LZFSM - (LZTWC + LZFPC + LZFSC)
                if PERC > DEFA:
                    PERC = DEFA
                UZFWC = UZFWC - PERC
                SPERC = SPERC + PERC

                # ESCOAMENTO SUBSUPERFICIAL (INTERFLOW)
                # Calcula SIF aqui, mas soh vai utilizar a atualizacao de UZFWC
                # no final deste condicional, na etapa de infiltracao
                DEL = UZFWC * DUZ
                SIF = SIF + DEL
                UZFWC = UZFWC - DEL

                # PERCOLACAO (e)
                # Distribui o volume percolado entre os rsvs da LZ.
                # Significado das variaveis:
                #   PERCT - Volume de percolacao que vai para o LZTWM
                #   EXC   - Volume que excede a capacidade do reservatorio
                #   PERCF - Volume de percolacao que vai para o LZFP e LZFS
                #   HPL   - Razao entre a capacidade maxima do rsv primario e a
                #   capacidade maxima de armazenamento de agua livre da LZ
                #   RATLP - Razao conteudo/capacidade do rsv primario
                #   RATLS - Razao conteudo/capacidade do rsv suplementar
                #   FRACP - Fracao de agua livre indo pro rsv primario
                #   PERCP - Volume de percolacao que vai para o rsv primario
                #   PERCS - Volume de percolacao que vai para o rsv suplementar
                PERCT = PERC*(1 - PFREE)
                if (PERCT + LZTWC) > LZTWM:
                    EXC = PERCT - (LZTWM - LZTWC)
                    LZTWC = LZTWM
                else:
                    EXC = 0
                    LZTWC = LZTWC + PERCT
                PERCF = EXC + PERC*PFREE
                if PERCF > 0:
                    HPL   = LZFPM/(LZFPM + LZFSM)
                    RATLP = LZFPC/LZFPM
                    RATLS = LZFSC/LZFSM
                    FRACP = HPL*2*(1-RATLP)/((1-RATLP)+(1-RATLS))
                    if FRACP > 1 : FRACP= 1
                    PERCP = PERCF*FRACP
                    PERCS = PERCF - PERCP
                    if (LZFSC + PERCS) <= LZFSM:
                        LZFSC = LZFSC + PERCS
                    else:
                        PERCS = LZFSM - LZFSC
                        LZFSC = LZFSM
                    LZFPC = LZFPC + (PERCF - PERCS)
                    if (LZFPC > LZFPM):
                        EXC   = LZFPC - LZFPM
                        LZTWC = LZTWC + EXC
                        LZFPC = LZFPM

                # INFILTRACAO
                # Passagem de agua livre excedente da superficie para o solo,
                # ou seja, adiciona PINC ao UZFW
                if PINC > 0:
                    # ESCOAMENTO SUPERFICIAL
                    # Ocorre somente quando a altura incremental + a agua livre
                    # do UZFW superam a capacidade maxima.
                    # Na area permeavel constante, basta multiplicar o SUR pela
                    # PAREA, ja calculada antes do Loop Externo.
                    # Ja na area permeavel variavel, o escoamento superficial
                    if (PINC + UZFWC) > UZFWM:
                        SUR = PINC - (UZFWM - UZFWC)
                        UZFWC = UZFWM
                        SSUR = SSUR + SUR*PAREA
                        ADSUR = SUR*(1 - ADDRO/PINC)
                        SSUR = SSUR + ADSUR*ADIMP
                    else:
                        # PINC = 0
                        UZFWC = UZFWC + PINC
            else:
                # (PINC+UZFWC) <= 0.01
                # NAO HA agua livre disponivel na UZ; nao ocorre percolacao
                UZFWC = UZFWC + PINC

            # ESCOAMENTO DIRETO DA AREA IMPERMEAVEL ADICIONAL
            ADIMC = ADIMC + PINC - ADDRO - ADSUR
            if ADIMC > UZTWM + LZTWM:
                ADDRO = ADDRO + ADIMC - (UZTWM + LZTWM)
                ADIMC = UZTWM + LZTWM
            SDRO = SDRO + ADDRO*ADIMP
            if ADIMC < 0.00001 : ADIMC = 0
        ########################################################################
        # FIM DO LOOP INTERNO
        ########################################################################

        # Computa os somatorios dos escoamentos e ajusata-os as areas nas quais
        # sao gerados...
        # SBF - Somatorio dos escoamentos de base (primario e suplementar);
        # TBF - Escoamento de base gerado pela area permeavel de tamanho constante;
        # SIDE - Quantidade de água do canal que infiltra (profundamente) e que depois eh descontado
        # BFCC - Componente do fluxo de base do canal
        # BFP - Componente de contribuicao da vazao de base do reservatorio primario
        # BFS - Componente de contribuicao da vazao de base do reservatorio suplementar
        # BFNCC - Componente do fluxo de base do canal que sai para fora da bacia
        SIF = SIF*PAREA
        SBF = SPBF + SSBF
        TBF = SBF*PAREA
        BFCC = TBF/(1+SIDE)
        BFP = SPBF*PAREA/(1+SIDE)
        BFS = BFCC - BFP
        if BFS < 0 : BFS = 0.0
        BFNCC = TBF - BFCC

        # Somatorio dos escoamentos da zona inferior -> QLZ
        QLZP.append(BFP)
        QLZS.append(BFS)

        # Somatorio dos escoamentos da zona superior -> QUZ
        SUZ = ROIMP + SDRO + SSUR + SIF
        EUSED = E1 + E2 + E3
        # RIVA - % de cobertura vegetal nas areas ribeirinhas
        # E4 - componente da evapotranspiracao real da cobertura vegetal
        E4 = (EP - EUSED)*RIVA
        SUZ = SUZ - E4
        if SUZ < 0:
            E4 = E4 + SUZ
            SUZ = 0
        QUZ.append(SUZ)

        ########################################################################
        # PROPACAO - CONVOLUCAO DO HU
        ########################################################################
        HU += SUZ * H
        QUZ_prop.append(HU[0])
        HU = np.roll(HU, -1)
        HU[-1] = 0

        # SROT = SROT + TCI # variavel nao declarada SROT!!!
        if ADIMC < UZTWC : ADIMC = UZTWC

    ############################################################################
    # FIM DO LOOP EXTERNO
    ############################################################################

    # Converte as laminas (mm) em vazoes (m3/s)
    fconv = area/(dt*86.4) # mm -> m3/s
    QLZP = np.asarray(QLZP) * fconv
    QLZS = np.asarray(QLZS) * fconv
    QUZ = np.asarray(QUZ) * fconv
    QUZ_prop = np.asarray(QUZ_prop) * fconv
    Qsim = QLZP + QLZS + QUZ_prop

    return Qsim
