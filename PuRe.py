import requests
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
import json

# --- Depcrated ---
def get_date_x_days_ago(days):
    date_x_days_ago = datetime.today()-timedelta(days=days)
    return date_x_days_ago.strftime('%Y-%m-%d')

# creates the query string for the PuRe API
def create_query_string(start_date, end_date):
    query = {
  "query" : {
    "bool" : {
      "must" : [ {
        "term" : {
          "publicState" : {
            "value" : "RELEASED"
          }
        }
      }, {
        "term" : {
          "versionState" : {
            "value" : "RELEASED"
          }
        }
      }, {
        "range" : {
          "metadata.datePublishedOnline" : {
            "gte" : start_date+"||/d",
            "lte": end_date+"||/d"
          }
        }
      } ]
    }
  },
  "sort" : [{"metadata.title.keyword":{"order":"asc"}}],
  "size" : "1000000",
  "from" : "0"
}
    return query

# --- Depcrated ---
def get_recent_papers(days, headers, url):
    date1 = get_date_x_days_ago(days)
    date2 = get_date_x_days_ago(days-5)
    query = create_query_string(date1, date2)
    #print(query)
    recent_papers = requests.post(url, headers=headers, data=json.dumps(query),)
    #print(recent_papers.json())
    return recent_papers

# queries the PuRe API for papers published between start_date and end_date
def get_papers(start_date, end_date, headers, url):
    query = create_query_string(start_date, end_date)
    recent_papers = requests.post(url, headers=headers, data=json.dumps(query),)
    return recent_papers

def iterate_recent_papers(recent_papers):
    for paper in recent_papers:
        extract_params(paper)

# returns the doi of the paper
def get_doi_from_paper(paper):
    doi = None
    # print(paper["data"]["metadata"])
    try:
        for identifier in paper["data"]["metadata"]["identifiers"]:
            if identifier["type"] == "DOI":
                doi = identifier["id"]
        return "https://doi.org/"+doi
    except:
        return doi

# returns the title of the paper
def get_title_from_paper(paper):
    title = paper["data"]["metadata"]["title"]
    return title

# returns the institution of the paper
def get_institution_from_paper(paper):
    institution = paper["data"]["metadata"]["creators"]
    print(institution)
    return institution

# returns the publishing year of the paper
def get_publishing_year_from_paper(paper):
    publishing_year = paper["data"]["metadata"]["datePublishedOnline"]
    publishing_year = publishing_year[:4]
    return publishing_year

# returns the PuRe object id of the paper
def get_object_id_from_paper(paper):
    object_id = paper["data"]["objectId"]
    return object_id

def get_genre_from_paper(paper):
  genre = paper["data"]["metadata"]["genre"]
  return genre

def get_publisher_from_paper(paper):
  publisher = None
  if "sources" in paper["data"]["metadata"]:
    published_source = paper["data"]["metadata"]["sources"][0]
    if "publishingInfo" in published_source:
      if "publisher" in published_source["publishingInfo"]:
        publisher = published_source["publishingInfo"]["publisher"]
  return publisher

def get_publication_date_from_paper(paper):
  published_date = None
  if "datePublishedOnline" in paper["data"]["metadata"]:
    published_date = paper["data"]["metadata"]["datePublishedOnline"]
  return published_date

# returns a list of dicts with the following keys: title, publishing_year, doi, object_id for each paper
def iterate_over_papers(papers):
    publication_dict = [{}]
    for paper in papers:
        doi, title, publishing_year, object_id, genre, publisher, publication_date = extract_params(paper)
        publication_dict.append({"title": title, "publishing_year": publishing_year, "doi": doi, "object_id": object_id, "genre": genre, "publisher": publisher, "publication_date": publication_date})
    return publication_dict

# calls all functions to extract the relevant parameters from the paper and returns them
def extract_params(paper):
    doi = get_doi_from_paper(paper)
    title = get_title_from_paper(paper)
    publishing_year = get_publishing_year_from_paper(paper)
    object_id = get_object_id_from_paper(paper)
    #institution = get_institution_from_paper(paper)
    genre = get_genre_from_paper(paper)
    publisher = get_publisher_from_paper(paper)
    publication_date = get_publication_date_from_paper(paper)
    return doi, title, publishing_year, object_id, genre, publisher, publication_date


# returns a list of dicts with the following keys: title, publishing_year, doi, object_id for each paper
def get_paper_for_time_period(start_date, end_date):
    url = "https://pure.mpg.de/rest/items/search?format=json"

    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
    }
    recent_papers = get_papers(start_date, end_date, headers, url)
    recent_papers = recent_papers.json()
    publications = iterate_over_papers(recent_papers["records"])
    return publications



