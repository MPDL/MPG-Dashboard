from db import DatabaseManager
from pdf_downlaoder import save_url_to_file
import os, shutil
from eval import eval_file_software_mentions, eval_data_mentions

def eval_paper(publication, urls, db_manager):
    if publication["open_access"] == True:
        open_access_workflow(publication, urls, db_manager)
    else:
        closed_access_workflow(publication, urls)

def open_access_workflow(publication, urls, db_manager):
    '''For open access publications, get the pdf and evaluate software and data use, creation and sharing'''
    
    destination = "./pdf/"
    successful_download = save_url_to_file(urls, destination, publication["title"])
    if successful_download is not None:
        software_evaluation = eval_file_software_mentions(successful_download)
        data_evaluation = eval_data_mentions(successful_download)
        
        db_manager.put_software_sharing_status(
            publication["object_id"],
            software_evaluation["software_used"],
            software_evaluation["software_shared"],
            software_evaluation["software_created"]
        )
        db_manager.put_data_sharing_status(
            publication["object_id"],
            data_evaluation["data_mentions"],
            data_evaluation["data_shared"]
        )
        delete_pdf()
        
def closed_access_workflow(publication, urls):
    # TODO: Implement closed access workflow
    pass

def delete_pdf():
    '''Delete downloaded publication pdf after evaluation'''
    folder = './pdf/'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
        


def full_workflow_time_period(publication_year):
    '''Request publications by year and evaluate data and software use, creation and sharing'''
    
    db_manager = DatabaseManager()
    db_manager.connect()
    publications= db_manager.get_unevaluated_papers_publication_year(publication_year)
    for publication in publications:
        urls = db_manager.get_urls_by_publication_id(publication["object_id"])
        print(f"URLs: {urls}, Type of URLs: {type(urls)}")
        
        if urls:
            eval_paper(publication, urls, db_manager)
            break
    db_manager.close()



if __name__ == "__main__":
    full_workflow_time_period("2021")