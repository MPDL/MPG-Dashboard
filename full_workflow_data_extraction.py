import json
import time
from concurrent import futures

from data_extraction.locator_urls import find_pdf_urls
from data_extraction.openalex import (
    get_openalex_entry_based_on_doi,
    get_openalex_entry_based_on_title,
    process_openalex_entry,
)
from data_extraction.PuRe import get_publications_for_time_period
from db.db_manager import DatabaseManager


def full_workflow(
    doi,
    title,
    publication_year,
    pure_id,
    genre,
    publisher,
    publication_date,
    pdf_urls,
    locator_urls,
    oa_status,
    db_manager,
):
    """Enrich publication with data from OpenAlex: get open access status, and pdf and locator link(s).

    If PuRe entry has a DOI, use it to request OpenAlex, otherwise use publication's title and publication year.
    Then save publication's data (PuRe data + OpenAlex enrichment) in database for further processing.
    """

    # check if the publication is already in the database
    if doi is not None:
        if db_manager.check_publication_exists_by_name_and_year(pure_id):
            print('    publication exists in DB')
            return
        else:
            openalex_entry = get_openalex_entry_based_on_doi(doi)
    else:
        if db_manager.check_publication_exists_by_name_and_year(pure_id):
            print('    publication exists in DB')
            return

        openalex_entry = get_openalex_entry_based_on_title(title, publication_year)

    print('openalex_entry:')
    print(json.dumps(openalex_entry, indent=2))

    # iterate over openalex json to get pdf and locator urls, and oa status
    processed_openalex_entry = process_openalex_entry(openalex_entry, pdf_urls, locator_urls)

    print('processed_openalex_entry:')
    print(json.dumps(processed_openalex_entry, indent=2))

    # if no pdf url was found neither in PuRe nor in OpenAlex, look for pdf url in locator urls (landing pages)
    if processed_openalex_entry is not None:
        print('entered processed_openalex_entry is not None')
        pdf_urls.extend(processed_openalex_entry.get('pdf_urls', []))
        locator_urls.extend(processed_openalex_entry.get('locator_urls', []))

    print('pdf_urls: ', json.dumps(pdf_urls, indent=2))
    print('locator_urls: ', json.dumps(locator_urls, indent=2))
    if len(pdf_urls) == 0 and len(locator_urls) > 0:
        print('entered len(pdf_urls) == 0 and len(locator_urls) > 0')
        locator_pdf_urls = search_locator_urls(locator_urls)
        print(f'Locator PDF URLs found by search_locator_urls(): {json.dumps(locator_pdf_urls)}')
        pdf_urls.extend(locator_pdf_urls)

    publication = {
        'pure_title': title,
        'openalex_title': processed_openalex_entry.get('title') if isinstance(processed_openalex_entry, dict) else None,
        'pure_id': pure_id,
        'openalex_id': processed_openalex_entry.get('id') if isinstance(processed_openalex_entry, dict) else None,
        'doi': doi,
        'pure_oa_status': oa_status,
        'openalex_oa_status': processed_openalex_entry.get('oa_status')
        if isinstance(processed_openalex_entry, dict)
        else None,
        'openalex_oa': processed_openalex_entry.get('oa') if isinstance(processed_openalex_entry, dict) else None,
        'manual_download': False,
        'discoverable': len(pdf_urls) > 0,
        'pure_genre': genre,
        'openalex_type': processed_openalex_entry.get('type') if isinstance(processed_openalex_entry, dict) else None,
        'crossref_type': processed_openalex_entry.get('type_crossref')
        if isinstance(processed_openalex_entry, dict)
        else None,
        'publication_year': publication_year,
        'publication_date': publication_date,
        'publisher': publisher,
    }

    print('publication: ')
    print(json.dumps(publication, indent=2))

    print('pdf_links:')
    print(json.dumps(pdf_urls, indent=2))

    # add publication to publications table in the database -> id primary key
    id = db_manager.add_publication(publication)

    # add pdf links to the publication_pdf_links table in the database
    if len(pdf_urls) > 0:
        for i, pdf_dict in enumerate(pdf_urls):
            pdf_url_id = f'{id}_{i}'
            db_manager.add_pdf_url(pdf_url_id, id, **pdf_dict)

    # # save_url_to_file(openalex_urls[openalex_title], path, article_title+'.pdf')


def search_locator_urls(locator_urls):
    """For publications without a pdf_link (neither in PuRe not in OpenAlex),
    use their landing page to search for pdf links.

    """
    print(f'!!!!!! search_locator_urls() - {len(locator_urls)} locator urls')
    print(f'locator_urls: {[url_dict["locator_url"] for url_dict in locator_urls]}')

    pdf_urls = []

    for locator_dict in locator_urls[:1]:
        locator_url = locator_dict.get('locator_url')
        if locator_url is None:
            continue

        urls = find_pdf_urls(locator_url)
        if not urls:
            continue

        _pdf_urls = [{**locator_dict, 'pdf_url': u} for u in urls]
        pdf_urls.extend(_pdf_urls)

    return pdf_urls


def process_publications(publication, db_manager):
    """Retrieve all relevant metadata accessible via PuRe."""

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


def full_workflow_time_period(start_date, end_date):
    """Request PuRe publications for the given dates and request
    OpenAlex for each one of them to get their open access status and pdf links."""

    db_manager = DatabaseManager()
    db_manager.connect()

    publications = get_publications_for_time_period(start_date, end_date)
    print(f'number of PuRe publications: {len(publications)}')
    publications = publications[5045:]
    # check that this pure_id exists: item_3569620

    for i, publication in enumerate(publications):
        # print('')

        print(f'    processing publication no. {i}')
        print(json.dumps(publication, indent=2))

        print('')
        print('')

        if publication == {}:
            print('    empty entry from PuRe -> skipping')
            print('    ------------------------------')
            print('')
            continue

        full_workflow(**publication, db_manager=db_manager)
        print('    ------------------------------')
        print('')

        if i % 30 == 0:
            time.sleep(5)

        # time.sleep(20)

    db_manager.close()


def full_workflow_time_period_parallel(start_date, end_date, num_workers=1):
    """This runs the full workflow in parallel iterating through all publications
    associated with Max Planck for a given time period.
    It checks whether the publication is already in the database and if not it,
    tries to extract the link for the pdf.
    """

    db_manager = DatabaseManager()
    db_manager.connect()

    publications = get_publications_for_time_period(start_date, end_date)

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
    # full_workflow_time_period_parallel('2021-01-01', '2021-02-05')
    full_workflow_time_period('2023-01-01', '2023-12-31')

    # pure_ids = [
    #     "item_3673842",
    #     "item_3668209"
    # ]

    # db_manager = DatabaseManager()
    # db_manager.connect()

    # for id_ in pure_ids:
    #     print(f'    deleting id_: {id_}')
    #     db_manager.delete_pdf_urls_by_id(id_)

    # db_manager.close()
