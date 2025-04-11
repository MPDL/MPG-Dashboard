from openalex import iterate_over_openalex_json, string_transformation, fetch_results_based_on_article_name, filter_for_json_for_article_name_and_year, fetch_result_based_on_doi
from closed_access.find_closed_acces_links import find_paper_url, quit_driver
from PuRe import get_paper_for_time_period
from pdf_downlaoder import save_url_to_file
from db import DatabaseManager
import pandas as pd
import multiprocessing as mp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from concurrent import futures
import time


def full_workflow(doi, title, publishing_year, db_manager, object_id, genre, publisher, publication_date):
    article_entry = None
    discoverable = True
    print("DOI: ", doi, "Title: ", title, "Year: ", publishing_year, "Object_id: ", object_id)

    # check if the publication is already in the database
    if doi is not None:
        if db_manager.check_publication_exists_by_name_and_year(object_id):  
            return
        else:
            article_entry = doi_available_workflow(doi)
    else:
        if db_manager.check_publication_exists_by_name_and_year(object_id):
            print("in DB vorhanden")
            return
        article_entry = title_only_available_workflow(title, publishing_year)
    
    #iterate_over_openalex_json to get pdf_urls and oA_status 
    article_urls, article_name, oA = iterate_over_openalex_json(article_entry)

    # if the article could not be found in OpenAlex, we set discoverable to False
    if article_urls == None:
        discoverable = False

    # if the article is not open access, we try to find the pdf link using the closed access workflow using the links of OpenAlex leading to the page where the pdf can be downloaded
    if not oA and discoverable:
        paper_urls = closed_access_workflow(article_urls[article_name])
        article_urls[article_name] = paper_urls
    
    publication = {
    "object_id": object_id,
    "title": title,
    "doi": doi,
    "year": publishing_year,
    "open_access": oA,
    "manual_download": False,
    "discoverable": discoverable,
    "genre": genre,
    "publisher": publisher,
    "publication_date": publication_date,
    }

    print(publication)

    # add publication to publications table in the database -> id primary key
    id = db_manager.add_publication(publication)

    # add pdf links to the publication_pdf_links table in the database
    if discoverable:
        for pdf_link in article_urls[article_name]:
            db_manager.add_pdf_link(id, pdf_link)

    #save_url_to_file(article_urls[article_name], path, article_title+".pdf")

# get OpenAlex parameters using the doi of the article
def doi_available_workflow(doi):
    article_entry = fetch_result_based_on_doi(doi)
    return article_entry

# get OpenAlex parameters using the title and the publishing year of the article
def title_only_available_workflow(title, publishing_year):
    json_result = fetch_results_based_on_article_name(title, publishing_year)
    article_entry = filter_for_json_for_article_name_and_year(title, publishing_year, json_result)
    return article_entry


def closed_access_workflow(article_urls):
    paper_urls = []
    chromedriver_path = r"C:\Users\matthies\Documents\Collections\Dashboard\paper\closed_access\chromedriver\chromedriver.exe"
    service2 = Service(executable_path=chromedriver_path)
    # Optional Chrome options
    options = Options()
    #options.add_argument("--headless")  # Uncomment to run Chrome in headless mode
    options.add_argument("--log-level=3")  # Suppress most console logs
    # Initialize the WebDriver with the local chromedriver.exe
    print("Cloased Access Workflow")
    driver = webdriver.Chrome(service=service2, options=options)	
    for article_url in article_urls:
        paper_url = find_paper_url(article_url, driver)
        print("Paper_url " ,paper_url)
        if paper_url == False:
            continue
        paper_urls.append(paper_url)
    time.sleep(10)
    quit_driver(driver)
    return paper_urls



# retrieves all relevant metadata accessible via PuRe 
def process_publications(publication, db_manager):
    # Check if the publication is an empty dictionary
    if publication == {}:
        return
    # Extract relevant fields from the publication

    doi = publication["doi"]
    title = publication["title"]
    publishing_year = publication["publishing_year"]
    # Call the full workflow for each publication
    object_id = publication["object_id"]
    genre = publication["genre"]
    publisher = publication["publisher"]
    publication_date = publication["publication_date"]
    #print(doi, title, publishing_year, object_id)
    full_workflow(doi, title, publishing_year, db_manager, object_id, genre, publisher, publication_date)



def full_workflow_time_period(start_date, end_date):
    
    db_manager = DatabaseManager()
    db_manager.connect()
    #publications= get_paper_for_time_period(start_date, end_date)

    publications= get_paper_for_time_period(start_date, end_date)
    for publication in publications:
        if publication == {}:
            continue
        process_publications(publication, db_manager)
    
    db_manager.close()


# This runs the full workflow in parallel iterating through all publications associated with Max Planck for a given time period
# It checks wether the publication is already in the database and if not it tries to extract the link for the pdf 
def full_workflow_time_period_parallel(start_date, end_date, num_workers=1):

    db_manager = DatabaseManager()
    db_manager.connect()
    publications= get_paper_for_time_period(start_date, end_date)

    print("Connected to the database")
    e = futures.ThreadPoolExecutor(max_workers=num_workers)
    print(len(publications))
    for publication in publications:
        if publication == {}:
            continue
        e.submit(process_publications, publication, db_manager)
    e.shutdown(wait=True)
    db_manager.close()
    


if __name__ == "__main__":
    #full_workflow_time_period_parallel("2021-01-01", "2021-02-05")
    full_workflow_time_period("2021-01-01", "2021-02-05")
