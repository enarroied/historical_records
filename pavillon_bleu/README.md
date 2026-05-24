# Pavillon Bleu / Blue Flags — data Reconsrtruction from several sources (PDF, web parsing)

The blue Flag program was launched in 1985 in france. It later became European, and after that, it became a world wide label.

I am collecting the data for the [French towns data lakehouse project](https://github.com/enarroied/french_towns_lakehouse). For this reason, i will only collect information about French beaches and ports that were awarded the blue Flag.

The data is very hard to obtain, and it is near-impossible to obtain the first years of the labl. The initial scope of the Data Lakehouse project is to collect data for years starting in 2000, so I will try that. There is some information available thanks to the wayback machine. Data prior to 2002 is very difficult to obtain.

## Data Format

The data format we extract needs to have one line per town for each year-nbsed file, since that is the granularity of our core project. For this reason, we add columns to indicate if the town has the flag for the beach or for the port (can be both). The `places` lists all the beaches and ports for that place.

Here is an example of the columns we extract:

| year | commune | department_name | department_number | region | beach_flag | port_flag | places |
| ---- | ------- | --------------- | ----------------- | ------ | ---------- | --------- | ------ |
|      |         |                 |                   |        |            |           |        |

The end file will group all the years together. One town may have several lines, one per year. This will end up being the source data for a fact table.


## Notebooks

Since we have different data sources, se split different data collection mechanisms.

The process used a mix of manual coding and agentic coding, I used openCode with Pickle. Pure agentic coding is difficult here because the PDFs are quite messy and some guidance is required, also the domain knowledge is important to parse the documents.

This is a project where I did not mind about aode quality. I wanted to have code because it is reproducible and informative, that is about it.

The reasons why code quality doesn't matter here is that the variability in the documents is too huge, each year has a different layout, and we cannot expect future years to have a similar format. None of these scripts will scae or be used for anything else.



## Manual curation

Some data sources, particularly the PDF files, are not accessible at all, and it is difficult to cover all the edge cases. Here are some manual-based work we needed to do after running the scripts:

- Ports: the PDF files list the port names, but don't add the commune/town name. Sometime (often) the port name mentions the town, but not always. The scripts *guess* the town name from the port name, but we need to manually verify them and look for the right names.
