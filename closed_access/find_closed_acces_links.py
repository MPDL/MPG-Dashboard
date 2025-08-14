import re

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

def find_a_tags(response_text, response_url):
    '''Get all a tags with an href. 
    Return all href whose a tag's text or its preceding tag's text contain 'pdf'.
    If the href has a relative link, prepend the page's domain.
    '''
    
    soup = BeautifulSoup(response_text, 'html.parser')
    a_tags = soup.find_all('a', href=True)
    
    pdf_links = []
    for i, t in enumerate(a_tags):
        t_href = t['href']
        t_descendants = [d for d in t.descendants if isinstance(d, str)]
        t_text = ''.join(t_descendants)
        p_sibling = t.find_previous_sibling()
        p_sibling_descendants = p_sibling.descendants if p_sibling is not None else []
        p_sibling_descendants = [d for d in p_sibling_descendants if isinstance(d, str)]
        p_sibling_text = ''.join(p_sibling_descendants)
        
        if ('pdf' in t_text.lower() or 'pdf' in p_sibling_text.lower()):
            absolute_path = re.compile(r'https?:\/\/\S+').match(t_href) # href starts with http(s)://
            if absolute_path: 
                pdf_links.append(t_href)
            else:
                match = re.compile(r'https?:\/\/(www\.)?([^\/]+)').match(response_url) # get main page from response_url
                if match:
                    prefix = match.group()
                    a_path = f'{prefix}{t_href}' if t_href.startswith('/') else f'{prefix}/{t_href}'
                    pdf_links.append(a_path)

        if i > 1000:
            break

    return pdf_links

def find_a_tags_selenium(driver, current_url):
    '''Selenium workflow. Get all a tags with an href. 
    Return all href whose a tag's text or its preceding tag's text contain 'pdf'.
    If the href has a relative link, prepend the page's domain.
    '''

    a_tags = driver.find_elements(By.TAG_NAME, 'a')
    pdf_links = []
    
    # Find all a tags and save href if pdf in tag.text
    for i, tag in enumerate(a_tags):
        try:
            t_href = tag.get_attribute('href')
            if t_href is None:
                continue
            if 'pdf' in tag.text.lower():
                absolute_path = re.compile(r'https?:\/\/\S+').match(t_href) # href starts with http(s)://
                if absolute_path:
                    pdf_links.append(t_href)
                else:
                    match = re.compile(r'https?:\/\/(www\.)?([^\/]+)').match(current_url) # get main page from home_url
                    if match:
                        prefix = match.group()
                        a_path = f'{prefix}{t_href}' if t_href.startswith('/') else f'{prefix}/{t_href}'
                        pdf_links.append(a_path)
        
        except Exception as e:
            print(f'    selenium - Error finding a tags: {e}')
            continue

        if i > 1000:
            break

    if len(pdf_links) == 0:
        # Find all <a> tags preceded by any element that contains 'pdf' in their text
        # https://www.browserstack.com/guide/find-elements-by-text-in-selenium-with-python
        more_a_tags = driver.find_elements(By.XPATH, "//*[contains(text(), 'PDF') or contains(text(), 'pdf')]/following-sibling::a")

        for i, tag in enumerate(more_a_tags):
            try:
                t_href = tag.get_attribute('href')
                if t_href is None:
                    continue
                absolute_path = re.compile(r'https?:\/\/\S+').match(t_href) # href starts with http(s)://
                if absolute_path:
                    pdf_links.append(t_href)
                else:
                    match = re.compile(r'https?:\/\/(www\.)?([^\/]+)').match(current_url) # get main page from home_url
                    if match:
                        prefix = match.group()
                        a_path = f'{prefix}{t_href}' if t_href.startswith('/') else f'{prefix}/{t_href}'
                        pdf_links.append(a_path)
            
            except Exception as e:
                print(f'    selenium - Error finding a tags preceded by pdf: {e}')
                continue

            if i > 1000:
                break
    
    return pdf_links

def find_paper_url_selenium(home_url, driver):
    '''Selenium workflow. Get all pdf links found in home_url. '''

    if home_url.endswith('.pdf'):
        return [home_url]

    ignored_exceptions=(NoSuchElementException,StaleElementReferenceException,)

    # 1. Check if home_url is itself a pdf
    driver.get(home_url)
    driver.implicitly_wait(20)  # Use implicit wait to allow time for elements to load

    # 2. Search for all http(s) links ending with '.pdf' or '.pdf#page={number}'
    page_source = driver.page_source
    pdf_links = re.findall(re.compile(r'https?:\/\/[^\s",{}\[\]]+?\.pdf(?:#page=\d+)?'), page_source) # matches http(s)://{any character but whitespace " , { } [ ]}.pdf(#page={number})

    # 3. Search for all a tags with an href and append href links if
    # a.string contains 'pdf' (case insensitive) or
    # preceding sibling is any element whose string contains 'pdf' (case insensitive)
    # Mind relative paths
    if len(pdf_links) == 0:
        current_url = driver.current_url
        pdf_links = find_a_tags_selenium(driver, current_url)

    if len(pdf_links) > 0:
        pdf_links = list(set(pdf_links))
        return pdf_links
    
    return False

def find_paper_url(home_url, driver):
    '''Get all pdf links found in home_url. '''

    response = requests.get(home_url)
    if response.status_code < 400:
        
        # 1. Check if home_url redirects to pdf or is itself a pdf 
        response_url = response.url
        content_type = response.headers['Content-Type']
        if re.compile(r'https?:\/\/[^\s]+?\.pdf(?:#page=\d+)?').match(response_url) or 'application/pdf' in content_type:
            return [response_url]

        # 2. Search for all http(s) links ending with '.pdf' or '.pdf#page={number}'
        pdf_links = re.findall(re.compile(r'https?:\/\/[^\s",{}\[\]]+?\.pdf(?:#page=\d+)?'), response.text) # matches http(s)://{any character but whitespace " , { } [ ]}.pdf(#page={number})
                
        # 3. Search for all a tags with an href and append href links if
        # a.string contains 'pdf' (case insensitive) or
        # preceding sibling is any element whose string contains 'pdf' (case insensitive)
        # Mind relative paths
        if len(pdf_links) == 0:
            pdf_links = find_a_tags(response.text, response_url)

        if len(pdf_links) > 0:
            pdf_links = list(set(pdf_links))
            return pdf_links

    # If request with library "requests" did not work or no pdf link was found, try out selenium workflow
    pdf_links_selenium = find_paper_url_selenium(home_url, driver)
    if isinstance(pdf_links_selenium, list) and len(pdf_links_selenium) > 0:
        return pdf_links_selenium

    file = open('NotCapableOfAccessing.txt', 'a')
    file.write(home_url + '\n')
    file.close()
    
    return False


# old version
# def find_paper_url(home_url, driver):
# # Navigate to the URL and # print the title

#     if home_url.endswith('.pdf'):
#         return [home_url]
    
#     # print(f'    Fetching URL: {home_url}')
#     ignored_exceptions=(NoSuchElementException,StaleElementReferenceException,)

#     driver.get(home_url)
#     driver.implicitly_wait(20)  # Use implicit wait to allow time for elements to load

#     # Find all <a> tags on the page
#     a_tags = driver.find_elements(By.TAG_NAME, 'a')
#     print(f'    Found {len(a_tags)} <a> tags on the page.')
#     # Print the href attributes and the text of all <a> tags
#     pdf_links = []
    
#     counter = 0
#     for tag in a_tags:
#         counter += 1
#         try:
#             if tag.get_attribute('href') is None:
#                 continue
#             if tag.get_attribute('href').endswith('pdf') or tag.text.lower().startswith == 'pdf':
#                 # print(f'    Text: {tag.text}, Href: {tag.get_attribute('href')}')
                
#                 pdf_links.append(tag.get_attribute('href'))
#         except Exception as e:
#             print(f'    error: {e}')
#             continue
#         if counter > 1000:
#             break

#     if len(pdf_links) > 0:
#         return pdf_links
    
#     file = open('NotCapableOfAccessing.txt', 'a')
#     file.write(home_url + '\n')
#     file.close()
#     return False