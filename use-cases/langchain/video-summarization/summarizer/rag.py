import requests
from concurrent.futures import ThreadPoolExecutor

MILVUS_SIM_SEARCH_ENDPOINT="http://127.0.0.1:8000/search"

def search_in_milvus(query_txt):
    with ThreadPoolExecutor() as pool:
        try:
            response = requests.get(url=MILVUS_SIM_SEARCH_ENDPOINT, params={"query": query_txt})
            # print(response.content)
            if response.status_code != 200:
                err_msg = {"error": f"Error in search_in_milvus function {response.status_code}: {response.content.decode('utf-8')}"}
                print("Error message inside search func:", err_msg)
                return err_msg
                #return None
            #return response.content
            return {"result": response.content.decode("utf-8")}

        except requests.exceptions.RequestException as e:
            print(f"Search in Milvus: Request failed: {e}")
            return {"error": str(e)}

#if __name__ == "__main__":
#    import argparse
#    import ast
#    from concurrent.futures import ThreadPoolExecutor

#    parser = argparse.ArgumentParser() 
#    parser.add_argument("--query_text", type=str)
#    args = parser.parse_args()
    
#    with ThreadPoolExecutor() as pool:
#        if args.query_text:
#            print(f"Search Query: {args.query_text}")
#            query_text = args.query_text
#            query_future = pool.submit(search_in_milvus, query_text)
#            result = query_future.result()
#            if result and "result" in result:
#                print(f"Search results: {ast.literal_eval(result['result'])}")

            #if query_future and query_future.result():
            #    print(f"Search Results: {ast.literal_eval(query_future.result().decode('utf-8'))}")
        
        #else:
        #    print("No query text provided. Please provide a query text to search.")
