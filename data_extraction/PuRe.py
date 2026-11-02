import json
import logging

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_query_string(start_date, end_date, per_page=2000, index=1):
    """Create the query string for the PuRe API."""
    query = {
        'query': {
            'bool': {
                'must': [
                    {'term': {'publicState': {'value': 'RELEASED'}}},
                    {'term': {'versionState': {'value': 'RELEASED'}}},
                    {
                        'bool': {
                            'must': [
                                {
                                    'bool': {
                                        'should': [
                                            {
                                                'range': {
                                                    'metadata.datePublishedOnline': {
                                                        'gte': start_date + '||/d',
                                                        'lte': end_date + '||/d',
                                                    }
                                                }
                                            },
                                            # v = metadata.datePublishedInPrint | metadata.dateAccepted |
                                            #     metadata.dateSubmitted | metadata.dateModified | metadata.dateCreated
                                            # {
                                            #   'range': {
                                            #       '{v}': {
                                            #           'gte':start_date+'||/d',
                                            #           'lte':end_date+'||/d',
                                            #       }
                                            #   }
                                            # },
                                        ]
                                    }
                                },
                                {
                                    'bool': {
                                        'should': [
                                            {'term': {'metadata.genre': {'value': 'BOOK'}}},
                                            {'term': {'metadata.genre': {'value': 'BOOK_ITEM'}}},
                                            {'term': {'metadata.genre': {'value': 'CONFERENCE_PAPER'}}},
                                            {
                                                'term': {
                                                    'metadata.genre': {'value': 'CONTRIBUTION_TO_COLLECTED_EDITION'}
                                                }
                                            },
                                            {'term': {'metadata.genre': {'value': 'ARTICLE'}}},
                                            {'term': {'metadata.genre': {'value': 'MONOGRAPH'}}},
                                            {
                                                'bool': {
                                                    'must': [
                                                        {'term': {'metadata.genre': {'value': 'THESIS'}}},
                                                        {
                                                            'bool': {
                                                                'should': [
                                                                    {
                                                                        'term': {
                                                                            'metadata.degree': {'value': 'HABILITATION'}
                                                                        }
                                                                    },
                                                                    {'term': {'metadata.degree': {'value': 'PHD'}}},
                                                                ]
                                                            }
                                                        },
                                                    ]
                                                }
                                            },
                                        ]
                                    }
                                },
                            ]
                        }
                    },
                ]
            }
        },
        'sort': [{'metadata.title.keyword': {'order': 'asc'}}],
        'size': f'{per_page}',
        'from': f'{index}',
    }

    return query


def request_publications(query, headers, url):
    response = requests.post(url, headers=headers, data=json.dumps(query))
    return response


def get_publications(start_date, end_date, headers, url):
    """Query the PuRe API for publications published between start_date and end_date."""

    per_page = 2000
    index = 0
    finished = False
    retry = 3
    publications = []
    while not finished:
        # print('entered loop')
        # print(f'    index: {index}, per_page: {per_page}, length(publications): {len(publications)}')
        query = create_query_string(start_date, end_date, per_page, index)
        # print(json.dumps(query, indent=2))

        response = request_publications(query, headers, url)

        try:
            response.raise_for_status()
            total_records = response.json().get('numberOfRecords')
            publications.extend(response.json().get('records', []))

            if total_records > per_page + index:
                finished = False
            else:
                finished = True

            index += per_page
            retry = 3

            # if index == 20 or index == 24:
            #     print('index == 20 or index == 24')
            #     raise requests.HTTPError('Made up exception')

        except requests.HTTPError:
            retry -= 1
            # print('')
            # print('')
            # print('')
            # print('')
            if retry == 0:
                finished = True
                logger.error('Failed to retrieve publications 3 times.')

    print(f'Total publications retrieved: {len(publications)}')
    return publications


def get_doi_from_publication(publication):
    doi = None
    for identifier in publication.get('data', {}).get('metadata', {}).get('identifiers', []):
        if identifier.get('type') == 'DOI' and identifier.get('id') is not None:
            doi = f'https://doi.org/{identifier.get("id")}'
            break

    return doi


def get_title_from_publication(publication):
    title = publication.get('data', {}).get('metadata', {}).get('title')
    return title if title != '' else None


def get_pure_id_from_publication(publication):
    pure_id = publication.get('data', {}).get('objectId')
    return pure_id if pure_id != '' else None


def get_genre_from_publication(publication):
    genre = publication.get('data', {}).get('metadata', {}).get('genre')
    return genre if genre != '' else None


def get_publisher_from_publication(publication):
    publishers = []
    for source in publication.get('data', {}).get('metadata', {}).get('sources', []):
        source_publisher = source.get('publishingInfo', {}).get('publisher')
        if source_publisher is not None and source_publisher not in publishers:
            publishers.append(source_publisher)

    publisher = ', '.join(publishers) if len(publishers) > 0 else None
    return publisher


def get_publication_date_from_publication(publication):
    published_year = None
    published_date = publication.get('data', {}).get('metadata', {}).get('datePublishedOnline')
    if published_date is not None:
        published_year = published_date[:4]
    return published_date, published_year


def get_file_urls_from_publication(publication):
    """Get file links from publication.
    PuRe publications have two types of files: `INTERNAL_MANAGED` and `EXTERNAL_URL`.
    `INTERNAL_MANAGED` files have a `mimeType` attribute, if it equals 'application/pdf', they are links to a pdf.
    `EXTERNAL_URL` files can be pdf links or locators, i.e. links to landing pages.

    """

    pdf_urls, locator_urls = [], []

    if publication.get('data', {}).get('files') is None:  # publication without files
        return pdf_urls, locator_urls

    df = pd.json_normalize(publication, ['data', 'files'])
    df.insert(0, 'url_source', ['PuRe'] * df.shape[0])
    df.insert(0, 'openalex_oa', [None] * df.shape[0])
    df.insert(0, 'openalex_version', [None] * df.shape[0])

    # Ensure all publication_pdf_url's columns exist, if not postgres add throws an error
    pure_optional_columns = ['content', 'metadata.contentCategory', 'metadata.oaStatus']
    for col in pure_optional_columns:
        if col not in df.columns:
            df[col] = None

    internal_filter = df['storage'] == 'INTERNAL_MANAGED'
    df.loc[internal_filter, 'content'] = 'https://pure.mpg.de' + df.loc[internal_filter, 'content'].astype(str)
    url_columns = [
        'content',
        'metadata.contentCategory',
        'openalex_version',
        'metadata.oaStatus',
        'openalex_oa',
        'url_source',
    ]

    # locator urls
    locator_df_column_names = {
        'content': 'locator_url',
        'metadata.contentCategory': 'pure_content_category',
        'metadata.oaStatus': 'pure_oa_status',
    }
    locator_urls = json.loads(
        df.loc[~internal_filter][url_columns]
        .rename(columns={k: v for k, v in locator_df_column_names.items() if k in df.columns})
        .to_json(orient='records')
    )

    # pdf urls
    if 'mimeType' in df.columns:
        pdf_filter = df['mimeType'] == 'application/pdf'

        pdf_df_column_names = {
            'content': 'pdf_url',
            'metadata.contentCategory': 'pure_content_category',
            'metadata.oaStatus': 'pure_oa_status',
        }
        pdf_df = df.loc[pdf_filter][url_columns].rename(
            columns={k: v for k, v in pdf_df_column_names.items() if k in df.columns}
        )
        pdf_df.insert(0, 'locator_url', [None] * df.loc[pdf_filter].shape[0])
        pdf_urls = json.loads(pdf_df.to_json(orient='records'))

    return pdf_urls, locator_urls


def get_open_access_status_from_publication(publication):
    oa_status = None

    if publication.get('data', {}).get('files') is None:  # publication without files
        return oa_status

    df = pd.json_normalize(publication, ['data', 'files'])
    if 'metadata.oaStatus' not in df.columns:  # no OA status available in the publication's files
        return oa_status

    unique_oa_status = df['metadata.oaStatus'].unique()
    oa_status = ', '.join([status for status in unique_oa_status if pd.notna(status)])

    return oa_status


def extract_params(publication):
    """Call all functions to extract the relevant parameters from the paper and returns them."""

    doi = get_doi_from_publication(publication)
    title = get_title_from_publication(publication)
    publication_date, publication_year = get_publication_date_from_publication(publication)
    pure_id = get_pure_id_from_publication(publication)
    genre = get_genre_from_publication(publication)
    publisher = get_publisher_from_publication(publication)
    pdf_urls, locator_urls = get_file_urls_from_publication(publication)
    oa_status = get_open_access_status_from_publication(publication)

    processed_publication = {
        'title': title,
        'publication_year': publication_year,
        'doi': doi,
        'pure_id': pure_id,
        'genre': genre,
        'publisher': publisher,
        'publication_date': publication_date,
        'pdf_urls': pdf_urls,
        'locator_urls': locator_urls,
        'oa_status': oa_status,
    }

    return processed_publication


def get_publications_for_time_period(start_date, end_date):
    """Request PuRe publications for the specified time range.
    Return a processed dictionary per publication containing a subset of PuRe publication's data.

    """

    url = 'https://pure.mpg.de/rest/items/search?format=json'

    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
    }
    publications = get_publications(start_date, end_date, headers, url)
    processed_publications = [extract_params(p) for p in publications]

    return processed_publications


if __name__ == '__main__':
    url = 'https://pure.mpg.de/rest/items/search?format=json'

    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
    }

    start_date = '2025-10-01'
    end_date = '2025-10-01'

    # publications = get_publications(start_date, end_date, headers, url)

    # for publication in publications:
    #     print(json.dumps(publication, indent=2))
    #     print('')
    #     print('')
    #     print('')

    #     get_file_urls_from_publication(publication)
    #     get_open_access_status_from_publication(publication)
    #     get_doi_from_publication(publication)

    # query, _per_page = create_query_string('2026-09-01', '2026-09-01')
    # print(json.dumps(query, indent=2))

    publications = get_publications('2026-09-01', '2026-09-01', headers, url)
