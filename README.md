# MPG-Dashboard

This project aims at giving an overview of software and data use, creation and sharing in the Max Planck Society (MPG) in the context of Open Science. 

Publication information comes from [PuRe](https://pure.mpg.de/), the publication repository of the MPG. [OpenAlex](https://openalex.org/about), a catalog of the world's scholarly research system, is used to enrich publication information, and Open Science evaluation is made with [Softcite](https://github.com/softcite), a model that extracts software and data mentions from publications' text.

## 1. WORKFLOWS

### 1.1 DATA EXTRACTION
-> full_workflow_data_extraction.py

Request [PuRe](https://pure.mpg.de/) publications and enrich them with [OpenAlex](https://openalex.org/about)'s open access status and pdf links.

### 1.2. EVALUATION
-> full_workflow_evaluation.py

Evaluate software and data use, creation and sharing. Evaluation workflow depends on open access status. Currently, only the open access workflow exists. 

## 2. CURRENT EVALUATION MODEL
-> https://github.com/softcite


