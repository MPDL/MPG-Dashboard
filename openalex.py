import requests
import pandas as pd
from pdf_downlaoder import save_url_to_file, save_all_urls_to_files
import re
from Levenshtein import distance as lev
from pathlib import Path

# do OpenAlex search request based on the article name
def fetch_results_based_on_article_name(article_name, publishing_year):
    article_name = article_name.replace(" ", "+")
    article_name = article_name.replace(",","")
    article_name = article_name.replace("++","+")
    
    #print(article_name)
    #print("https://api.openalex.org/works?page=1&filter=default.search:"+article_name+"&sort=relevance_score:desc&per_page=10")
    response = requests.get("https://api.openalex.org/works?page=1&filter=default.search:"+article_name+",publication_year:"+publishing_year+"&sort=relevance_score:desc&per_page=10&mailto=matthiesen@mpdl.mpg.de")
    #print("https://api.openalex.org/works?page=1&filter=default.search:"+article_name+",publication_year:"+publishing_year+"&sort=relevance_score:desc&per_page=10&mailto=matthiesen@mpdl.mpg.de")
    response_without_year = requests.get("https://api.openalex.org/works?page=1&filter=default.search:"+article_name+"&sort=relevance_score:desc&per_page=10&mailto=matthiesen@mpdl.mpg.de")
    full_dict = response.json()
    if response.status_code == 403:
        print("403 Forbidden: ", response.url)
        return False
    response_without_year = response_without_year.json()
    full_dict["results"].extend(response_without_year["results"])
    #print(len(full_dict["results"]))
    return full_dict

# search for correct article in the json response based on the article name and the publishing year
def filter_for_json_for_article_name_and_year(article_name, publishing_year, json):

    if json == False:
        return False
    publishing_year = int(publishing_year)
    for entry in json["results"]:
        entry_title= string_transformation(entry["title"])
        article_name = string_transformation(article_name)
        
        if lev(entry_title, article_name)<=2 and entry["publication_year"] >= publishing_year-3 and entry["publication_year"] <= publishing_year+3:
            return entry
    return False

# -- Deprecated --
def return_result_based_on_article_name_and_publishing_year(article_name, publishing_year):
    json_result = fetch_results_based_on_article_name(article_name, publishing_year)
    article_entry = filter_for_json_for_article_name_and_year(article_name, publishing_year, json_result)
    return article_entry


# extract pdf links, oA status and article name from the OpenAlex json response
def iterate_over_openalex_json(open_alex_json):
    # if no OpenAlex json is found, return None for the parameters
    if open_alex_json == False:
        return None, None, None
    pdf_urls = []
    location_urls = []
    pdf_dict_name_urls = {} 
    location_dict_name_urls = {}
    #article_name = string_transformation(open_alex_json["title"])

    article_name = open_alex_json["title"]

    #get pdf urls for open access articles
    for location in open_alex_json["locations"]:
        if location["pdf_url"] is not None:
            pdf_urls.append(location["pdf_url"])

    # get landing page urls for closed access articles
    if len(pdf_urls) == 0:
        print("Closed Access: ", article_name)
        for location in open_alex_json["locations"]:
            if location["landing_page_url"] is not None:
                location_urls.append(location["landing_page_url"])
    pdf_dict_name_urls[article_name] = pdf_urls
    if len(location_urls) != 0:
        location_dict_name_urls[article_name] = location_urls
        return location_dict_name_urls, article_name, False
    return pdf_dict_name_urls, article_name, True

def string_transformation(string: str):
    transformed_string = re.sub('[^A-Za-z0-9]+', '', string)
    lower_case_transformed_string = transformed_string.lower()
    return lower_case_transformed_string

# return the json of the OpenAlex request using the doi as parameter
def fetch_result_based_on_doi(doi):
    response = requests.get("https://api.openalex.org/works/"+doi)
    #print(response.status_code)
    if response.status_code == 404:
        print("No article found for DOI: ", doi)
        return False
    return response.json()
 
