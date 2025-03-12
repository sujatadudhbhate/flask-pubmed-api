import requests
import ssl
import certifi
import csv
import sys
from Bio import Entrez
from typing import List, Dict

# Set your email for PubMed API
Entrez.email = "your_email@example.com"

# Fix SSL Certificate Issue
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(certifi.where())

# Keywords to detect non-academic affiliations
NON_ACADEMIC_KEYWORDS = [
    "Inc.", "Ltd.", "Corporation", "Company", "Biotech", "Pharma", "Laboratories", 
    "LLC", "Technologies", "Industries", "Research Institute", "Diagnostics", 
    "Solutions", "Consulting", "Foundation", "Healthcare", "Medical Center", 
    "Hospital", "Cancer Institute", "Genomics", "Therapeutics", "Life Sciences", 
    "Biopharma", "Institute", "Private Research", "Consulting Group"
]

def fetch_pubmed_papers(query: str, max_results: int = 10, year_filter: int = None) -> List[Dict]:
    """
    Fetch research papers from PubMed based on a query.
    """
    try:
        # Apply year filter if specified
        if year_filter:
            query = f"{query} AND ({year_filter}[PDAT] : 3000[PDAT])"

        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()
        
        pubmed_ids = record["IdList"]
        if not pubmed_ids:
            print("No papers found for the given query.")
            return []
        
        handle = Entrez.efetch(db="pubmed", id=",".join(pubmed_ids), rettype="medline", retmode="text")
        papers = handle.read()
        handle.close()
        
        return parse_pubmed_results(papers)
    except Exception as e:
        print(f"Error fetching papers: {e}")
        return []

def parse_pubmed_results(raw_data: str) -> List[Dict]:
    """
    Parse the raw data retrieved from PubMed and extract required details.
    """
    papers_list = []
    papers = raw_data.strip().split("\n\n")
    
    for paper in papers:
        lines = paper.split("\n")
        paper_data = {
            "PubmedID": None,
            "Title": None,
            "Publication Date": None,
            "Authors": [],
            "Affiliations": [],
            "Company Affiliations": [],
            "Corresponding Author Email": None
        }
        
        for line in lines:
            if line.startswith("PMID-") or line.startswith("PMID -"):
                paper_data["PubmedID"] = line.split("-")[-1].strip()
                print(f"✅ Extracted PubMed ID: {paper_data['PubmedID']}")
            elif line.startswith("TI  -"):
                paper_data["Title"] = line.replace("TI  - ", "").strip()
            elif line.startswith("DP  -"):
                paper_data["Publication Date"] = line.replace("DP  - ", "").strip()
            elif line.startswith("AU  -"):
                paper_data["Authors"].append(line.replace("AU  - ", "").strip())
            elif line.startswith("AD  -"):
                affiliation = line.replace("AD  - ", "").strip()
                paper_data["Affiliations"].append(affiliation)
                print(f"Checking affiliation: {affiliation}")
                if any(keyword.lower() in affiliation.lower() for keyword in NON_ACADEMIC_KEYWORDS):
                    print(f"✅ Non-Academic Detected: {affiliation}")
                    paper_data["Company Affiliations"].append(affiliation)
                else:
                    print(f"❌ Not Non-Academic: {affiliation}")
            elif "@" in line:
                paper_data["Corresponding Author Email"] = line.strip()
        
        papers_list.append(paper_data)
    
    return papers_list

def save_to_csv(papers: List[Dict], filename: str):
    """
    Save the extracted data to a CSV file.
    """
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["PubmedID", "Title", "Publication Date", "Authors", "Company Affiliations", "Corresponding Author Email"])
        writer.writeheader()
        for paper in papers:
            writer.writerow({
                "PubmedID": paper["PubmedID"],
                "Title": paper["Title"],
                "Publication Date": paper["Publication Date"],
                "Authors": ", ".join(paper["Authors"]),
                "Company Affiliations": ", ".join(paper["Company Affiliations"]),
                "Corresponding Author Email": paper["Corresponding Author Email"]
            })

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pubmed_fetcher.py \"search term\" output.csv [--year YYYY]")
        sys.exit(1)

    query = sys.argv[1]
    output_file = sys.argv[2]
    year_filter = None

    # Check if a year argument was provided
    if len(sys.argv) == 4 and sys.argv[3].startswith("--year"):
        try:
            year_filter = int(sys.argv[3].split("--year")[-1].strip())
            print(f"📅 Filtering results from {year_filter} onwards.")
        except ValueError:
            print("❌ Invalid year format. Use: --year YYYY")
            sys.exit(1)

    results = fetch_pubmed_papers(query, max_results=5, year_filter=year_filter)
    save_to_csv(results, output_file)
    print(f"✅ Results saved to {output_file}")
