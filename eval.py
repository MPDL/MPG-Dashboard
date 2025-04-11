import requests
import json
import os

def eval_file_software_mentions(filename):
    print("Filename: ", filename)
    try:
        if filename.endswith(".pdf"):
            files = {
            'input': open('./pdf/'+filename, 'rb'),
            'disambiguate': (None, '1'),
            }
            response = requests.post('http://localhost:8060/service/annotateSoftwarePDF', files=files)
            text = json.loads(response.text)
            if len(text["mentions"])!=0:
                infos = {"name": filename, "software_used": text["mentions"][0]["documentContextAttributes"]["used"]["value"], "software_shared": text["mentions"][0]["documentContextAttributes"]["shared"]["value"], "software_created": text["mentions"][0]["documentContextAttributes"]["created"]["value"]}
                print(type(text["mentions"][0]["documentContextAttributes"]["used"]["value"]))
                print(infos)
                return infos
            else:
                infos = {"name": filename, "software_used": False, "software_shared": False, "software_created": False}
                print(infos)
                return infos
        else:
            print("File is not a PDF")
            infos = {"name": filename, "software_used": "not_a_pdf"}
            return infos
    except Exception as e:
        print("PDF wasn´t proccessable")
        infos = {"name": filename, "software_used": "not_assessable"}
        return infos

def eval_data_mentions(filename):
    try:
        used = False
        created= False
        shared = False
        if filename.endswith(".pdf"):
            directory=directory.decode('utf-8')
            files = {
            'input': open('./pdf/'+filename, 'rb'),
            'disambiguate': (None, '1'),
            }
            print(files)
            response = requests.post('http://localhost:8060/service/annotateDatasetPDF', files=files)
            text = json.loads(response.text)
            print("Text", text)
            if len(text["mentions"])!=0:
                for mentions in text["mentions"]:
                    print(mentions["mentionContextAttributes"])
                    if mentions["mentionContextAttributes"]["used"]["value"] != False:
                        used = True
                    if mentions["mentionContextAttributes"]["created"]["value"] != False:
                        created = True
                    if mentions["mentionContextAttributes"]["shared"]["value"] != False:
                        shared = True
                data_mentions = True if used or created else False
                infos = {"name": filename, "data_mentions": data_mentions, "data_shared": shared}
                return infos
            else:
                infos = {"name": filename, "data_mentions": False, "data_shared": False}
                print(infos)
                return infos
        else:
            print("File is not a PDF")
            infos = {"name": filename, "data_mentions": "not_a_pdf", "data_shared": False}
            return infos
    except Exception as e:
        print("PDF wasn´t proccessable")
        print(e)
        infos = {"name": filename, "data_mentions": "not_assessable", "data_shared": False}
        return infos


def eval_directory_for_software_mentions(directory):
    directory = os.fsencode(directory)
    evaluations = []
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        evaluation = eval_file_software_mentions(filename)
        print("Evalution", evaluation)
        evaluations.append(evaluation)
        write_dict_list_to_json(evaluations, "evaluations.json")
        simple_total_number_analysis_of_evaluations_list(evaluations)

def eval_directory(directory, type_of_eval, eval_file):
    directory = os.fsencode(directory)
    already_evaluated_file = open("evaluations_data.json")
    already_evaluated = json.load(already_evaluated_file)
    already_evaluated_titles = [publication["name"] for publication in already_evaluated]
    evaluations = already_evaluated
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if type_of_eval == "software":
            evaluation = eval_file_software_mentions(filename)
        elif type_of_eval == "data":
            if filename in already_evaluated_titles:
                print("Already evaluated", filename)
                continue
            evaluation = eval_data_mentions(filename, directory)
        print("Evalution", evaluation)
        evaluations.append(evaluation)
        write_dict_list_to_json(evaluations, eval_file)
        simple_total_number_analysis_of_evaluations_list(evaluations, type_of_eval)




def write_dict_list_to_json(list_of_dicts, filename):
    with open(filename, 'w') as json_file:
        json.dump(list_of_dicts, json_file)

def simple_total_number_analysis_of_evaluations_list(evaluation_list, eval_type):
    used = 0
    shared = 0
    created = 0
    not_assessable = 0
    for eval in evaluation_list:    
        if eval_type == "software":
            if eval["software_used"] != False:
                used += 1
                if eval["software_shared"] != False:
                    shared += 1
                if eval["software_created"] != False:
                    created += 1
            if eval["software_used"] == "not_assessable":
                not_assessable += 1
        if eval_type == "data":
            if eval["data_mentions"] != False:
                used += 1
            if eval["data_shared"] != False:
                shared += 1
            if eval["data_mentions"] == "not_assessable":
                not_assessable += 1
    print("Used: ", used, "Shared: ", shared, "Created: ", created, "Not assessable: ", not_assessable, "out of: ", len(evaluation_list))
    print("Used: ", used/len(evaluation_list)*100, "%", "Shared: ", shared/len(evaluation_list)*100, "%", "Created: ", created/len(evaluation_list)*100, "%", "Not assessable: ", not_assessable/len(evaluation_list)*100, "%")

#eval_directory("./open_alex_pdfs", "data", "evaluations_data_closed.json")
