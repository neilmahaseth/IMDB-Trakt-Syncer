import os
import time
import csv
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
from chromedriver_py import binary_path
try:
    from IMDBTraktSyncer import errorHandling as EH
    from IMDBTraktSyncer import errorLogger as EL
except ImportError:
    import errorHandling as EH
    import errorLogger as EL

class PageLoadException(Exception):
    pass

def getImdbData(imdb_username, imdb_password, driver, directory, wait):
    # Process IMDB Watchlist
    print('Processing IMDB Data')
    
    
    # Generate watchlist export
    success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/list/watchlist', driver, wait)
    if not success:
        # Page failed to load, raise an exception
        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

    export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid*='hero-list-subnav-export-button'] button")))
    export_button.click()
    time.sleep(3)
    
    # Wait for export processing to finish
    # Function to check if any summary item contains "in progress"
    def check_in_progress(summary_items):
        for item in summary_items:
            if "in progress" in item.text.lower():
                return True
        return False
    # Maximum time to wait in seconds
    max_wait_time = 1200
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        # Wait for export processing to finish
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
        
        # Locate all elements with the selector
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

        # Check if any summary item contains "in progress"
        if not check_in_progress(summary_items):
            #print("No 'in progress' found. Proceeding.")
            break
        else:
            #print("'In progress' found. Waiting for 30 seconds before retrying.")
            time.sleep(30)
    else:
        raise TimeoutError("IMDB data processing did not complete within the allotted 20 minutes.")
    
    #Get IMDB Watchlist Items
    try:
        # Load page
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        # Locate all elements with the selector
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

        # Iterate through the located elements to find the one containing the text "watchlist"
        csv_link = None
        for item in summary_items:
            if "watchlist" in item.text.lower():
                # Try to find the button inside this item
                button = item.find_element(By.CSS_SELECTOR, "button[data-testid*='export-status-button']")
                if button:
                    csv_link = button
                    break

        # Check if the csv_link was found and then perform the actions
        if csv_link:
            driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
            csv_link.click()
        else:
            print("Unable to fetch IMDB watchlist data.")

        #Wait for csv download to complete
        time.sleep(8)

        imdb_watchlist = []

        here = os.path.abspath(os.path.dirname(__file__))
        here = directory
        
        try:
            # Find any CSV file in the directory
            csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]
            if not csv_files:
                raise FileNotFoundError("Watchlist data not found. No CSV files found in the directory")
            
            # Use the first CSV file found 
            watchlist_path = os.path.join(directory, csv_files[0])
            with open(watchlist_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader)  # Read the header row

                # Create a mapping from header names to their index
                header_index = {column_name: index for index, column_name in enumerate(header)}
                
                required_columns = ["Title", "Year", "Const", "Created", "Title Type"]
                missing_columns = [col for col in required_columns if col not in header_index]
                if missing_columns:
                    raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

                for row in reader:
                    title = row[header_index['Title']]
                    year = row[header_index['Year']]
                    imdb_id = row[header_index['Const']]
                    date_added = row[header_index['Created']]
                    media_type = row[header_index['Title Type']]
                    # Convert date format
                    date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    if "TV Series" in media_type or "TV Mini Series" in media_type:
                        media_type = "show"
                    elif "TV Episode" in media_type:
                        media_type = "episode"
                    elif any(media in media_type for media in ["Movie", "TV Special", "TV Movie", "TV Short", "Video"]):
                        media_type = "movie"
                    else:
                        media_type = "unknown"
                    
                    imdb_watchlist.append({
                        'Title': title,
                        'Year': year,
                        'IMDB_ID': imdb_id,
                        'Date_Added': date_added,
                        'Type': media_type
                    })
            
        except FileNotFoundError as e:
            print(f"Error: {error_message}", exc_info=True)
            EL.logger.error(error_message, exc_info=True)

        # Delete csv files
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                os.remove(os.path.join(directory, file))

    except (NoSuchElementException, TimeoutException):
        # No IMDB Watchlist Items
        imdb_watchlist = []
        pass
    
    # Get IMDB Ratings

    imdb_ratings = []

       
    #Get IMDB Reviews
    
    # Load page
    
    
    reviews = []
    errors_found_getting_imdb_reviews = False
   
    filtered_reviews = []
    
    imdb_reviews = filtered_reviews

    print('Processing IMDB Data Complete')
    
    return imdb_watchlist, imdb_ratings, imdb_reviews, errors_found_getting_imdb_reviews
