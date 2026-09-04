from tools.profit_rtd_book_adaptive_normalization_shadow import _classify


def main():
    baseline=[0.01]*15
    labels,_=_classify(baseline+[0.05])
    assert labels[-1] == 'NEUTRAL'  # zero variance baseline fails safe
    varied=[0.009,0.010,0.011]*5
    labels,_=_classify(varied+[0.020,-0.010])
    assert labels[-2] == 'BUY'
    assert labels[-1] == 'SELL'
    print('PROFIT_RTD_RC44=OK')

if __name__=='__main__': main()
