import requests
import json 
import validators
import os
import uuid 

#x = requests.get('https://api.unpaywall.org/v2/search?query="Das Event Horizon Telescope"&email=matthiesen@mpdl.mpg.de')
#data = x.json()
#print(data)
#print(data["results"][0]["response"]["best_oa_location"]["url_for_pdf"])
#url_for_pdf


def get_pdf_url(unpaywall_json):
    try:
        return unpaywall_json["best_oa_location"]["url_for_pdf"]
    except:
        return unpaywall_json["doi"]

def get_pdf_urls(unpaywall_json):
    pdf_urls = []
    for entry in unpaywall_json["oa_locations"]:
        try:
            if entry["url_for_pdf"] is not None:
                pdf_urls.append(entry["url_for_pdf"])
        except:
            pass
    #print(pdf_urls)
    return pdf_urls

def get_paper_title(unpaywall_json):
    try:
        return unpaywall_json["title"]
    except:
        return "No title found"

def iterate_over_unpaywall_jsons(unpaywall_jsons):
    pdf_urls = []
    pdf_dict_name_urls = {}  #dict with title as key and url as value
    for json in unpaywall_jsons:
        pdf_title = get_paper_title(json)
        pdf_urls = get_pdf_urls(json)
        pdf_dict_name_urls[pdf_title] = pdf_urls
    return pdf_dict_name_urls

def read_jsonl_to_list_of_dicts(filename):
    data = []
    with open(filename, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def filter_dict_for_pdf_urls(dict_of_unfiltered_entries):
    pdf_dict = {}
    for key in dict_of_unfiltered_entries:
        if validators.url(dict_of_unfiltered_entries[key]):
            pdf_dict[key] = dict_of_unfiltered_entries[key]
    return pdf_dict

def save_url_to_file(urls, destination, filename):
    #print("URL: ", url," Filename: ", filename)
    print(urls)
    for url in urls:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
            
            if 'application/pdf' in response.headers.get('Content-Type', ''):
                
                try:
                    print("Saving PDF: ", filename, " from URL: ", url, " with content length of: ", len(response.content))
                    with open(destination + filename, 'wb') as f:
                        f.write(response.content)
                        return True
                except:
                    with open(destination + str(uuid.uuid4()) + ".pdf", 'wb') as f:
                        f.write(response.content)
                        return True
            else:
                print("The response does not contain a PDF.", url)
                # You might want to handle this case differently based on your requirement
        except requests.exceptions.RequestException as e:
            print("Error occurred while fetching the URL:", e)
            # You might want to handle this error more specifically


def save_all_urls_to_files(dict_of_urls, destination):
    for title in dict_of_urls:
        #print("Title: ", title, " Title_check: ", title is not None)
        if title is not None:
            save_url_to_file(dict_of_urls[title], destination, title+".pdf")
        else:
            save_url_to_file(dict_of_urls[title], destination, str(uuid.uuid4())+".pdf")

def check_valid_pdf(directory, pdf):
    file_stats = os.stat(directory + pdf)
    #print("PDF name: ", pdf, " File size: ", file_stats.st_size)
    if file_stats.st_size < 1*1500 or 15*1000 < file_stats.st_size < 17*1000:
        return False
    return True

def remove_invalid_pdfs(directory):
    for pdf in os.listdir(directory):
        if not check_valid_pdf(directory, pdf):
            os.remove(directory + pdf)


data_in_json = read_jsonl_to_list_of_dicts("./unpaywall/all_results_publication_with_doi.jsonl")
iterated_data = iterate_over_unpaywall_jsons(data_in_json)
print("Anzahl der Einträge: ", len(iterated_data))
#pdf_urls = filter_dict_for_pdf_urls(iterated_data)
#print("Anzahl der PDFs: ",len(pdf_urls))
save_all_urls_to_files(iterated_data, "./unpaywall/pdf/")

#remove_invalid_pdfs("./unpaywall/pdf/") #269 currently -> 176
