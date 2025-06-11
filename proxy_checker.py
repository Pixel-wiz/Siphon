#!/usr/bin/env python3
import requests
import concurrent.futures
import time
import re

PROXY_URLS = [ 
    'https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt',
    'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/proxylist.txt',
    'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/http_checked.txt'
]

def download_proxy_list(url):
    try:
        response = requests.get(url, timeout=10)
        lines = response.text.strip().split('\n')
        proxies = [line.strip() for line in lines if line.strip() and ':' in line]
        print(f"Downloaded {len(proxies)} proxies from {url}")
        return proxies
    except Exception as e:
        print(f"Failed to download from {url}: {e}")
        return []

def clean_proxy(proxy):
    proxy = proxy.strip()
    proxy = re.sub(r'^https?://', '', proxy)
    proxy = re.sub(r'^socks[45]?://', '', proxy)
    proxy = re.sub(r'/.*$', '', proxy)
    if ':' not in proxy:
        return None
    return proxy

def test_proxy(proxy):
    clean = clean_proxy(proxy)
    if not clean:
        return None
    
    try:
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', 
                              proxies={'http': f'http://{clean}', 'https': f'http://{clean}'}, 
                              timeout=3)
        response_time = time.time() - start_time
        if response.status_code == 200:
            print(f"{clean} - Success {response_time:.3f}s")
            return (clean, response_time)
    except:
        pass
    return None

def main():
    all_proxies = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        download_futures = [executor.submit(download_proxy_list, url) for url in PROXY_URLS]
        for future in concurrent.futures.as_completed(download_futures):
            proxies = future.result()
            all_proxies.extend(proxies)
    
    unique_proxies = list(set(all_proxies))
    print(f"Total unique proxies to test: {len(unique_proxies)}")
    
    working_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(test_proxy, proxy) for proxy in unique_proxies]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                working_proxies.append(result)
    
    working_proxies.sort(key=lambda x: x[1])
    top_50 = working_proxies[:50]
    
    with open('proxies.txt', 'w') as f:
        for proxy, _ in top_50:
            f.write(f"{proxy}\n")
    
    print(f"Found {len(working_proxies)} working proxies, saved top {len(top_50)} to proxies.txt")

if __name__ == "__main__":
    main()
