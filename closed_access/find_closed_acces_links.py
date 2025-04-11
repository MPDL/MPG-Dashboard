from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


def find_paper_url(home_url, driver):
# Navigate to the URL and print the title

    if home_url.endswith('.pdf'):
        return home_url
    print(f"Fetching URL: {home_url}")
    ignored_exceptions=(NoSuchElementException,StaleElementReferenceException,)

    driver.get(home_url)
    driver.implicitly_wait(20)  # Use implicit wait to allow time for elements to load

    # Find all <a> tags on the page
    a_tags = driver.find_elements(By.TAG_NAME, 'a')
    print(f"Found {len(a_tags)} <a> tags on the page.")
    # Print the href attributes and the text of all <a> tags
    counter = 0
    for tag in a_tags:
        counter += 1
        if tag.get_attribute('href') is None:
            continue
        if tag.get_attribute('href').endswith('pdf') or tag.text.lower().startswith == 'pdf':
            print(f"Text: {tag.text}, Href: {tag.get_attribute('href')}")
            
            return tag.get_attribute('href')
        if counter > 1000:
            break
    file = open('NotCapabaleOfAccessing.txt', 'a')
    file.write(home_url + '\n')
    file.close()
    return False


def quit_driver(driver):
    driver.quit()