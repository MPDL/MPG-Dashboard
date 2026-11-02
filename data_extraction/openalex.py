import html
import json
import os
import re

import dotenv
import pandas as pd
import requests
from Levenshtein import distance as lev

dotenv.load_dotenv()


def get_openalex_entry_based_on_doi(doi):
    """Get OpenAlex work entry by doi."""
    response = requests.get(
        f'https://api.openalex.org/works/{doi}?mailto={os.getenv("REQUEST_MAIL")}&'
        'select=id,title,type,type_crossref,publication_year,open_access,locations'
    )

    try:
        response.raise_for_status()
        return response.json()
    except requests.HTTPError:
        # print(f'    Error fetching openalex article data by doi, error: {e}')
        return


def get_openalex_entry_based_on_title(title, publication_year):
    """Get OpenAlex work entry by title and publishing year."""
    # print('get_openalex_entry_based_on_title(title, publication_year)')

    results = fetch_openalex_entry_based_on_title(title, publication_year)
    # print('    length openalex response: {len( results)}')

    openalex_entry = find_correct_entry(title, publication_year, results)
    return openalex_entry


def fetch_openalex_entry_based_on_title(title, publication_year):
    """Get OpenAlex work entry/entries by article name and publication year.

    First filter by article name and publication year.
    If there are no results, filter only by article name.

    """

    clean_title = title.replace(' ', '+').replace('?', '').replace(',', '').replace('*', '').replace('++', '+')

    response = requests.get(
        f'https://api.openalex.org/works?sort=relevance_score:desc&per_page=10&mailto={os.getenv("REQUEST_MAIL")}&'
        'select=id,title,type,type_crossref,publication_year,open_access,locations&'
        f'filter=title.search:{clean_title},publication_year:{publication_year}'
    )

    try:
        response.raise_for_status()
        results = response.json().get('results', [])

        if len(results) == 0:
            response_without_year = requests.get(
                f'https://api.openalex.org/works?sort=relevance_score:desc&per_page=10&mailto={os.getenv("REQUEST_MAIL")}&'
                f'select=id,title,type,type_crossref,publication_year,open_access,locations&filter=title.search:{clean_title}'
            )

            try:
                response_without_year.raise_for_status()
                results.extend(response_without_year.json().get('results', []))
            except requests.HTTPError:
                return results

        return results

    except requests.HTTPError:
        # print(f'    Error fetching openalex article data by title and year, error: {e}')
        return


def find_correct_entry(article_name, publication_year, results):
    """Given a PuRe publication's name and publication year, find the matching entry from a list of OpenAlex entries.
    In the case of multiple matching entries, filter by type and open-access status.

    """
    # # print('find_article_entry()')
    # # print(f'    original length: {len(results)}')

    if results is None or len(results) == 0:
        return

    filtered_results = filter_results_by_article_name_and_year(article_name, publication_year, results)
    # print(f'    length after name filter: {len(filtered_results)}')
    filtered_results = filter_results_by_type(filtered_results)
    # print(f'    length after type filter: {len(filtered_results)}')
    filtered_results = filter_results_by_oa_status(filtered_results)
    # print(f'    length after oa status filter: {len(filtered_results)}')

    if len(filtered_results) == 0:
        return

    return filtered_results[0]


def filter_results_by_oa_status(results):
    """Filter OpenAlex's response based on open-access status."""

    matches = [entry for entry in results if entry.get('open_access', {}).get('is_oa')]

    if len(matches) > 0:
        return matches

    return results


def filter_results_by_type(results):
    """Filter OpenAlex's response based on article type.
    See https://docs.openalex.org/api-entities/works/work-object#type

    """

    relevant_types = ['article', 'book-chapter', 'dissertation', 'book']
    matches = [entry for entry in results if entry.get('type') in relevant_types]

    if len(matches) > 0:
        return matches

    return results


def filter_results_by_article_name_and_year(article_name, publication_year, results):
    """Search for correct article in OpenAlex's response based on the article name and the publishing year."""

    word_count_article_name = len(article_name.split()) if isinstance(article_name, str) else 0
    article_name = string_transformation(article_name)
    print(f'    article name: {article_name}')
    publication_year = int(publication_year)

    perfect_matches = []
    matches = []
    for entry in results:
        if entry['title'] is not None:
            # print(f'entry title: {entry['title']}')
            word_count_entry_title = len(entry.get('title', '').split())
            entry_title = string_transformation(entry.get('title', ''))
            print(f'    entry title: {entry_title}')

            # If weighted levenshtein distance is small enough (i.e. titles are similar enough) and
            # publication year is in acceptable range, then return entry
            # weighted by word count for flexibility in larger strings
            # BUT using min instead of max word count to lower diminishing factor
            min_word_count = min(word_count_article_name, word_count_entry_title)
            if (
                min_word_count > 0
                and (lev(entry_title, article_name) / min_word_count) <= 2
                and entry.get('publication_year') >= publication_year - 3
                and entry.get('publication_year') <= publication_year + 3
            ):
                # print(f'weighted levenshtein distance: {lev(entry_title, article_name)/min_word_count}')
                matches.append(entry)

                if lev(entry_title, article_name) == 0:
                    perfect_matches.append(entry)

    if len(perfect_matches) > 0:
        print(f'Perfect matches found: {len(perfect_matches)}')
        return perfect_matches

    return matches


def process_openalex_entry(openalex_entry, pure_pdf_urls, pure_locator_urls):
    """Extract pdf and location links, oA status and article name from OpenAlex's response."""

    # if no OpenAlex entry was found, return None
    if openalex_entry is None:
        return

    # locations
    df = pd.json_normalize(openalex_entry, 'locations')
    # filter out MPG locations, directly requested at PuRe api
    df = df.loc[df['source.id'] != 'https://openalex.org/S4306400654'] if 'source.id' in df.columns else df
    df.insert(0, 'url_source', ['OpenAlex'] * df.shape[0])
    df.insert(0, 'pure_oa_status', [None] * df.shape[0])
    df.insert(0, 'pure_content_category', [None] * df.shape[0])
    df.rename(columns={'version': 'openalex_version', 'is_oa': 'openalex_oa'}, inplace=True)

    pdf_df = df.loc[df['pdf_url'].notna()][
        ['pdf_url', 'pure_content_category', 'openalex_version', 'pure_oa_status', 'openalex_oa', 'url_source']
    ]
    pdf_df.insert(0, 'locator_url', [None] * df.loc[df['pdf_url'].notna()].shape[0])

    openalex_pdf_urls = [
        url_dict
        for url_dict in json.loads(pdf_df.to_json(orient='records'))
        if url_dict['pdf_url'] not in [pure_url_dict['pdf_url'] for pure_url_dict in pure_pdf_urls]
    ]
    # print(f'PDF URLs extracted from OpenAlex: {json.dumps(openalex_pdf_urls)}')

    openalex_locator_urls = json.loads(
        df.loc[df['landing_page_url'].notna()][
            [
                'landing_page_url',
                'pure_content_category',
                'openalex_version',
                'pure_oa_status',
                'openalex_oa',
                'url_source',
            ]
        ]
        .rename(columns={'landing_page_url': 'locator_url'})
        .to_json(orient='records')
    )
    openalex_locator_urls = [
        url_dict
        for url_dict in openalex_locator_urls
        if url_dict['locator_url'] not in [pure_url_dict['locator_url'] for pure_url_dict in pure_locator_urls]
    ]
    # print(f'Locator URLs extracted from OpenAlex: {json.dumps(openalex_locator_urls)}')

    processed_openalex_entry = {
        'id': openalex_entry.get('id'),
        'title': openalex_entry.get('title'),
        'oa': openalex_entry.get('open_access', {}).get('is_oa'),
        'oa_status': openalex_entry.get('open_access', {}).get('oa_status'),
        'type': openalex_entry.get('type'),
        'type_crossref': openalex_entry.get('type_crossref'),
        'pdf_urls': openalex_pdf_urls,
        'locator_urls': openalex_locator_urls,
    }

    return processed_openalex_entry


def string_transformation(string: str):
    """Unescape string input and afterward keep only lowercased alphanumeric characters.

    Motivation: html strings can contain escaped values that contain alphanumeric characters.
    (A&lt;sub&gt;&amp;infin;&lt;/sub&gt;,2) is the escaped version of: (A<sub>∞</sub>,2).
    Skipping unescaping means transforming (A&lt;sub&gt;&amp;infin;&lt;/sub&gt;,2)
    to altsubgtampinfinltsubgt2
    instead of asubsub2
    """

    if not isinstance(string, str):
        return ''

    print(f'        original string        : {string}')
    html_unescaped_str = html.unescape(string)
    print(f'        first unescaped string : {html_unescaped_str}')
    html_unescaped_str = html.unescape(html_unescaped_str)
    print(f'        second unescaped string: {html_unescaped_str}')

    transformed_string = re.sub('[^A-Za-z0-9]+', '', html_unescaped_str)
    lower_case_transformed_string = transformed_string.lower()
    print(f'        transformed string    : {lower_case_transformed_string}')
    return lower_case_transformed_string


if __name__ == '__main__':
    # DOI SEARCH
    # openalex_entry = get_openalex_entry_based_on_doi('https://doi.org/10.1007/s00209-021-02784-w')

    # https://openalex.org/W3205380891
    # openalex_entry = get_openalex_entry_based_on_title(
    #   'A reduction principle for Fourier coefficients of automorphic forms',
    #   2021
    # )
    # # print(f'openalex_entry: {json.dumps(openalex_entry, indent=2)}')

    # FIND ARTICLE
    # title = 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic'
    # publication_year = 2021
    # json_result = fetch_openalex_entry_based_on_title(title, publication_year)
    # article_entry = find_correct_entry(title, publication_year, json_result)

    # # print(f'article_entry: {json.dumps(article_entry, indent=2)}')

    # LEVENSHTEIN DISTANCE
    # pure_title = 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic'
    # openalex_title = 'A Sorted Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic'

    # transformed_pure = string_transformation(pure_title)
    # transformed_openalex = string_transformation(openalex_title)

    # word_count_pure = len(pure_title.split())
    # word_count_openalex = len(openalex_title.split())
    # min_word_count = min(word_count_pure, word_count_openalex)

    # similarity = lev(transformed_pure, transformed_openalex)/min_word_count

    # # print(f'similarity: {similarity}')

    # openalex_entry = {
    #     'id':'https://openalex.org/W4414705619',
    #     'title':'HippoMaps: multiscale cartography of human hippocampal organization',
    #     'type':'article',
    #     'type_crossref':'journal-article',
    #     'publication_year':2025,
    #     'open_access':{'is_oa':True,'oa_status':'hybrid','oa_url':'https://doi.org/10.1038/s41592-025-02783-3','any_repository_has_fulltext':True},
    #     'locations':[
    #         {
    #             'is_oa': True,
    #             'landing_page_url': 'https://doi.org/10.1038/s41592-025-02783-3',
    #             'pdf_url': None,
    #             'source': {
    #                 'id': 'https://openalex.org/S127827428',
    #                 'display_name': 'Nature Methods',
    #                 'issn_l': '1548-7091',
    #                 'issn': ['1548-7091','1548-7105'],
    #                 'is_oa': False,
    #                 'is_in_doaj': False,
    #                 'is_indexed_in_scopus': True,
    #                 'is_core': True,
    #                 'host_organization': 'https://openalex.org/P4310319908',
    #                 'host_organization_name': 'Nature Portfolio',
    #                 'host_organization_lineage': ['https://openalex.org/P4310319908','https://openalex.org/P4310319965'],
    #                 'host_organization_lineage_names': ['Nature Portfolio','Springer Nature'],
    #                 'type': 'journal'
    #             },
    #             'license': 'cc-by-nc-and',
    #             'license_id': 'https://openalex.org/licenses/cc-by-nc-nd',
    #             'version': 'publishedVersion',
    #             'is_accepted': True,
    #             'is_published': True
    #         },
    #         {
    #             'is_oa': True,
    #             'landing_page_url': 'https://doi.org/10.21203/rs.3.rs-4045651/v1',
    #             'pdf_url': 'https://www.researchsquare.com/article/rs-4045651/latest.pdf',
    #             'source': {
    #                 'id': 'https://openalex.org/S4306402450',
    #                 'display_name': 'Research Square (Research Square)',
    #                 'issn_l': None,
    #                 'issn': None,
    #                 'is_oa': True,
    #                 'is_in_doaj': False,
    #                 'is_indexed_in_scopus': False,
    #                 'is_core': False,
    #                 'host_organization': 'https://openalex.org/I4210096694',
    #                 'host_organization_name': 'Research Square (United States)',
    #                 'host_organization_lineage': ['https://openalex.org/I4210096694'],
    #                 'host_organization_lineage_names': ['Research Square (United States)'],
    #                 'type': 'repository'
    #             },
    #             'license': 'cc-by',
    #             'license_id': 'https://openalex.org/licenses/cc-by',
    #             'version': 'submittedVersion',
    #             'is_accepted': False,
    #             'is_published': False
    #         },
    #         {
    #             'is_oa': False,
    #             'landing_page_url': 'https://pubmed.ncbi.nlm.nih.gov/41034610',
    #             'pdf_url': None,
    #             'source': {
    #                 'id': 'https://openalex.org/S4306525036',
    #                 'display_name': 'PubMed',
    #                 'issn_l': None,
    #                 'issn': None,
    #                 'is_oa': False,
    #                 'is_in_doaj': False,
    #                 'is_indexed_in_scopus': False,
    #                 'is_core': False,
    #                 'host_organization': 'https://openalex.org/I1299303238',
    #                 'host_organization_name': 'National Institutes of Health',
    #                 'host_organization_lineage': ['https://openalex.org/I1299303238'],
    #                 'host_organization_lineage_names': ['National Institutes of Health'],
    #                 'type': 'repository'
    #             },
    #             'license': None,
    #             'license_id': None,
    #             'version': None,
    #             'is_accepted': False,
    #             'is_published': False
    #         }
    #     ]
    # }

    # _, __, ___, ____ = process_openalex_entry(openalex_entry)

    #####

    article_name = 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic'
    publication_year = 2021
    results = [
        {
            'id': 'https://openalex.org/W3181626888',
            'title': 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic',
            'type': 'conference-paper',
            'publication_year': 2021,
            'open_access': {
                'is_oa': True,
                'oa_status': 'green',
                'oa_url': 'https://arxiv.org/pdf/2107.03189',
                'any_repository_has_fulltext': True,
            },
            'locations': [
                {
                    'id': 'doi:10.1007/978-3-030-86205-3_1',
                    'is_oa': False,
                    'landing_page_url': 'https://doi.org/10.1007/978-3-030-86205-3_1',
                    'pdf_url': None,
                    'source': {
                        'id': 'https://openalex.org/S106296714',
                        'display_name': 'Lecture notes in computer science',
                        'issn_l': '0302-9743',
                        'issn': ['0302-9743', '1611-3349'],
                        'is_oa': False,
                        'is_in_doaj': False,
                        'is_core': True,
                        'listed_in': ['cwts-core', 'jufo-1', 'norway-1'],
                        'host_organization': 'https://openalex.org/P4310319900',
                        'host_organization_name': 'Springer Science+Business Media',
                        'host_organization_lineage': [
                            'https://openalex.org/P4310319900',
                            'https://openalex.org/P4310319965',
                        ],
                        'host_organization_lineage_names': ['Springer Science+Business Media', 'Springer Nature'],
                        'type': 'book series',
                    },
                    'license': None,
                    'license_id': None,
                    'version': 'publishedVersion',
                    'is_accepted': True,
                    'is_published': True,
                    'raw_source_name': 'Lecture Notes in Computer Science',
                    'raw_type': 'book-chapter',
                },
                {
                    'id': 'pmh:oai:arXiv.org:2107.03189',
                    'is_oa': True,
                    'landing_page_url': 'http://arxiv.org/abs/2107.03189',
                    'pdf_url': 'https://arxiv.org/pdf/2107.03189',
                    'source': {
                        'id': 'https://openalex.org/S4306400194',
                        'display_name': 'arXiv (Cornell University)',
                        'issn_l': '2331-8422',
                        'issn': ['2331-8422'],
                        'is_oa': True,
                        'is_in_doaj': False,
                        'is_core': False,
                        'listed_in': [],
                        'host_organization': 'https://openalex.org/I205783295',
                        'host_organization_name': 'Cornell University',
                        'host_organization_lineage': ['https://openalex.org/I205783295'],
                        'host_organization_lineage_names': ['Cornell University'],
                        'type': 'repository',
                    },
                    'license': None,
                    'license_id': None,
                    'version': 'submittedVersion',
                    'is_accepted': False,
                    'is_published': False,
                    'raw_source_name': None,
                    'raw_type': 'text',
                },
                {
                    'id': 'mag:3181626888',
                    'is_oa': True,
                    'landing_page_url': 'http://arxiv.org/pdf/2107.03189.pdf',
                    'pdf_url': None,
                    'source': {
                        'id': 'https://openalex.org/S4306400194',
                        'display_name': 'arXiv (Cornell University)',
                        'issn_l': '2331-8422',
                        'issn': ['2331-8422'],
                        'is_oa': True,
                        'is_in_doaj': False,
                        'is_core': False,
                        'listed_in': [],
                        'host_organization': 'https://openalex.org/I205783295',
                        'host_organization_name': 'Cornell University',
                        'host_organization_lineage': ['https://openalex.org/I205783295'],
                        'host_organization_lineage_names': ['Cornell University'],
                        'type': 'repository',
                    },
                    'license': None,
                    'license_id': None,
                    'version': 'submittedVersion',
                    'is_accepted': False,
                    'is_published': False,
                    'raw_source_name': 'arXiv (Cornell University)',
                    'raw_type': None,
                },
                {
                    'id': 'pmh:oai:HAL:hal-03531889v1',
                    'is_oa': False,
                    'landing_page_url': 'https://inria.hal.science/hal-03531889',
                    'pdf_url': None,
                    'source': {
                        'id': 'https://openalex.org/S4306402512',
                        'display_name': 'HAL (Le Centre pour la Communication Scientifique Directe)',
                        'issn_l': None,
                        'issn': None,
                        'is_oa': False,
                        'is_in_doaj': False,
                        'is_core': False,
                        'listed_in': [],
                        'host_organization': 'https://openalex.org/I1294671590',
                        'host_organization_name': 'Centre National de la Recherche Scientifique',
                        'host_organization_lineage': ['https://openalex.org/I1294671590'],
                        'host_organization_lineage_names': ['Centre National de la Recherche Scientifique'],
                        'type': 'repository',
                    },
                    'license': None,
                    'license_id': None,
                    'version': 'submittedVersion',
                    'is_accepted': False,
                    'is_published': False,
                    'raw_source_name': 'FroCos 2021 - 13th International Symposium on Frontiers of Combining Systems, \
                        Sep 2021, Birmingham, United Kingdom. pp.3-24, &#x27E8;10.1007/978-3-030-86205-3_1&#x27E9;',
                    'raw_type': 'info:eu-repo/semantics/conferenceObject',
                },
                {
                    'id': 'doi:10.48550/arxiv.2107.03189',
                    'is_oa': True,
                    'landing_page_url': 'https://doi.org/10.48550/arxiv.2107.03189',
                    'pdf_url': None,
                    'source': {
                        'id': 'https://openalex.org/S4306400194',
                        'display_name': 'arXiv (Cornell University)',
                        'issn_l': '2331-8422',
                        'issn': ['2331-8422'],
                        'is_oa': True,
                        'is_in_doaj': False,
                        'is_core': False,
                        'listed_in': [],
                        'host_organization': 'https://openalex.org/I205783295',
                        'host_organization_name': 'Cornell University',
                        'host_organization_lineage': ['https://openalex.org/I205783295'],
                        'host_organization_lineage_names': ['Cornell University'],
                        'type': 'repository',
                    },
                    'license': None,
                    'license_id': None,
                    'version': None,
                    'is_accepted': False,
                    'is_published': None,
                    'raw_source_name': None,
                    'raw_type': 'Preprint',
                },
            ],
        },
        {
            'id': 'https://openalex.org/W4287083637',
            'title': 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple\\n Linear Arithmetic',
            'type': 'preprint',
            'publication_year': 2021,
            'open_access': {
                'is_oa': True,
                'oa_status': 'green',
                'oa_url': 'https://arxiv.org/pdf/2107.03189',
                'any_repository_has_fulltext': True,
            },
            'locations': [
                {
                    'id': 'pmh:oai:arXiv.org:2107.03189',
                    'is_oa': True,
                    'landing_page_url': 'http://arxiv.org/abs/2107.03189',
                    'pdf_url': 'https://arxiv.org/pdf/2107.03189',
                    'source': {
                        'id': 'https://openalex.org/S4306400194',
                        'display_name': 'arXiv (Cornell University)',
                        'issn_l': '2331-8422',
                        'issn': ['2331-8422'],
                        'is_oa': True,
                        'is_in_doaj': False,
                        'is_core': False,
                        'host_organization': 'https://openalex.org/I205783295',
                        'host_organization_name': 'Cornell University',
                        'host_organization_lineage': ['https://openalex.org/I205783295'],
                        'host_organization_lineage_names': ['Cornell University'],
                        'type': 'repository',
                    },
                    'license': None,
                    'license_id': None,
                    'version': 'submittedVersion',
                    'is_accepted': False,
                    'is_published': False,
                    'raw_source_name': '',
                    'raw_type': 'text',
                }
            ],
        },
    ]

    # filter_results_by_article_name_and_year(article_name, publication_year, results)

    string_transformation('A&amp; B <sub>2</sub>!')
