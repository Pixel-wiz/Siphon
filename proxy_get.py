#!/usr/bin/env python3
# Part of the Siphon - Web Data Extraction Tool
import requests
import concurrent.futures
import time
import re
import signal
import threading
import argparse

PROXY_URLS = [ 
    'https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt',
    'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/refs/heads/master/proxylist.txt',
    'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/refs/heads/main/http_checked.txt'
]

MAX_WORKING_PROXIES = 50
shutdown_flag = threading.Event()

def handle_sigint(signum, frame):
    print("\n[!] Ctrl+C detected. Stopping proxy check and saving results...")
    shutdown_flag.set()

signal.signal(signal.SIGINT, handle_sigint)

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

def test_proxy(proxy, timeout=2):
    clean = clean_proxy(proxy)
    if not clean:
        return None
    try:
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', 
                              proxies={'http': f'http://{clean}', 'https': f'http://{clean}'}, 
                              timeout=timeout)
        response_time = time.time() - start_time
        if response.status_code == 200:
            print(f"{clean} - Success {response_time:.3f}s")
            return (clean, response_time)
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Proxy checker with threading and timeout options.")
    parser.add_argument('--threads', type=int, default=5, help='Number of threads for proxy testing (default: 5)')
    args = parser.parse_args()
    all_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        download_futures = [executor.submit(download_proxy_list, url) for url in PROXY_URLS]
        for future in concurrent.futures.as_completed(download_futures):
            proxies = future.result()
            all_proxies.extend(proxies)
    unique_proxies = list(set(all_proxies))
    print(f"Total unique proxies to test: {len(unique_proxies)}")
    working_proxies = []
    working_lock = threading.Lock()
    def test_and_collect(proxy):
        if shutdown_flag.is_set():
            return None
        result = test_proxy(proxy, timeout=2)
        if result:
            with working_lock:
                if len(working_proxies) < MAX_WORKING_PROXIES:
                    working_proxies.append(result)
        return result
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = [executor.submit(test_and_collect, proxy) for proxy in unique_proxies]
            for future in concurrent.futures.as_completed(futures):
                if shutdown_flag.is_set():
                    break
                with working_lock:
                    if len(working_proxies) >= MAX_WORKING_PROXIES:
                        print(f"[+] Reached {MAX_WORKING_PROXIES} working proxies. Stopping early.")
                        shutdown_flag.set()
                        break
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user. Saving found proxies...")
        shutdown_flag.set()
    working_proxies.sort(key=lambda x: x[1])
    top_n = working_proxies[:MAX_WORKING_PROXIES]
    with open('proxies.txt', 'w') as f:
        for proxy, _ in top_n:
            f.write(f"{proxy}\n")
    print(f"Found {len(working_proxies)} working proxies, saved top {len(top_n)} to proxies.txt")

if __name__ == "__main__":
    main()
