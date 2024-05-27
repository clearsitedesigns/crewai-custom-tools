"""
The following is designed to work with CrewAI. This leverages the https://serpapi.com/. 
You will need to create an API key to use this. This code is provided as is. 
To use this with your CrewAI, you simply need to include it as a custom_tool or in your crew.py.
you can include SerpApiMultisearchTool in your Agent tools.


This allows you to customize the number of results you want back from each search engine. 
The rate limit can be adjusted as well to help mitigate calls. Results are returned in a way that 
should be usable by additional CrewAI tools. The main difference is this will search multiple search engines 
and aggregate the results. Output is saved to a separate file for results for each run if you need to investigate 
routes further.

After saving this file, include it as an import into your CrewAI process and import `SerpApiMultisearchTool`. 
You may also need to install `loguru`. I use this because it's a superior logging approach.

Provided by Preston McCauley 2024. Check out my YouTube for more great AI tutorials:
https://www.youtube.com/channel/UCHCarGG_dLc5GuCEViwAF7g
"""

import os
from time import sleep
from typing import Dict, Any
from serpapi import GoogleSearch
from loguru import logger

# Environment variable setup
os.environ["SERPER_API_KEY"] = 'your_serper_api_key_here'

# Set up loguru for logging
logger.add("search_tool.log", rotation="1 MB")

# Configuration variables for each search engine
GOOGLE_SEARCH_ENGINE = "google"
BING_SEARCH_ENGINE = "bing"
DUCKDUCKGO_SEARCH_ENGINE = "duckduckgo"
YAHOO_SEARCH_ENGINE = "yahoo"

# Number of results to fetch from each search engine
GOOGLE_RESULTS_NUM = 10
BING_RESULTS_NUM = 10
DUCKDUCKGO_RESULTS_NUM = 10
YAHOO_RESULTS_NUM = 10

# Output directory for saving results
OUTPUT_DIR = "./output"

# Helper function to perform search using SerpAPI and get results
def serpapi_search(params: Dict[str, Any]) -> list:
    try:
        search = GoogleSearch(params)
        results = search.get_dict().get("organic_results", [])
        structured_results = [
            {
                "title": result.get("title"),
                "link": result.get("link"),
                "date": result.get("date"),
                "author": result.get("author"),
                "snippet": result.get("snippet")
            }
            for result in results
        ]
        return structured_results
    except Exception as e:
        logger.error(f"Failed to retrieve search results: {e}")
        return []

# Helper function to save results to a markdown file
def save_results_to_markdown(results: Dict[str, Any], output_dir: str) -> None:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    file_path = os.path.join(output_dir, "search_results.md")
    
    with open(file_path, "a") as file:
        for result in results["search_results"]:
            file.write(f"### {result['title']}\n")
            file.write(f"[Link]({result['link']})\n")
            file.write(f"{result['snippet']}\n")
            file.write(f"**Date:** {result.get('date', 'N/A')}\n")
            file.write(f"**Author:** {result.get('author', 'N/A')}\n\n")
        file.write("\n---\n")

# Rate limiting
RATE_LIMIT = 10  # seconds

# Function to perform the internet search
def serpapi_multisearch(query: str, output_dir: str = OUTPUT_DIR, save_to_file: bool = True) -> Dict[str, Any]:
    """Performs an internet search using multiple search engines and returns combined structured results."""
    logger.info(f"Starting search for query: {query}")

    if not query:
        return {"error": "Query parameter is required"}

    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        logger.error("API key is missing")
        return {"error": "API key is required"}

    search_engines = [
        {
            "params": {
                "engine": GOOGLE_SEARCH_ENGINE,
                "q": query,
                "api_key": api_key,
                "num": GOOGLE_RESULTS_NUM
            }
        },
        {
            "params": {
                "engine": BING_SEARCH_ENGINE,
                "q": query,
                "api_key": api_key,
                "num": BING_RESULTS_NUM
            }
        },
        {
            "params": {
                "engine": DUCKDUCKGO_SEARCH_ENGINE,
                "q": query,
                "kl": "us-en",
                "api_key": api_key,
                "num": DUCKDUCKGO_RESULTS_NUM
            }
        },
        {
            "params": {
                "engine": YAHOO_SEARCH_ENGINE,
                "p": query,
                "api_key": api_key,
                "num": YAHOO_RESULTS_NUM
            }
        }
    ]

    all_results = []
    for engine in search_engines:
        results = serpapi_search(engine["params"])
        all_results.extend(results)
        sleep(RATE_LIMIT)  # rate limiting

    if len(all_results) < GOOGLE_RESULTS_NUM + BING_RESULTS_NUM + DUCKDUCKGO_RESULTS_NUM + YAHOO_RESULTS_NUM:
        all_results += [{"title": "No additional results", "link": "", "snippet": ""}] * (
            GOOGLE_RESULTS_NUM + BING_RESULTS_NUM + DUCKDUCKGO_RESULTS_NUM + YAHOO_RESULTS_NUM - len(all_results)
        )

    combined_results = {
        "search_results": all_results[:GOOGLE_RESULTS_NUM + BING_RESULTS_NUM + DUCKDUCKGO_RESULTS_NUM + YAHOO_RESULTS_NUM],
        "cited_sources": [{"title": result["title"], "url": result["link"]} for result in all_results[:GOOGLE_RESULTS_NUM + BING_RESULTS_NUM + DUCKDUCKGO_RESULTS_NUM + YAHOO_RESULTS_NUM]]
    }

    if save_to_file:
        save_results_to_markdown(combined_results, output_dir)

    logger.info("Search completed successfully")
    return combined_results

# Custom tool class for CrewAI
class SerpApiMultisearchTool:
    name: str = "SerpApiMultisearchTool"
    description: str = "Performs an internet search using multiple search engines and returns structured results."

    def run(self, query: str, output_dir: str = OUTPUT_DIR) -> str:
        return serpapi_multisearch(query, output_dir)

# Create the custom tool
serp_api_multisearch_tool = SerpApiMultisearchTool()
