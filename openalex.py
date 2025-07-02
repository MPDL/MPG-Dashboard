import os
import re

import dotenv
import requests
import html
from Levenshtein import distance as lev

dotenv.load_dotenv()

def fetch_result_based_on_doi(doi):
    '''Get OpenAlex work entry by doi. '''
    response = requests.get(f'https://api.openalex.org/works/{doi}?mailto={os.getenv("REQUEST_MAIL")}&select=id,title,publication_year,locations')
    
    try:
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'    Error fetching openalex article data by doi, error: {e}')
        return False

def fetch_results_based_on_article_name(article_name, publication_year):
    '''Get OpenAlex work entry/entries by article name and publication year. '''
    
    article_name = article_name.replace(" ", "+").replace(",","").replace("++","+")
    
    response = requests.get(
        f'https://api.openalex.org/works?sort=relevance_score:desc&per_page=10&mailto={os.getenv("REQUEST_MAIL")}&select=id,title,publication_year,locations&filter=default.search:{article_name},publication_year:{publication_year}'
    )
    response_without_year = requests.get(
        f'https://api.openalex.org/works?sort=relevance_score:desc&per_page=10&mailto={os.getenv("REQUEST_MAIL")}&select=id,title,publication_year,locations&filter=default.search:{article_name}'
    )

    try:
        response.raise_for_status()
        results = response.json().get('results', [])

        response_without_year.raise_for_status()
        results.extend(response_without_year.json().get('results', []))
        return results
    
    except Exception as e:
        print(f'    Error fetching openalex article data by title and year, error: {e}')
        return False
    

def filter_json_for_article_name_and_year(article_name, publication_year, json):
    '''Search for correct article in OpenAlex's response based on the article name and the publishing year'''
    
    if json == False or len(json) == 0:
        return False
    
    word_count_article_name = len(article_name.split()) if isinstance(article_name, str) else 0
    publication_year = int(publication_year)
    
    for entry in json:
        if entry['title'] is not None:
            word_count_entry_title = len(entry["title"].split()) if isinstance(entry["title"], str) else 0
            
            entry_title = string_transformation(entry["title"])
            article_name = string_transformation(article_name)
            
            # If levenshtein distance is small enough (i.e. titles are similar enough) and 
            # publication year is in acceptable range
            # return entry
            if (
                lev(entry_title, article_name)<=2 and 
                entry["publication_year"] >= publication_year-3 and 
                entry["publication_year"] <= publication_year+3
            ):
                return entry
            
            # If any of the title (PuRe's vs OpenAlex entry's) is a substring of the other and 
            # publication year is in acceptable range
            # return entry
            min_word_count = min(word_count_article_name, word_count_entry_title)
            if (
                word_count_article_name > 0 and 
                word_count_entry_title > 0 and
                # the difference in word count must be smaller than the smallest word count
                abs(word_count_article_name - word_count_entry_title) < min_word_count and
                (entry_title in article_name or article_name in entry_title) and
                entry["publication_year"] >= publication_year-3 and 
                entry["publication_year"] <= publication_year+3
            ):
                return entry
    
    return False

# -- Deprecated --
def return_result_based_on_article_name_and_publication_year(article_name, publication_year):
    json_result = fetch_results_based_on_article_name(article_name, publication_year)
    article_entry = filter_json_for_article_name_and_year(article_name, publication_year, json_result)
    return article_entry


def iterate_over_openalex_json(open_alex_json):
    '''Extract pdf links, oA status and article name from OpenAlex's response. '''    
    
    # if no OpenAlex json is found, return None for the parameters
    if open_alex_json == False:
        return None, None, None
    
    pdf_urls = []
    location_urls = []
    pdf_dict_name_urls = {} 
    location_dict_name_urls = {}
    article_name = open_alex_json["title"]

    #get pdf urls for open access articles
    for location in open_alex_json["locations"]:
        is_oa = location['is_oa']
        if not is_oa and location["pdf_url"] is not None:
            print(f'    location marked as is_oa == {is_oa} BUT pdf_url = {location["pdf_url"]}')
        
        if location["pdf_url"] is not None:
            pdf_urls.append(location["pdf_url"])

    # get landing page urls for closed access articles
    if len(pdf_urls) == 0:
        print(f'    Closed Access: {article_name}')
        for location in open_alex_json["locations"]:
            if location["landing_page_url"] is not None:
                location_urls.append(location["landing_page_url"])
    
    if len(location_urls) > 0:
        location_dict_name_urls[article_name] = location_urls
        return location_dict_name_urls, article_name, False
    
    pdf_dict_name_urls[article_name] = pdf_urls
    return pdf_dict_name_urls, article_name, True

def string_transformation(string: str):
    '''Unescape string input and afterward keep only lowercased alphanumeric characters.
    
    Motivation: html strings can contain escaped values that contain alphanumeric characters.
    (A&lt;sub&gt;&amp;infin;&lt;/sub&gt;,2) is the escaped version of: (A<sub>∞</sub>,2).
    Skipping unescaping means transforming (A&lt;sub&gt;&amp;infin;&lt;/sub&gt;,2) 
    to altsubgtampinfinltsubgt2
    instead of asubsub2
    '''
    
    if not isinstance(string, str):
        print(f'    string_transformation got {string} with type {type(string)} instead of a string')
        return ''
    
    html_unescaped_str = html.unescape(string)
    html_unescaped_str = html.unescape(html_unescaped_str)
    transformed_string = re.sub('[^A-Za-z0-9]+', '', html_unescaped_str)
    lower_case_transformed_string = transformed_string.lower()
    
    return lower_case_transformed_string
 
