# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 10:00:00 2020

@author: sabri
"""

import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import numpy as np
from scipy import optimize
import scipy.linalg as la

# import data
maturity_df = pd.read_csv('maturity_df.csv')[:-1]
bond_df = pd.read_csv('bond data.csv')
validIsin = ['CA135087D929',
             'CA135087E596',
             'CA135087F254',
             'CA135087F585',
             'CA135087G328',
             'CA135087ZU15',
             'CA135087H490',
             'CA135087A610',
             'CA135087J546',
             'CA135087J967',
             'CA135087K528',
             'CA135087D507']

validIsin = [str.lower(i) for i in validIsin]

yieldBonds = bond_df.loc[bond_df['isin'].isin(validIsin)].reset_index(drop = True)
dateRange = ['1/15/2020', '1/14/2020', '1/13/2020', '1/10/2020',
             '1/9/2020', '1/8/2020', '1/7/2020', '1/6/2020', 
             '1/3/2020', '1/2/2020']
dateRange.reverse()

yieldBonds.maturity = [int(datetime.strptime(i, '%Y-%m-%d %H:%M').strftime('%y%m%d')) for i in yieldBonds.maturity]

t1 = datetime.date((datetime.strptime('2020-02-02 0:00', '%Y-%m-%d %H:%M')))

# =============================================================================
# yield curve (solve for YTM as IRR)
# =============================================================================

def xnpv(rate,cashflows):
    """
    Calculate the net present value of a series of cashflows at irregular intervals.
    Arguments
    ---------
    * rate: the discount rate to be applied to the cash flows
    * cashflows: a list object in which each element is a tuple of the form (date, amount), where date is a python datetime.date object and amount is an integer or floating point number. Cash outflows (investments) are represented with negative amounts, and cash inflows (returns) are positive amounts.
    
    Returns
    -------
    * returns a single value which is the NPV of the given cash flows.
    Notes
    ---------------
    * The Net Present Value is the sum of each of cash flows discounted back to the date of the first cash flow. The discounted value of a given cash flow is A/(1+r)**(t-t0), where A is the amount, r is the discout rate, and (t-t0) is the time in years from the date of the first cash flow in the series (t0) to the date of the cash flow being added to the sum (t).  
    * This function is equivalent to the Microsoft Excel function of the same name. 
    """

    chron_order = sorted(cashflows, key = lambda x: x[0])
    t0 = chron_order[0][0] #t0 is the date of the first cash flow

    return sum([cf/(1+rate)**((t-t0).days/365.0) for (t,cf) in chron_order])

def xirr(cashflows,guess=0.1):
    """
    Calculate the Internal Rate of Return of a series of cashflows at irregular intervals.
    Arguments
    ---------
    * cashflows: a list object in which each element is a tuple of the form (date, amount), where date is a python datetime.date object and amount is an integer or floating point number. Cash outflows (investments) are represented with negative amounts, and cash inflows (returns) are positive amounts.
    * guess (optional, default = 0.1): a guess at the solution to be used as a starting point for the numerical solution. 
    Returns
    --------
    * Returns the IRR as a single value
    
    Notes
    ----------------
    * The Internal Rate of Return (IRR) is the discount rate at which the Net Present Value (NPV) of a series of cash flows is equal to zero. The NPV of the series of cash flows is determined using the xnpv function in this module. The discount rate at which NPV equals zero is found using the secant method of numerical solution. 
    * This function is equivalent to the Microsoft Excel function of the same name.
    * For users that do not have the scipy module installed, there is an alternate version (commented out) that uses the secant_method function defined in the module rather than the scipy.optimize module's numerical solver. Both use the same method of calculation so there should be no difference in performance, but the secant_method function does not fail gracefully in cases where there is no solution, so the scipy.optimize.newton version is preferred.
    """
    
    #return secant_method(0.0001,lambda r: xnpv(r,cashflows),guess)
    return optimize.newton(lambda r: xnpv(r,cashflows),guess)

fig = go.Figure()
dailyYield = {}

for date in dateRange:
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
    d = [datetime.date(datetime.strptime(str(i), '%y%m%d')) for i in bonds.maturity]
    d = [t1] + d

    x = [datetime.strptime(str(i), '%y%m%d') for i in bonds.maturity]
    yieldRate = []
    
    for i in range(0,len(bonds)):
        notional = 1000
        marketPrice = [-bonds.loc[i,'pClose']/100 * notional]
        couponRate = bonds.loc[i,'couponRate']/100
        coupons = [notional*couponRate] * (i)    
        cashflow = marketPrice + coupons + [notional]
        values = [(a,b) for a,b in zip(d[:len(cashflow)],cashflow)]
        
        newYield = xirr(values, 0.1)
        yieldRate.append(newYield)
    
    dailyYield[date] = yieldRate

    fig.add_trace(go.Scatter(x=x, y=yieldRate,
                    mode='lines + markers',
                    name=date))
    
    fig.update_layout(title = {
            'text':"5 Year Yield Curve - Gov't of Canada Bonds",
            'y':0.8,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Yield Rate',
               template = 'plotly_white'
               )
    fig.update_xaxes(range = [datetime.strptime(str(200101), '%y%m%d'),datetime.strptime(str(260101), '%y%m%d')])

    
fig.show()
fig.write_image("5 Year Yield Curve.png", width = 624, height = 300)

dailyYield = pd.DataFrame(dailyYield)

# =============================================================================
# bootstrap the spot rate for each data point for each market date and plot it
# =============================================================================

# we will store the yield rates of every day in a dictionary
# this saves us from needing to recalculate further on

fig = go.Figure()

for date in dateRange:
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
    x = [datetime.strptime(str(i), '%y%m%d') for i in bonds.maturity]

    timesToMaturity = [abs((datetime.date(datetime.strptime(str(i), '%y%m%d'))-t1).days)/365.25 for i in bonds.maturity]

    spotRate = []
    
    for i in range(0,len(bonds)):
        notional = 1000
        marketPrice = bonds.loc[i,'pClose']/100 * notional
        couponRate = bonds.loc[i,'couponRate']/100
        timeToMaturity = timesToMaturity[i]
        coupons = [notional*couponRate] * (i)    
        discount = [np.exp(-i*j) for i,j in zip(spotRate, timesToMaturity[:len(spotRate)])]
        cashflow = np.multiply(coupons,discount)
        newSpot = -np.log((marketPrice - sum(cashflow))/(notional))/(timeToMaturity)
        spotRate.append(newSpot)
    
    fig.add_trace(go.Scatter(x=x, y=spotRate,
                    mode='lines + markers',
                    name=date))
    
    fig.update_layout(title = {
            'text':"5 Year Spot Rate Curve",
            'y':0.8,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Spot Rate',
               template = 'plotly_white'
               )
    fig.update_xaxes(range = [datetime.strptime(str(200101), '%y%m%d'),datetime.strptime(str(260101), '%y%m%d')])

fig.show()
fig.write_image("5 Year Spot Curve.png", width = 624, height = 300)

# =============================================================================
# calculate the forward rate for each matury date and plot it
# =============================================================================

#store forward rates in dictionary for future question
dailyFwd = {}

fig3 = go.Figure()

for date in dateRange:
    
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
    x = [datetime.strptime(str(i), '%y%m%d') for i in bonds.maturity]

    yieldRate = list(dailyYield[date])    
    fwdRate = []
        
    for i in range(2,len(yieldRate)-2):
        y1 = yieldRate[i]
        y2 = yieldRate[i+2]
        t1 = timesToMaturity[i]
        t2 = timesToMaturity[i+2]
        newFwd = ((y2*t2)-(y1*t1))/(t2-t1)
        fwdRate.append(newFwd)
    
    dailyFwd[date]=fwdRate
     
    fig3.add_trace(go.Scatter(x=x[2:], y=fwdRate,
                    mode='lines + markers',
                    name=date))
    
    fig3.update_layout(title = {
            'text':"One Year Forward Curve",
            'y':0.8,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Forward Rate',
               template = 'plotly_white'
               )
    
    fig3.update_xaxes(range = [datetime.strptime(str(200101), '%y%m%d'),datetime.strptime(str(260101), '%y%m%d')])


dailyFwd = pd.DataFrame(dailyFwd)

fig3.show()
fig3.write_image("5 Year Forward Curve.png", width = 624, height = 300)

# =============================================================================
# find covariance matrix of log-returns of yield
# =============================================================================

yCov = np.empty([5,9])

for i in range(2,11,2):

    yields = dailyYield.loc[i]
    
    for j in range(len(yields)-1):
        ind = int(i/2)-1
        yCov[ind,j]=np.log(yields[j+1]/yields[j])

yCov = np.cov(yCov)
yEval, yEvec = la.eig(yCov)

d={}
for i in range(len(yEval)):
    d[yEval[i]]=yEvec[i]
    
fCov = np.empty([4,9])

for i in range(0,7,2):
    fwds = dailyFwd.loc[i]
    for j in range(len(fwds)-1):
        ind = int(i/2)
        fCov[ind,j] = np.log(fwds[j+1]/fwds[j])

fCov = np.cov(fCov)
fEval, fEvec = la.eig(fCov)

d={}
for i in range(len(fEval)):
    d[fEval[i]]=fEvec[i]
    



