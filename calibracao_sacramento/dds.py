import numpy as np
from tqdm import tqdm

def dds(Xmin, Xmax, fobj, r=0.2, m=100):
    # Passo 1
    Xmin = np.asarray(Xmin)
    Xmax = np.asarray(Xmax)
    X0 = (Xmin + Xmax)/2
    D = len(Xmin)
    ds = [i for i in range(D)]
    dX = Xmax - Xmin
    # Passo 2
    I = np.arange(1, m+1, 1)
    Xbest = X0
    Fbest = fobj(Xbest)
    # Passo 3
    for i in tqdm(I):
        Pi = 1 - np.log(i)/np.log(m)
        P = np.random.rand(len(Xmin))
        N = np.where(P < Pi)[0]
        if N.size == 0:
            N = [np.random.choice(ds)]
        # Passo 4
        Xnew = np.copy(Xbest)
        for j in N:
            Xnew[j] = Xbest[j] + r*dX[j]*np.random.normal(0, 1)
            if Xnew[j] < Xmin[j]:
                Xnew[j] = Xmin[j] + (Xmin[j] - Xnew[j])
                if Xnew[j] > Xmax[j]:
                    Xnew[j] = Xmin[j]
            elif Xnew[j] > Xmax[j]:
                Xnew[j] = Xmax[j] - (Xnew[j] - Xmax[j])
                if Xnew[j] < Xmin[j]:
                    Xnew[j] = Xmax[j]
        # Passo 5
        Fnew = fobj(Xnew)
        if Fnew <= Fbest:
            Fbest = Fnew
            print('fmin=',Fbest)
            Xbest = np.copy(Xnew)
    # Fim
    return Xbest, Fbest
