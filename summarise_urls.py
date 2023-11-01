import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import argparse
from tqdm import tqdm
import os
from langchain.llms import Ollama
from langchain.document_loaders import WebBaseLoader
from langchain.chains.summarize import load_summarize_chain

def save_result_to_file(result, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(result)

def create_or_empty_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

def scrape_links_iteration(start_url, max_depth, data_folder):
    visited = set()
    to_visit = deque([(start_url, 0)])
    scraped_links = []

    while to_visit:
        current_url, depth = to_visit.popleft()

        if depth > max_depth:
            continue

        if current_url in visited:
            continue

        try:
            response = requests.get(current_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                links = soup.find_all('a')
                tqdm_links = tqdm(links, desc=f"Scraping {current_url}")
                for link in tqdm_links:
                    href = link.get('href')
                    if href:
                        absolute_url = urljoin(current_url, href)
                        
                        parsed_absolute_url = urlparse(absolute_url)
                        parsed_base_url = urlparse(base_url)
                        
                        if parsed_absolute_url.netloc == parsed_base_url.netloc:
                            scraped_links.append(absolute_url)
                            to_visit.append((absolute_url, depth + 1))
                            visited.add(absolute_url)

        except Exception as e:
            print(f"Error: {str(e)}")

    scraped_links = list(set(scraped_links))
    return scraped_links

def process_url(url, data_folder):
    try:
        print(f"Processing URL: {url}")
        loader = WebBaseLoader(url)
        docs = loader.load()
        print(f"length: {len(docs[0].page_content)} for url: {url}")
    
        llm = Ollama(model="llama2")
        chain = load_summarize_chain(llm, chain_type="stuff")
        result = chain.run(docs)
        print(f"Length of result for {url}: {len(result)}")
        result_filename = os.path.join(data_folder, f"{url.replace('/', '_')}_result.txt")
        save_result_to_file(result, result_filename)
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_url", type=str, required=True, help="Base URL to start scraping from")
    parser.add_argument("--max_depth", type=int, required=True, help="Maximum depth for recursion")
    parser.add_argument("--data_folder", type=str, required=True, help="Folder to save results")
    args = parser.parse_args()

    base_url = args.base_url
    max_depth = args.max_depth
    start_url = base_url
    data_folder = args.data_folder

    create_or_empty_folder(data_folder)  # Create or empty the data folder

    unique_scraped_links = scrape_links_iteration(start_url, max_depth, data_folder)
    print(f"Found {len(unique_scraped_links)} final links from base URL: {base_url}")

    for link in tqdm(unique_scraped_links, desc="Processing Links"):
        print('*'*100)
        process_url(link, data_folder)
