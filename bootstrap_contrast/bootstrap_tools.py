from __future__ import division

import numpy as np
import pandas as pd
import seaborn as sns

from scipy.stats import norm
from numpy.random import randint
from scipy.stats import ttest_1samp, ttest_ind, ttest_rel, mannwhitneyu, wilcoxon, norm
import warnings

# Keep python 2/3 compatibility, without using six. At some point,
# we may need to add six as a requirement, but right now we can avoid it.
try:
    xrange
except NameError:
    xrange=range

class bootstrap:
    '''Computes the summary statistic and a bootstrapped confidence interval. 

    Keyword arguments:
        x1, x2: array-like
            The data in a one-dimensional array form. Only x1 is required. 
            If x2 is given, the bootstrapped summary difference between 
            the two groups (x2-x1) is computed.
            
        paired: boolean, default False
            Whether or not x1 and x2 are paired samples. 
            
        statfunction: callable, default np.mean
            The summary statistic called on data.

        smoothboot: boolean, default False 
            Taken from seaborn.algorithms.bootstrap.
            If True, performs a smoothed bootstrap (draws samples from a kernel
            destiny estimate).

        alpha: float, default 0.05
            Denotes the likelihood that the confidence interval produced _does not_
            include the true summary statistic. When alpha=0.05, a 95% confidence
            interval is produced.

        reps: int, default 5000
            Number of bootstrap iterations to perform.

    Returns:
        An `bootstrap` object reporting the summary statistics, percentile CIs,
        bias-corrected and accelerated (BCa) CIs, and the settings used.

        summary: float
            The summary statistic.
        is_difference: boolean
            Whether or not the summary is the difference between two groups.
            If False, only x1 was supplied.
        is_paired: boolean
            Whether or not the difference reported is between 2 paired groups.
        statistic: callable
            The function used to compute the summary.
        reps: int
            The number of bootstrap iterations performed.
        stat_array: array.
            A sorted array of values obtained by bootstrapping the input arrays.
        ci: float
            The size of the confidence interval reported (in percentage).
        pct_ci_low, pct_ci_high: floats
            The upper and lower bounds of the confidence interval as computed
            by taking the percentage bounds. 
        pct_low_high_indices: array
            An array with the indices in `stat_array` corresponding to the percentage
            confidence interval bounds.
        bca_ci_low, bca_ci_high: floats
            The upper and lower bounds of the bias-corrected and accelerated (BCa)
            confidence interval. See Efron 1977. 
        bca_low_high_indices: array
            An array with the indices in `stat_array` corresponding to the BCa
            confidence interval bounds.

        Reported p-values (either float OR string 'NIL')
        pvalue_1samp_ttest: 
            P-value obtained from scipy.stats.ttest_1samp. 
            If 2 arrays were given (x1 and x2), returns 'NIL'.
            See https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.ttest_1samp.html

        pvalue_2samp_ind_ttest: 
            P-value obtained from scipy.stats.ttest_ind. 
            If a single array was given (x1 only), or if `paired` is True, returns 'NIL'.
            See https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.ttest_ind.html

        pvalue_2samp_related_ttest: 
            P-value obtained from scipy.stats.ttest_rel. 
            If a single array was given (x1 only), or if `paired` is False, returns 'NIL'.
            See https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.ttest_rel.html

        pvalue_wilcoxon: float OR string 'NIL'
            P-value obtained from scipy.stats.wilcoxon. 
            If a single array was given (x1 only), or if `paired` is False, returns 'NIL'.
            The Wilcoxons signed-rank test is a nonparametric paired test of the null hypothesis that
            the related samples x1 and x2 are from the same distribution.
            See https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.wilcoxon.html

        pvalue_mannWhitney: float OR string 'NIL'
            Two-sided p-value obtained from scipy.stats.mannwhitneyu. 
            If a single array was given (x1 only), returns 'NIL'.
            The Mann-Whitney U-test is a nonparametric unpaired test of the null hypothesis that
            x1 and x2 are from the same distribution.
            See https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.mannwhitneyu.html
            
    '''
    def __init__(self, x1, x2=None, 
        paired=False,
        statfunction=None,
        smoothboot=False,
        alpha_level=0.05, 
        reps=5000):

        # Turn to pandas series.
        x1=pd.Series(x1)
        diff=False

        # Initialise statfunction
        if statfunction==None:
            statfunction=np.mean
        
        # Compute two-sided alphas.
        if alpha_level>1. or alpha_level <0.:
            raise ValueError("alpha_level must be between 0 and 1.")
        alphas=np.array([alpha_level/2., 1-alpha_level/2.])

        if paired:
            # check x2 is not None:
            if x2 is None:
                raise ValueError('Please specify x2.')
            else:
                x2=pd.Series(x2)
                if len(x1)!=len(x2):
                    raise ValueError('x1 and x2 are not the same length.')
        
        if (x2 is None) or (paired is True) :
            if x2 is None:
                tx=x1
                paired=False
                ttest_single=ttest_1samp(x1,0)[1]
                ttest_2_ind='NIL'
                ttest_2_paired='NIL'
                wilcoxonresult='NIL'

            else:
                diff=True
                tx=x2-x1
                ttest_single='NIL'
                ttest_2_ind='NIL'
                ttest_2_paired=ttest_rel(x1,x2)[1]
                wilcoxonresult=wilcoxon(x1,x2)[1]
            mannwhitneyresult='NIL'

            # Turns data into array, then tuple.
            tdata=(tx,)

            # The value of the statistic function applied just to the actual data.
            summ_stat=statfunction(*tdata)

            ## Convenience function invoked to get array of desired bootstraps see above!
            # statarray=getstatarray(tdata, statfunction, reps, sort=True)
            statarray=sns.algorithms.bootstrap(tx, func=statfunction, n_boot=reps, smooth=smoothboot)
            statarray.sort()

            # Get Percentile indices
            pct_low_high=np.round((reps-1)*alphas)
            pct_low_high=np.nan_to_num(pct_low_high).astype('int')


        elif x2 is not None and paired is False:
            diff=True
            # Generate statarrays for both arrays.
            ref_statarray=sns.algorithms.bootstrap(x1, func=statfunction, n_boot=reps, smooth=smoothboot)
            exp_statarray=sns.algorithms.bootstrap(x2, func=statfunction, n_boot=reps, smooth=smoothboot)
            
            tdata=exp_statarray-ref_statarray
            statarray=tdata.copy()
            statarray.sort()
            tdata=(tdata,) # Note tuple form.

            # The difference as one would calculate it.
            summ_stat=statfunction(x2)-statfunction(x1)
            
            # Get Percentile indices
            pct_low_high=np.round((reps-1)*alphas)
            pct_low_high=np.nan_to_num(pct_low_high).astype('int')

            # Statistical tests.
            ttest_single='NIL'
            ttest_2_ind=ttest_ind(x1,x2)[1]
            ttest_2_paired='NIL'
            mannwhitneyresult=mannwhitneyu(x1,x2,alternative='two-sided')[1]
            wilcoxonresult='NIL'

        # Get Bias-Corrected Accelerated indices convenience function invoked.
        bca_low_high=bca(tdata, alphas, statarray, statfunction, summ_stat, reps)

        # Warnings for unstable or extreme indices.
        for ind in [pct_low_high, bca_low_high]:
            if np.any(ind==0) or np.any(ind==reps-1):
                warnings.warn("Some values used extremal samples results are probably unstable.")
            elif np.any(ind<10) or np.any(ind>=reps-10):
                warnings.warn("Some values used top 10 low/high samples results may be unstable.")
            
        self.summary=summ_stat
        self.is_paired=paired
        self.is_difference=diff
        self.statistic=str(statfunction)
        self.n_reps=reps

        self.ci=(1-alpha_level)*100
        self.stat_array=np.array(statarray)

        self.pct_ci_low=statarray[pct_low_high[0]]
        self.pct_ci_high=statarray[pct_low_high[1]]
        self.pct_low_high_indices=pct_low_high

        self.bca_ci_low=statarray[bca_low_high[0]]
        self.bca_ci_high=statarray[bca_low_high[1]]
        self.bca_low_high_indices=bca_low_high

        self.pvalue_1samp_ttest=ttest_single
        self.pvalue_2samp_ind_ttest=ttest_2_ind
        self.pvalue_2samp_paired_ttest=ttest_2_paired
        self.pvalue_wilcoxon=wilcoxonresult
        self.pvalue_mannWhitney=mannwhitneyresult

        self.results={'stat_summary':self.summary,
                'is_difference':diff,
                'is_paired':paired,
                'bca_ci_low':self.bca_ci_low, 
                'bca_ci_high':self.bca_ci_high,
                'ci':self.ci}

def jackknife_indexes(data):
    # Taken without modification from scikits.bootstrap package
    """
From the scikits.bootstrap package.
Given data points data, where axis 0 is considered to delineate points, return
a list of arrays where each array is a set of jackknife indexes.
For a given set of data Y, the jackknife sample J[i] is defined as the data set
Y with the ith data point deleted.
    """
    base=np.arange(0,len(data))
    return (np.delete(base,i) for i in base)

def bca(data, alphas, statarray, statfunction, ostat, reps):
    '''Subroutine called to calculate the BCa statistics. Borrowed heavily from scikits.bootstrap code.'''

    # The bias correction value.
    z0=norm.ppf( ( 1.0*np.sum(statarray < ostat, axis=0)  ) / reps )

    # Statistics of the jackknife distribution
    jackindexes=jackknife_indexes(data[0]) # I use the scikits.bootstrap function here.
    jstat=[statfunction(*(x[indexes] for x in data)) for indexes in jackindexes]
    jmean=np.mean(jstat,axis=0)

    # Acceleration value
    a=np.sum( (jmean - jstat)**3, axis=0 ) / ( 6.0 * np.sum( (jmean - jstat)**2, axis=0)**1.5 )
    if np.any(np.isnan(a)):
        nanind=np.nonzero(np.isnan(a))
        warnings.warn("Some acceleration values were undefined. \
            This is almost certainly because all values \
            for the statistic were equal. Affected \
            confidence intervals will have zero width and \
            may be inaccurate (indexes: {}). \
            Other warnings are likely related.".format(nanind))
    zs=z0 + norm.ppf(alphas).reshape(alphas.shape+(1,)*z0.ndim)
    avals=norm.cdf(z0 + zs/(1-a*zs))
    nvals=np.round((reps-1)*avals)
    nvals=np.nan_to_num(nvals).astype('int')
    
    return nvals