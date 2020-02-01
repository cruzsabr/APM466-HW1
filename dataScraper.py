# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 20:25:03 2020

@author: sabri
"""

from selenium import webdriver
import time
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# =============================================================================
# getting a list of 17 shortterm bond URLs
# =============================================================================

# initialize webdriver
driver = webdriver.Firefox()

# input link to table of relevant bonds
shortTermUrl = 'https://markets.businessinsider.com/bonds/finder?borrower=71&maturity=shortterm&yield=&bondtype=2%2c3%2c4%2c16&coupon=&currency=184&rating=&country=19'

# navigate driver to url
driver.get(shortTermUrl)

# scrape the page using bs4
shortTermSoup = BeautifulSoup(driver.page_source, 'html.parser')

# select the results table
shortTermLst = shortTermSoup.find_all('table', {'class':'table table-small tableAltColor no-margin-bottom'})

# initialize storage list for links
shortTermLinks = []

# scrape the table for links
for link in shortTermLst[0].findAll('a'):
    shortTermLinks.append(link.get('href'))
    
# retain only relevant links
shortTermLinks = shortTermLinks[8:]

# initialize storage lists for relevant link data + isins
shortBondLst = []
shortBondIsin = []

# scrape shortTermLinks for the necessary info
for link in shortTermLinks:
    shortBondLst.append(link.split('/')[-1])

for link in shortBondLst:
    shortBondIsin.append(link.split('-')[-1])

# =============================================================================
# repeat for 15 midterm bonds
# =============================================================================

midTermUrl = 'https://markets.businessinsider.com/bonds/finder?borrower=71&maturity=midterm&yield=&bondtype=2%2c3%2c4%2c16&coupon=&currency=184&rating=&country=19'
driver.get(midTermUrl)

midTermSoup = BeautifulSoup(driver.page_source, 'html.parser')
midTermLst = midTermSoup.find_all('table', {'class':'table table-small tableAltColor no-margin-bottom'})

midTermLinks = []

for link in midTermLst[0].findAll('a'):
    midTermLinks.append(link.get('href'))
    
midTermLinks = midTermLinks[8:]

midBondLst = []
midBondIsin = []

for link in midTermLinks:
    midBondLst.append(link.split('/')[-1])

for link in midBondLst:
    midBondIsin.append(link.split('-')[-1])

# =============================================================================
# scrape each page of historical bond data - ran after markets closed Jan 15
# =============================================================================

def scrapeHistory(isin, linkLst):
    """
    Takes a list of unique bond identifiers for businessinsider.com.
    Returns a dictionary of isin values, dates, opening prices, 
    and closing prices of the past 10 market days.
    """

    isinLst = []
    date = []
    pOpen = []
    pClose = []
    
    for i in range(len(isin)):
        pageIsin = isin[i]    
        pageUrl = 'https://markets.businessinsider.com/bond/historical/'+linkLst[i]+'/fse'
        time.sleep(20)
        driver.get(pageUrl)
        time.sleep(5)
        
        pageSoup = BeautifulSoup(driver.page_source, 'html.parser')
        pageInfo = pageSoup.find('div', {'id':'historic-price-list'})
        
        pageTable = pageInfo.find_all('td')
        
        for j in range(0,10):
            isinLst.append(pageIsin)
        
        for j in range(0,40,4):
            date.append(str(pageTable[j].text).strip())
            
        for j in range(1,40,4):
            pOpen.append(str(pageTable[j].text).strip())
            
        for j in range(2,40,4):
            pClose.append(str(pageTable[j].text).strip())
    
    d = {'isin':isinLst,
         'date':date,
         'pOpen':pOpen,
         'pClose':pClose}
    
    return d

midTermBond = scrapeHistory(midBondIsin, midBondLst)        
middf = pd.DataFrame(midTermBond)
middf.to_csv(r'mid term bond data.csv')

shortTermBond = scrapeHistory(shortBondIsin, shortBondLst)
shortdf = pd.DataFrame(shortTermBond)
shortdf.to_csv(r'short term bond data.csv')

# =============================================================================
# associating bonds to their maturity date
# =============================================================================

maturityInfoUrl = 'https://www.bankofcanada.ca/markets/government-securities-auctions/bank-of-canada-holdings/?fbclid=IwAR0QpyunbKQ_Y5Y9cjCrzDi8uf9ilm2Sy8aR77hP2sE-ny96qXj7MpY7vRU'
driver.get(maturityInfoUrl)

maturityInfoSoup = BeautifulSoup(driver.page_source, 'html.parser')
maturityInfoSauce = maturityInfoSoup.find_all('tbody', {'class':'bocss-table__tbody'})
maturityInfo = maturityInfoSauce[2]
maturityInfo = maturityInfo.find_all('tr')

maturity = []
couponRate = []
isin = []
parVal = []

for i in range(len(maturityInfo)):
    info = maturityInfo[i].find_all('td')
    maturity.append(info[0].text)
    couponRate.append(info[1].text)
    isin.append(info[2].text)
    parVal.append(info[3].text)
    

maturityDic = {'maturity':maturity,
               'couponRate':couponRate,
               'isin':isin,
               'parVal':parVal}

maturity_df = pd.DataFrame(maturityDic)
maturity_df.to_csv(r'maturity_df.csv') 

# =============================================================================
# compiling pricing data and maturity data 
# =============================================================================


mid_df = pd.read_csv('mid term bond data.csv')
short_df = pd.read_csv('short term bond data.csv')

# combine shortterm and midterm bonds
bond_df = pd.concat([short_df, mid_df],axis = 0)

# initialize new columns for incoming data
bond_df['maturity'] = 0
bond_df['couponRate'] = 0
bond_df['parVal'] = 0

# get a list of unique bond identifiers
isinLst = bond_df['isin'].unique()

# join maturity_df information to bond_df along isin
for e in isinLst:
    maturityDate = maturity_df[maturity_df['isin']==str.upper(e)]['maturity'].item()
    maturityDate = datetime.strptime(maturityDate, '%Y-%m-%d')
    bond_df.loc[bond_df['isin']==e,'maturity']=maturityDate
    couponRate = float(maturity_df[maturity_df['isin']==str.upper(e)]['couponRate'].item())
    bond_df.loc[bond_df['isin']==e,'couponRate']=couponRate
    parVal = float(maturity_df[maturity_df['isin']==str.upper(e)]['parVal'].item().replace(',',''))
    bond_df.loc[bond_df['isin']==e,'parVal'] = parVal
    
bond_df.to_csv(r'bond data.csv')    
