# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 10:00:00 2020

@author: sabri
"""

import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import numpy as np

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
             'CA135087D507',
             'CA135087E679']

validIsin = [str.lower(i) for i in validIsin]

yieldBonds = bond_df.loc[bond_df['isin'].isin(validIsin)].reset_index(drop = True)
dateRange = ['1/15/2020', '1/14/2020', '1/13/2020', '1/10/2020',
             '1/9/2020', '1/8/2020', '1/7/2020', '1/6/2020', 
             '1/3/2020', '1/2/2020']
dateRange.reverse()

yieldBonds.maturity = [int(datetime.strptime(i, '%Y-%m-%d %H:%M').strftime('%y%m%d')) for i in yieldBonds.maturity]

# =============================================================================
# interpolate to solve for market price and cashflow for Sept 2022,2023,2025
# =============================================================================

# base sep2022 data on jun2022 
sep2022 = yieldBonds.loc[yieldBonds.maturity == 220601].reset_index(drop = True)

# change the maturity date
sep2022['maturity'] = [220901 for i in range(len(sep2022))]
mar2023 = yieldBonds.loc[yieldBonds.maturity == 230301].reset_index(drop = True)

# linearly interpolate price and coupon rate between jun 2022 and mar2023
weight = 1/3
for i in range(len(sep2022)):
    sep2022.loc[i,'pClose'] = (weight*sep2022.loc[i,'pClose']+(1-weight)*mar2023.loc[i,'pClose'])
    sep2022.loc[i,'couponRate'] = (weight*sep2022.loc[i,'couponRate']+(1-weight)*mar2023.loc[i,'couponRate'])

# repeat similar process for sep2023
sep2023 = yieldBonds.loc[yieldBonds.maturity == 230601].reset_index(drop = True)
sep2023['maturity'] = [230901 for i in range(len(sep2023))]
mar2024 = yieldBonds.loc[yieldBonds.maturity == 240301].reset_index(drop = True)
for i in range(len(sep2023)):
    sep2023.loc[i,'pClose'] = (weight*sep2023.loc[i,'pClose']+(1-weight)*mar2024.loc[i,'pClose'])
    sep2023.loc[i,'couponRate'] = (weight*sep2023.loc[i,'couponRate']+(1-weight)*mar2024.loc[i,'couponRate'])

# repeat similar process for sep2025
weight = 1/4
sep2025 = yieldBonds.loc[yieldBonds.maturity == 250601].reset_index(drop = True)
sep2025['maturity'] = [250901 for i in range(len(sep2025))]
jun2026 = yieldBonds.loc[yieldBonds.maturity == 260601].reset_index(drop = True)
for i in range(len(sep2025)):
    sep2025.loc[i,'pClose'] = (weight*sep2025.loc[i,'pClose']+(1-weight)*jun2026.loc[i,'pClose'])
    sep2025.loc[i,'couponRate'] = (weight*sep2025.loc[i,'couponRate']+(1-weight)*jun2026.loc[i,'couponRate'])


# remove jun2022 and jun2023 data
yieldBonds = yieldBonds[~yieldBonds.maturity.isin([220601,230601,250601,260601])].reset_index(drop = True)
yieldBonds = pd.concat([yieldBonds, sep2022,sep2023,sep2025],axis = 0)
yieldBonds = yieldBonds.sort_values(by = 'maturity')

# =============================================================================
# calculate yield rate for each data point for each market date and plot it
# =============================================================================

fig = go.Figure()

for date in dateRange:
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
    x = range(0,11)
    x = [i/2 for i in x]

    yieldRate = []
    
    runningSum = 0
   
    for i in range(0,len(bonds)-1):
        couponRate = bonds.loc[i+1,'couponRate']/100
        notional = 1000
        marketPrice = bonds.loc[i,'pClose']/100 * notional
        timeToMaturity = (1+(6*i))/12
        newYield = -np.log((marketPrice - runningSum)/notional)/timeToMaturity
        yieldRate.append(newYield)
        runningSum += notional * couponRate * np.exp(-yieldRate[i]*timeToMaturity)
            
    fig.add_trace(go.Scatter(x=x, y=yieldRate,
                    mode='lines + markers',
                    name=date))
    
    fig.update_layout(title = {
            'text':"5 Year Yield Curve",
            'y':0.9,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Yield Rate',
               template = 'plotly_white'
               )
    fig.update_xaxes(dtick =1, rangemode = 'tozero', range = [0,5])
    

fig.show()
fig.write_image("5 Year Yield Curve.png", width = 624, height = 300)

# =============================================================================
# calculate the spot rate for each maturity date and plot it
# =============================================================================

fig2 = go.Figure()

for date in dateRange:
    
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
#    x_maturity = bonds['maturity']
#    x_maturity = [datetime.strptime(str(i),'%y%m%d') for i in x_maturity]
    x = range(0,11)
    x = [i/2 for i in x]
    spotRate = []
    firstSpot = yieldRate[0]
    firstCoupon = 1000 * bonds.loc[1,'couponRate']/100
    spotRate.append(firstSpot)
    runningSum = firstCoupon * np.exp(-spotRate[0]*(1/2))
    
    for i in range(1,len(bonds)-1):
        couponRate = bonds.loc[i+1,'couponRate']/100
        notional = 1000
        marketPrice = bonds.loc[i,'pClose']/100 * notional
        timeToMaturity = 1/2
        newSpot = (((notional/(marketPrice - runningSum))**(1/(i+1)))-1)/timeToMaturity
        spotRate.append(newSpot)
        runningSum += notional * couponRate * np.exp(-spotRate[i]*timeToMaturity)
     
    fig2.add_trace(go.Scatter(x=x, y=spotRate,
                    mode='lines + markers',
                    name=date))
    
    fig2.update_layout(title = {
            'text':"5 Year Spot Curve",
            'y':0.9,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Spot Rate',
               template = 'plotly_white'
               )
    fig2.update_xaxes(dtick =1, rangemode = 'tozero', range = [0,5])


fig2.show()
fig2.write_image("5 Year Spot Curve.png", width = 624, height = 300)
# =============================================================================
# calculate the forward rate for each matury date and plot it
# =============================================================================


fig3 = go.Figure()

for date in dateRange:
    
    bonds = yieldBonds[yieldBonds.date == date].reset_index(drop = True)
    x = range(2,11)
    x = [i/2 for i in x]

    # calculate the yield rates
    yieldRate = []
    
    runningSum = 0
   
    for i in range(0,len(bonds)-1):
        couponRate = bonds.loc[i+1,'couponRate']/100
        notional = 1000
        marketPrice = bonds.loc[i,'pClose']/100 * notional
        timeToMaturity = (1+(6*i))/12
        newYield = -np.log((marketPrice - runningSum)/notional)/timeToMaturity
        yieldRate.append(newYield)
        runningSum += notional * couponRate * np.exp(-yieldRate[i]*timeToMaturity)
    
    fwdRate = []
        
    for i in range(2,len(yieldRate)-2):
        y1 = yieldRate[i]
        y2 = yieldRate[i+2]
        t1 = (1+(6*i))/2
        t2 = (1+(6*(i+2)))/2
        newFwd = ((y2*t2)-(y1*t1))/(t2-t1)
        fwdRate.append(newFwd)
     
    fig3.add_trace(go.Scatter(x=x, y=fwdRate,
                    mode='lines + markers',
                    name=date))
    
    fig3.update_layout(title = {
            'text':"One Year Forward Curve",
            'y':0.9,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'},
               xaxis_title = 'Time to Maturity',
               yaxis_title = 'Forward Rate',
               template = 'plotly_white'
               )
    fig3.update_xaxes(dtick =1, rangemode = 'tozero', range = [0,5])

fig3.show()
fig3.write_image("5 Year Forward Curve.png", width = 624, height = 300)


