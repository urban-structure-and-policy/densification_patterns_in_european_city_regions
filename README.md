# Densification patterns in European City-regions
In this repository we provide a geospatial approach to measure and compare densification processes in city-regions in France, Germany and UK. 

## Workflow
The process includes five main steps: 
1. Pre-processing
2. Measure building change
3. Classification of building types and use
4. Delineation of densification projects
5. Contextual information

<img src="https://github.com/user-attachments/assets/a9cf2d0a-ca61-49ce-a0c8-602e8f692d93" width="600">

## Output
The output of the process is a dataset of building footprints with a) newly emerged residential buildings between t0 and t1, b) which are located within the built-up urban area of t0 and c) can be assigned to one of six densification types ranging from Large densification with multi-family housing (MFH) to Small densification with single-family housing (SFH). This allows for comparison between the city-regions in the three countries regarding occurence, spatial distribution and importance of specific densification processes. 

<img src="https://github.com/user-attachments/assets/94d1bc3b-72d4-4d7a-ad16-ee9282956f36" width="600">

## Getting started
The purpose of this repository is to provide the code for review and documentation. As some of the data for reproducing the whole process is not open accessible, possibilites for actually running the workflow are limited. 

### Input data
The process uses several datasources of which not all are openly available. More information on input data is provided in [data_input.md](https://github.com/anonymauthorgit/compare_densification_review/blob/main/data_input.md).

### Prerequisites
The main parts of the workflow runs in [R](https://www.r-project.org/). For some processing steps [Python](https://www.python.org/), [QGIS](https://qgis.org/), and [ArcGIS](https://www.arcgis.com/index.html) are required. Further, an API and a local instance of [openrouteservice](https://openrouteservice.org/) is needed. Further details on the software used can be found [here](https://github.com/anonymauthorgit/compare_densification_review/blob/main/software_used.md).

### Description of the code
The file [00_run_all.Rmd](https://github.com/anonymauthorgit/compare_densification_review/blob/main/code/00_run_all.Rmd) gives and overview on all processing steps and describes them in more detail. The processing steps which are implemented in R can be run directly form the run_all script. All other steps have to be executed separatly, as explained in run_all at the respective location.

