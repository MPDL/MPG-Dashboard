import time
import json

from concurrent import futures

from openalex import (
    iterate_over_openalex_json, 
    fetch_results_based_on_article_name, 
    filter_json_for_article_name_and_year, 
    fetch_result_based_on_doi
)
from closed_access.find_closed_acces_links import find_paper_url
from PuRe import get_paper_for_time_period
from db import DatabaseManager
from selenium_driver.selenium_driver import instanciate_driver, quit_driver

def full_workflow(doi, title, publication_year, db_manager, pure_id, genre, publisher, publication_date):
    '''Enrich publication with data from OpenAlex: get open access status, pdf link(s). 
    If PuRe entry has a DOI, use it to request OpenAlex, otherwise use publication's title and publication year. 
    Then save publication's data (PuRe data + OpenAlex enrichment) in database for further processing.
    '''
    
    article_entry = None
    discoverable = True
    print(f'    DOI: {doi}, pure_id: {pure_id}')
    print(f'    title: {title}')

    # pure_ids = ["item_3309388"]
    # for id_ in pure_ids:
    #     print(f'    deleting id_: {id_}')
    #     db_manager.delete_pdf_links_by_id(id_)

    # check if the publication is already in the database
    if doi is not None:
        if db_manager.check_publication_exists_by_name_and_year(pure_id):  
            print(f'    publication exists in DB')
            return
        else:
            print(f'    getting article_entry by doi')
            article_entry = fetch_result_based_on_doi(doi)
    else:
        if db_manager.check_publication_exists_by_name_and_year(pure_id):
            print(f'    publication exists in DB')
            return
        
        print(f'    getting article_entry by title and publication_year')
        article_entry = title_only_available_workflow(title, publication_year)
    
    # iterate over openalex json to get pdf_urls and oA_status
    # oA is True if pdf_link is given by OpenAlex (this does not always match OpenAlex's open access status)
    article_urls, article_name, oA = iterate_over_openalex_json(article_entry)
    print(f'    open access: {oA}')
    print(f'    article_urls found in OpenAlex: {article_urls}')

    # if the article could not be found in OpenAlex, we set discoverable to False
    if article_urls == None:
        discoverable = False

    # if the article is not open access, we try to find the pdf link using the closed access workflow 
    # using the links of OpenAlex to the landing page where the pdf can be downloaded
    if not oA and discoverable:
        paper_urls = closed_access_workflow(article_urls[article_name])
        print(f'    paper_urls found with closed_access_workflow: {paper_urls}')
        article_urls[article_name] = paper_urls
    
    publication = {
        'pure_title': title,
        'openalex_title': article_name,
        'pure_id': pure_id,
        'openalex_id': article_entry.get('id') if isinstance(article_entry, dict) else None,
        'doi': doi,
        'open_access': oA,
        'manual_download': False,
        'discoverable': discoverable,
        'genre': genre,
        'publication_year': publication_year,
        'publication_date': publication_date,
        'publisher': publisher,
    }

    # print('')
    # print(json.dumps(publication, indent=2))

    # add publication to publications table in the database -> id primary key
    id = db_manager.add_publication(publication)

    # add pdf links to the publication_pdf_links table in the database
    if discoverable:
        for pdf_link in article_urls[article_name]:
            db_manager.add_pdf_link(id, pdf_link)

    #save_url_to_file(article_urls[article_name], path, article_title+'.pdf')

def title_only_available_workflow(title, publication_year):
    '''Get OpenAlex work entry by title and publishing year. '''
    
    json_result = fetch_results_based_on_article_name(title, publication_year)
    article_entry = filter_json_for_article_name_and_year(title, publication_year, json_result)
    return article_entry


def closed_access_workflow(article_urls):
    '''For OpenAlex work entries without a pdf_link, use their landing page to search for pdf links. '''
    
    urls = []
    driver = instanciate_driver()

    for article_url in article_urls:
        paper_urls = find_paper_url(article_url, driver)
        if paper_urls == False:
            continue
        urls.extend(paper_urls)
    
    time.sleep(10)
    quit_driver(driver)
    
    return urls


def process_publications(publication, db_manager):
    '''Retrieve all relevant metadata accessible via PuRe. '''    
    
    # Check if the publication is an empty dictionary
    if publication == {}:
        return
    
    # Extract relevant fields from the publication
    doi = publication['doi']
    title = publication['title']
    publication_year = publication['publication_year']
    pure_id = publication['pure_id']
    genre = publication['genre']
    publisher = publication['publisher']
    publication_date = publication['publication_date']
    
    # Call the full workflow for each publication
    full_workflow(doi, title, publication_year, db_manager, pure_id, genre, publisher, publication_date)

def _count_genres(publications):
    '''Create dict with counts for each genre in a list of publications. '''

    with open('genre_count_from_2000_01_01.json', 'r') as f:
        try:
            genres = json.load(f)
            print(f'    genres exists, genres["ARTICLE"]: {genres["ARTICLE"]}')
        except Exception as e:
            genres = {}
            print(f'    genres does not exist yet, error: {e}')
    for publication in publications:
        if publication == {}:
            continue

        if publication['genre'] in genres.keys():
            genres[publication['genre']] += 1
        else:
            genres[publication['genre']] = 1
    
    with open('genre_count_from_2000_01_01.json', 'w') as f:
        json.dump(genres, f)

def full_workflow_time_period(start_date, end_date):
    '''Request PuRe publications for the given dates and request
    OpenAlex for each one of them to get their open access status and pdf links. '''
    
    db_manager = DatabaseManager()
    db_manager.connect()

    publications= get_paper_for_time_period(start_date, end_date)
    publications = publications[:100]

    # _count_genres(publications)

    for i, publication in enumerate(publications):
        print('')
        print(f'    processing publication no. {i}')

        if publication == {}:
            print(f'    empty entry from PuRe -> skipping')
            print(f'    ------------------------------')
            print('')
            continue

        full_workflow(**publication, db_manager=db_manager)
        print(f'    ------------------------------')
        print('')

        if i % 30 == 0:
            time.sleep(5)
   
    db_manager.close()

def full_workflow_time_period_parallel(start_date, end_date, num_workers=1):
    '''This runs the full workflow in parallel iterating through all publications 
    associated with Max Planck for a given time period.
    It checks whether the publication is already in the database and if not it, 
    tries to extract the link for the pdf.
    '''

    db_manager = DatabaseManager()
    db_manager.connect()

    publications= get_paper_for_time_period(start_date, end_date)

    print('Connected to the database')
    e = futures.ThreadPoolExecutor(max_workers=num_workers)
    print(f'    {len(publications)}')
    for publication in publications:
        if publication == {}:
            continue
        e.submit(process_publications, publication, db_manager)
    e.shutdown(wait=True)
    db_manager.close()    


if __name__ == '__main__':
    #full_workflow_time_period_parallel('2021-01-01', '2021-02-05')
    full_workflow_time_period('2021-01-01', '2021-01-01')
