from selenium import webdriver
from selenium.webdriver.support import ui
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import csv
from datetime import date, datetime
import pprint 
import json

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


chrome_options = webdriver.ChromeOptions()
prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)


def scrape(zipCode, sold=True, hist='5yr'):

  pp = pprint.PrettyPrinter()

  if sold:
    params = f'_sold_{hist}'
  else:
    params = f'_sale_{datetime.now()}'

  filename = f'homes_{zipCode}' + params + '.json'
  jsonFile =  open(filename, 'w')


  # assemble url
  url = f"https://www.redfin.com/zipcode/{zipCode}"
  if sold:
    url += f'/filter/include=sold-{hist}'

  # launch chrome
  web = webdriver.Chrome("./chromedriver.exe", chrome_options=chrome_options)
  web.get(url)

  def isloaded(driver):
    return driver.find_element(By.TAG_NAME, "body") != None

  wait = ui.WebDriverWait(web, 10)
  wait.until(isloaded)

  try:
    pagesText = web.find_element(By.CLASS_NAME, 'pageText').get_attribute('textContent')
    numPages = int(pagesText.split(' ')[-1])
    print(f"Found {numPages} pages")
  except Exception as e:
    print('Problem getting number of pages: ' + str(e))
    return

  # Page-by-Page loop
  pageCounter = 1
  ctr = 1
  timeout = 0
  em = ''
  data = {
    'houses' : []
  }
  while True:
    try:
      # get the next page
      if pageCounter > 1:
        print(f"Page {pageCounter} of {numPages}")
        web.get(url + f'/page-{pageCounter}')
        wait.until(isloaded)
        time.sleep(3)
      if pageCounter > numPages:
        break

      # get the links 
      links = []
      homes = web.find_elements(By.CLASS_NAME, 'HomeViews')
      for h in homes:
        bottoms = h.find_elements(By.CLASS_NAME, 'bottomV2')
      for bottom in bottoms:
        link = bottom.find_element(By.TAG_NAME, 'a').get_attribute('href')
        links.append(link)

      # home-by-home loop
      for link in links:
        # get the page
        web.get(link)

        # scrape that data baby
        # basics
        while True:
          try:
            if timeout == 200:
              print(em)
              return
            address = web.find_element(By.CLASS_NAME, 'street-address').get_attribute('title')
            pNb = web.find_elements(By.CSS_SELECTOR, '.stat-block.beds-section')
            price = pNb[0].find_element(By.CLASS_NAME, 'statsValue').get_attribute('textContent')
            beds = pNb[1].find_element(By.CLASS_NAME, 'statsValue').get_attribute('textContent')
            baths = web.find_element(By.CSS_SELECTOR, '.stat-block.baths-section').find_element(By.CLASS_NAME, 'statsValue').get_attribute('textContent')
            sqft = web.find_element(By.CSS_SELECTOR, '.stat-block.sqft-section').find_element(By.CLASS_NAME, 'statsValue').get_attribute('textContent')
            remarks = web.find_element(By.ID, 'marketing-remarks-scroll').find_element(By.TAG_NAME, 'p').find_element(By.TAG_NAME, 'span').get_attribute('textContent')
            if sold:
              lastSold = web.find_element(By.CSS_SELECTOR, '.sold-row.row.PropertyHistoryEventRow').find_element(By.CLASS_NAME, 'col-4').get_attribute('textContent')[:-4]
              soldDate = datetime.strptime(lastSold, '%b %d, %Y') # Mon dd, YYYY
            else:
              soldDate = 'nd'

            timeout = 0
            em = 'unknown error'
            success = True
            break
          except NoSuchElementException as e:
            print(f'({ctr})\t(NoSuchElementException) Data not found')
            success = False
            break
          except Exception as e:
            timeout += 1
            em = str(e)
            continue
        
            
        if success:
          # the basics 
          houseData = {
            "address" : address,
            "price" : price,
            "beds" : beds,
            "baths" : baths,
            "sqft" : sqft,
            "remarks" : remarks,
          }
          if sold:
            houseData['date_d'] = soldDate.day
            houseData['date_m'] = soldDate.month
            houseData['date_y'] = soldDate.year
          else:
            houseData['date_d'] = 'cfs'
            houseData['date_m'] = 'cfs'
            houseData['date_y'] = 'cfs'

          # from the amenities table
          amenitiesContainer = web.find_element(By.CLASS_NAME, 'amenities-container')
          sgTitles = [sgt.get_attribute('textContent') for sgt in amenitiesContainer.find_elements(By.CLASS_NAME, 'super-group-title')]
          sgContent = amenitiesContainer.find_elements(By.CLASS_NAME, 'super-group-content')
          superGroups = zip(sgTitles, sgContent) # e.g Interior Features, Parking, Lot info
          for title, content in superGroups:
            t = title.lower().replace(' ', '_')
            houseData[t] = {}
            amenityGroups = content.find_elements(By.CLASS_NAME, 'amenity-group')
            for ag in amenityGroups: # e.g Interior Features: Interior Features, Flooring Info, Heating 
              subtitle = ag.find_element(By.TAG_NAME, 'h3').get_attribute('textContent').lower().replace(' ', '_')
              houseData[t][subtitle] = {}
              entries = ag.find_elements(By.TAG_NAME, 'li')
              for entry in entries: # e.g Interior Features: Heating and cooling: Gas and electric, Energy efficiency, ... 
                kv = entry.get_attribute('textContent').lower().replace(' ', '_').split(':')
                k = kv[0]
                v = ''.join(kv[1:])[1:]
                houseData[t][subtitle][k] = v.replace('_', ' ')

          
          data['houses'].append(houseData)
          print(f"({ctr}) \t {address}: {beds} beds, {baths} baths, {sqft} sqft, {price}")
        ctr += 1

  
      pageCounter += 1
    except KeyboardInterrupt:
      json.dump(data, jsonFile, indent=4)
      jsonFile.close()
      print(f"Interrupted. Wrote {ctr} data points to {filename}")
      return


  json.dump(data, jsonFile, indent=4)
  jsonFile.close()
  print(f'\nFinished. {ctr} data points written to {filename}')



    
    





if __name__ == "__main__":

  welcome = \
"""
 _      _       
| |__  (_)_   __
| '_ \ | \ \ / /    Redfin Data Web Scraper (c) 2022 Henry Vecchione
| | | || |\ V /     Press CTRL-C to quit
|_| |_|/ | \_/  
     |__/       
"""

  print(welcome)

  try:
    zipCode = input("Search for a zip code:\n>>> ")
    if len(zipCode) != 5:
      raise Exception("Please enter a valid zip code (a 5-digit integer)")
    _ = int(zipCode)

    s = input("Type 'sold' for houses sold, or 'sale' for houses for sale:\n>>> ")
    if s == 'sold':
      sold = True
    elif s == 'sale':
      sold = False
    else:
      raise Exception("Please choose a valid option")
    
    if sold:
      print("How far back do you want to search? Enter the number of the option.")
      options = \
"""1) Last 1 week
2) Last 1 Month
3) Last 3 Months
4) Last 6 Months
5) Last 1 Year
6) Last 2 Years
7) Last 3 Years
8) Last 5 Years
>>> """
      h = int(input(options))
      if h < 1 or h > 8:
        raise Exception("Please pick a valid option")
      histStrs = {
        1 : '1wk',
        2 : '1mo',
        3 : '3mo',
        4 : '6mo',
        5 : '1yr',
        6 : '2yr',
        7 : '3yr',
        8 : '5yr'
      }

      hist = histStrs[h]

    if sold:
      out = f"sold in the last {hist}s"
    else:
      out = f"currently for sale"

    print(f'OK. Scraping houses in {zipCode} ' + out + '...')
    if sold:
      scrape(zipCode, sold=sold, hist=hist)
    else:
      scrape(zipCode, sold=sold)


        
  except Exception as e:
    print(str(e))
