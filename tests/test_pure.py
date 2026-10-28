import json
from pathlib import Path

from data_extraction import PuRe  # ..data_extraction import PuRe

TEST_DATA = Path(__file__).parent / 'test_data' / 'pure'


def load_publication(filename, index=0):
    '''Load a single publication record from a PuRe API response fixture.'''
    with (TEST_DATA / filename).open(encoding='utf-8') as file:
        data = json.load(file)
    return data['records'][index]


# --- get_doi_from_publication ---------------------------------------------


def test_get_doi_from_publication_returns_doi_url():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_doi_from_publication(publication) == 'https://doi.org/10.3390/ani13172751'


def test_get_doi_from_publication_returns_none_without_top_level_doi():
    '''DOI exists nested under a source, but not under metadata.identifiers.'''
    publication = load_publication('pure_publication_without_doi.json')
    assert PuRe.get_doi_from_publication(publication) is None


# --- get_title_from_publication ---------------------------------------------


def test_get_title_from_publication():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_title_from_publication(publication) == (
        '"An Aid with Soul": understanding the determinants of guide '
        'dog-owner compatibility from qualitative interviews'
    )


# --- get_pure_id_from_publication ---------------------------------------------


def test_get_pure_id_from_publication():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_pure_id_from_publication(publication) == 'item_3536683'


# --- get_genre_from_publication ---------------------------------------------


def test_get_genre_from_publication_returns_genre():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_genre_from_publication(publication) == 'ARTICLE'


def test_get_genre_from_publication_returns_none_when_missing():
    publication = load_publication('pure_publication_without_genre.json')
    assert PuRe.get_genre_from_publication(publication) is None


def test_get_genre_from_publication_with_empty_genre_fixture():
    publication = load_publication('pure_publication_with_empty_genre.json')
    assert PuRe.get_genre_from_publication(publication) is None


# --- get_publisher_from_publication ---------------------------------------------


def test_get_publisher_from_publication_single_source():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_publisher_from_publication(publication) == 'MDPI'


def test_get_publisher_from_publication_joins_multiple_sources():
    publication = load_publication('pure_publication_without_files.json')
    assert PuRe.get_publisher_from_publication(publication) == 'CT : Peeters'


def test_get_publisher_from_publication_returns_none_when_missing():
    publication = load_publication('pure_publication_without_publisher.json')
    assert PuRe.get_publisher_from_publication(publication) is None


# --- get_publication_date_from_publication ---------------------------------------------


def test_get_publication_date_from_publication():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_publication_date_from_publication(publication) == ('2023-08-29', '2023')


def test_get_publication_date_from_publication_missing_date():
    publication = load_publication('pure_publication_without_date.json')
    assert PuRe.get_publication_date_from_publication(publication) == (None, None)


def test_get_publication_date_from_publication_empty_date():
    publication = load_publication('pure_publication_with_empty_date.json')
    assert PuRe.get_publication_date_from_publication(publication) == ('', '')


# --- get_file_urls_from_publication ---------------------------------------------


def test_get_file_urls_from_publication_internal_pdf():
    publication = load_publication('pure_complete_publications.json', 0)
    pdf_urls, locator_urls = PuRe.get_file_urls_from_publication(publication)

    assert locator_urls == []
    assert len(pdf_urls) == 1
    assert pdf_urls[0]['pdf_url'] == ('https://pure.mpg.de/rest/items/item_3536683_2/component/file_3536685/content')
    assert pdf_urls[0]['pure_content_category'] == 'publisher-version'
    assert pdf_urls[0]['pure_oa_status'] == 'GOLD'
    assert pdf_urls[0]['locator_url'] is None


def test_get_file_urls_from_publication_external_locator():
    publication = load_publication('pure_complete_publications.json', 1)
    pdf_urls, locator_urls = PuRe.get_file_urls_from_publication(publication)

    assert pdf_urls == []
    assert len(locator_urls) == 1
    assert locator_urls[0]['locator_url'] == ('https://www.tandfonline.com/doi/abs/10.1080/15548627.2023.2214031')
    assert locator_urls[0]['pure_content_category'] == 'any-fulltext'
    assert locator_urls[0]['pure_oa_status'] == 'NOT_SPECIFIED'


def test_get_file_urls_from_publication_multiple_pdfs():
    publication = load_publication('pure_complete_publications.json', 2)
    pdf_urls, locator_urls = PuRe.get_file_urls_from_publication(publication)

    assert locator_urls == []
    assert len(pdf_urls) == 2
    assert {pdf['pure_oa_status'] for pdf in pdf_urls} == {'GOLD'}


def test_get_file_urls_from_publication_returns_empty_lists_without_files():
    publication = load_publication('pure_publication_without_files.json')
    assert PuRe.get_file_urls_from_publication(publication) == ([], [])


# --- get_open_access_status_from_publication ---------------------------------------------


def test_get_open_access_status_from_publication_single_file():
    publication = load_publication('pure_complete_publications.json', 0)
    assert PuRe.get_open_access_status_from_publication(publication) == 'GOLD'


def test_get_open_access_status_from_publication_deduplicates_statuses():
    publication = load_publication('pure_complete_publications.json', 2)
    assert PuRe.get_open_access_status_from_publication(publication) == 'GOLD'


def test_get_open_access_status_from_publication_returns_none_without_files():
    publication = load_publication('pure_publication_without_files.json')
    assert PuRe.get_open_access_status_from_publication(publication) is None


def test_get_open_access_status_from_publication_raises_when_oastatus_missing_from_all_files():
    publication = load_publication('pure_publication_without_oastatus.json')
    assert PuRe.get_open_access_status_from_publication(publication) is None


# --- extract_params ---------------------------------------------


def test_extract_params_combines_all_fields():
    publication = load_publication('pure_complete_publications.json', 0)
    result = PuRe.extract_params(publication)

    assert result == {
        'title': (
            '"An Aid with Soul": understanding the determinants of guide '
            'dog-owner compatibility from qualitative interviews'
        ),
        'publication_year': '2023',
        'doi': 'https://doi.org/10.3390/ani13172751',
        'pure_id': 'item_3536683',
        'genre': 'ARTICLE',
        'publisher': 'MDPI',
        'publication_date': '2023-08-29',
        'pdf_urls': [
            {
                'locator_url': None,
                'pdf_url': 'https://pure.mpg.de/rest/items/item_3536683_2/component/file_3536685/content',
                'pure_content_category': 'publisher-version',
                'openalex_version': None,
                'pure_oa_status': 'GOLD',
                'openalex_oa': None,
                'url_source': 'PuRe',
            }
        ],
        'locator_urls': [],
        'oa_status': 'GOLD',
    }
    assert len(result['locator_urls']) == 0
