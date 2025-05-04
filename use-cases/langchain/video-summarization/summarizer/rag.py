import argparse
import ast
import requests
from concurrent.futures import ThreadPoolExecutor

MILVUS_SIM_SEARCH_ENDPOINT="http://127.0.0.1:8000/search"

def search_in_milvus(query_txt):
    try:
        response = requests.get(url=MILVUS_SIM_SEARCH_ENDPOINT, params={"query": query_txt})
        # print(response.content)
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.content}")
            return None

        return response.content

    except requests.exceptions.RequestException as e:
        print(f"Search in Milvus: Request failed: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()    
    parser.add_argument("--query_text", type=str)
    args = parser.parse_args()
    
    with ThreadPoolExecutor() as pool:
        if args.query_text:
            print(f"Search Query: {args.query_text}")
            query_text = args.query_text
            query_future = pool.submit(search_in_milvus, query_text)
    
            if query_future and query_future.result():
                print(f"Search Results: {ast.literal_eval(query_future.result().decode('utf-8'))}")
        
        else:
            print("No query text provided. Please provide a query text to search.")