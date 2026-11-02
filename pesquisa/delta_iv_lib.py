import pandas as pd, numpy as np, pickle, sys
from scipy.stats import norm
from scipy.optimize import brentq
R=0.10
def bs(S,K,T,s,tp):
    d1=(np.log(S/K)+(R+s*s/2)*T)/(s*np.sqrt(T)); d2=d1-s*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-R*T)*norm.cdf(d2) if tp=="c" else K*np.exp(-R*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
def ivf(p,S,K,T,tp):
    try: return brentq(lambda s:bs(S,K,T,s,tp)-p,0.02,3.0)
    except Exception: return np.nan
def delta(S,K,T,s,tp):
    d1=(np.log(S/K)+(R+s*s/2)*T)/(s*np.sqrt(T)); return norm.cdf(d1) if tp=="c" else norm.cdf(d1)-1
