import uuid

import requests

def save_url_to_file(urls, destination, filename):
    print("URL: ", urls," Filename: ", filename)
    #print(urls)
    #print(filename)
    for url_dict in urls:
        try:
            url = url_dict["pdf_link"] 
            response = requests.get(url)
            print(response.status_code)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
            
            if 'application/pdf' in response.headers.get('Content-Type', ''):
                try:
                    #print("Saving PDF: ", filename, " from URL: ", url, " with content length of: ", len(response.content))
                    with open(destination + filename, 'wb') as f:
                        f.write(response.content)
                        return filename
                except:
                    random_filename = str(uuid.uuid4()) + ".pdf"
                    with open(destination + random_filename, 'wb') as f:
                        f.write(response.content)
                        return random_filename
            else:
                print("The response does not contain a PDF.", url)
                # You might want to handle this case differently based on your requirement
        except requests.exceptions.RequestException as e:
            print("Error occurred while fetching the URL:", e)
            # You might want to handle this error more specifically
    return None


def save_all_urls_to_files(dict_of_urls, destination):
    for title in dict_of_urls:
        #print("Title: ", title, " Title_check: ", title is not None)
        if title is not None:
            save_url_to_file(dict_of_urls[title], destination, title+".pdf")
        else:
            save_url_to_file(dict_of_urls[title], destination, str(uuid.uuid4())+".pdf")