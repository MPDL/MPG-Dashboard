import json
from pathlib import Path

from data_extraction import openalex

TEST_DATA = Path(__file__).parent / 'test_data' / 'openalex'


def load_fixture(name):
    with (TEST_DATA / name).open(encoding='utf-8') as file:
        return json.load(file)


def test_filter_results_by_article_name_and_year():
    """Tests OpenAlex matches have:
    - a perfect match* or similar enough** title compared to PuRe title
    - a publication year within a 3-year window of the PuRe publication year

    *lev distance of 0
    **weighted lev distance of max 2

    """

    # COMPLETE MISMATCH
    article_name = (
        'Understanding spin relaxation and magnetization transfer in ex vivo '
        'white matter using an unconstrained four-pool model analysis',
    )
    publication_year = 2021
    results = load_fixture('openalex_title_mismatches.json').get('results')

    assert openalex.filter_results_by_article_name_and_year(article_name, publication_year, results) == []

    # VERY SIMILAR TITLES - ALMOST PERFECT MATCHES AFTER STRING TRANSFORMATION
    article_name = 'A Datalog Hammer for Supervisor Verification Conditions Modulo Simple Linear Arithmetic'
    publication_year = 2021
    results = load_fixture('openalex_title_and_year_matches_different_type.json').get('results')

    assert len(openalex.filter_results_by_article_name_and_year(article_name, publication_year, results)) == 1

    # VERY SIMILAR TITLES - LONGER OPENALEX TITLE, DIFFERENT YEAR
    article_name = 'Altneuland: A German colonial journal?'
    publication_year = 2023
    results = load_fixture('openalex_title_match_different_year.json').get('results')

    assert len(openalex.filter_results_by_article_name_and_year(article_name, publication_year, results)) == 1


def test_string_transformation_unescapes_and_normalizes_text():
    """Tests title normalization because fuzzy matching must ignore HTML entities, case, and punctuation."""
    assert openalex.string_transformation('A&amp; B <sub>2</sub>!') == 'absub2sub'
    assert openalex.string_transformation(None) == ''

    # item_3366511
    openalex_title = '(A&lt;sub&gt;&amp;infin;&lt;/sub&gt;,2)-categories and relative 2-operads'
    pure_title = '(A<sub>∞</sub>,2)-categories and relative 2-operads'

    assert openalex.string_transformation(openalex_title) == openalex.string_transformation(pure_title)
