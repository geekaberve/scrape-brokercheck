from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

# The goal of this file is to scrape data from BrokerCheck
# To do this, we want to loop over every state and get the data of the brokers

# Initialize the WebDriver
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 60)

# Open the website
driver.get("https://brokercheck.finra.org")

# Locate the search bar and fill in a state (to be incorporated in a loop later)
search_box = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@placeholder="City, State or ZIP (optional)"]')))
search_box.send_keys("Alabama")

# Select the state option from the dropdown
state_option = wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "menu-item") and not(.//span[contains(text(), ",")])]')))
state_option.click()

# Locate and click the search button
search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="IndividualSearch"]')))
search_button.click()

# Wait for the page to load
time.sleep(5)

# Accept cookies if prompted
try:
    element_to_click = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div[2]/a[1]')))
    element_to_click.click()
    print("Accepted cookies.")
except Exception as e:
    print(f"Error clicking the element: {e}")

# Create a list to store the data
dataset = []

try:
    while True:  # Loop over all pages
        # Create a list with all the "More details" buttons on the page
        more_details_buttons = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, '//button[@aria-label="more details"]'))
        )
        
        # Wait for the page to load
        time.sleep(10)

        # Iterate over the buttons to extract information for each person
        for i in range(len(more_details_buttons)):
            more_details_buttons = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, '//button[@aria-label="more details"]'))
            )

            # Click one of the buttons and wait for the next page to load
            more_details_buttons[i].click()
            time.sleep(5)

            # Check if it's an investment adviser page
            more_details_buttons_after_click = driver.find_elements(By.XPATH, '//button[@aria-label="more details"]')
            if more_details_buttons_after_click:
                print("This is an investment adviser.")
                continue
            else:
                print("Broker.")

            # Get the page source and parse it with BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract the data we are interested in
            try:
                # Name
                name = None
                name_tag = soup.find('div', class_='flex flex-row gap-2 items-baseline')
                if name_tag:
                    name = name_tag.text.strip()

                # Variables in small boxes
                big_box = soup.find('div', class_='sm:hidden lg:hidden')
                disclosure_count, years_of_experience, firms_count = None, None, None

                if big_box:
                    small_boxes = big_box.find_all('div', class_='flex flex-row items-center gap-1 sm:my-0 sm:h-auto my-2 h-9 ng-star-inserted')
                    for j in range(0, len(small_boxes), 2):
                        number = small_boxes[j].get_text(strip=True)
                        description = small_boxes[j + 1].get_text(strip=True) if j + 1 < len(small_boxes) else None

                        if "Disclosure" in description:
                            disclosure_count = int(number)
                        elif "Years of Experience" in description:
                            years_of_experience = int(number)
                        elif "Firms" in description:
                            firms_count = int(number)

                # Organization and Address
                organization_name, address = None, None
                parent_div = soup.find('div', class_='flex flex-col text-sm')
                if parent_div:
                    org_name_tag = parent_div.find('span', class_='text-primary-60 font-semibold')
                    if org_name_tag:
                        organization_name = org_name_tag.get_text(strip=True)

                    address_tag = parent_div.find('investor-tools-address')
                    if address_tag:
                        address = address_tag.get_text(" ", strip=True)

                # Disclosure Details
                disclosure_details = []
                if disclosure_count and disclosure_count > 0:
                    chevron_buttons = driver.find_elements(By.XPATH, '//div[contains(@class, "flex-row") and contains(@class, "cursor-pointer")]//button')

                    for chevron_button in chevron_buttons:
                        driver.execute_script("arguments[0].scrollIntoView(true);", chevron_button)
                        chevron_button.click()
                        time.sleep(1)

                        try:
                            parent_row = chevron_button.find_element(By.XPATH, './ancestor::div[contains(@class, "transition flex flex-row items-center")]')
                            date_dispute = parent_row.find_element(By.XPATH, './div[contains(@class, "text-sm")]').text.strip().split('\n')[0]
                            type_dispute = parent_row.find_element(By.XPATH, './div[contains(@class, "text-sm")]').text.strip().split('\n')[1]
                            action_dispute = parent_row.find_element(By.XPATH, './div[contains(@class, "text-sm")]').text.strip().split('\n')[2]

                            disclosure_details.append({
                                'date': date_dispute,
                                'type': type_dispute,
                                'action': action_dispute
                            })
                        except Exception:
                            disclosure_details.append({
                                'date': None,
                                'type': None,
                                'action': None
                            })

                # Append all data to the dataset
                dataset.append({
                    'name': name if name else 'NA',
                    'disclosure_count': disclosure_count if disclosure_count is not None else 'NA',
                    'years_of_experience': years_of_experience if years_of_experience is not None else 'NA',
                    'firms_count': firms_count if firms_count is not None else 'NA',
                    'organization_name': organization_name if organization_name else 'NA',
                    'address': address if address else 'NA',
                    'disclosure_details': disclosure_details if disclosure_details else 'NA'
                })

            except Exception as e:
                print(f"Error extracting data for a broker: {e}")
                
            # Go back to the main page to get the next broker
            driver.back()

        # Move to the next page
        try:
            next_page_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/bc-root/div/bc-search-results-page/bc-search-results/div/investor-tools-search-results-template/div[last()]/div[3]/div/investor-tools-pager/div/div[4]/button'))
            )
            next_page_button.click()
            print("Moved to the next page.")
            time.sleep(2)
        except Exception:
            print("No more pages. Exiting.")
            break
finally:
    driver.quit()











            

