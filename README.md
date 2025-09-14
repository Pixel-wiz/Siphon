# Siphon Web Scraper

Siphon is a powerful and flexible web scraping tool designed for efficient data extraction from websites. It supports multi-threaded operations, proxy rotation, and advanced filtering capabilities, making it ideal for various data collection tasks while maintaining anonymity and avoiding detection.

## Features

-   **Multi-threaded web scraping**: Accelerate data collection by scraping multiple pages concurrently.
-   **Proxy support and rotation**: Maintain anonymity and bypass IP-based restrictions using a list of proxies.
-   **File type filtering**: Specify and download only desired file types (e.g., images, documents).
-   **Recursive depth control**: Limit the depth of crawling to focus on relevant content.
-   **Robust error handling**: Gracefully manage network issues and website errors during scraping.
-   **Easy command-line interface**: Simple and intuitive commands for quick setup and execution.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/Pixel-wiz/Siphon
    cd siphon
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the scraper:
    ```bash
    python siphon.py [URL] [options]
    ```

## Usage

Siphon can be run from the command line with various options to customize its behavior.

```bash
python siphon.py <URL> [options]
```

**Options:**
-   `--depth <N>`: Maximum recursion depth (default: 1)
-   `--threads <N>`: Number of concurrent threads (default: 1)
-   `--filetype <EXT>`: Filter files by extension (e.g., jpg, png, pdf)
-   `--proxy-file <FILE>`: Path to a file containing a list of proxies (one per line)
-   `--output <DIR>`: Output directory for downloaded files (default: current directory)

### Advanced Options (Phase 0)

-   `--events-ndjson <PATH or '-'>`: Emit structured NDJSON event stream to a file or stdout.
-   `--manifest <PATH>`: Append a per-artifact record `{url, path, sha256, bytes, content_type}`.
-   `--retries <N>`: Max retries for retryable errors like 429/503/timeouts (default: 3).
-   `--backoff-base-ms <MS>`: Base for exponential backoff with jitter (default: 250).
-   `--respect-robots`: Placeholder to enable robots.txt compliance in a later phase.

### Advanced Options (Phase 1)

-   Health-aware proxy rotation with cooldown and simple circuit breaker (auto, no new flags).
-   Emits additional NDJSON events: `proxy_select`, `proxy_ok`, `proxy_fail`, and breaker transitions.
-   Retries honor `Retry-After` on 429/503 where present; both fetch and downloads use backoff.

## Requirements

-   Python 3.x
-   `requests` library
-   `beautifulsoup4` library

These dependencies will be installed automatically when you run `pip install -r requirements.txt`.

## Utility Scripts

### `proxy_get.py`

This script is a standalone utility designed to fetch and validate a list of free proxies from various online sources. It can be used independently to generate a `proxies.txt` file, which can then be utilized by the main `siphon.py` script for proxy rotation.

To use `proxy_get.py`:

```bash
python proxy_get.py
```

This will generate a `proxies.txt` file in the current directory.

### Validation Matrix

Use the helper to validate against a small set of JS-heavy public sites. This
exercises dynamic detection (mode_switch/dynamic_ok/dynamic_fail), retries, and
proxy health events.

```bash
python scripts/validation_matrix.py --out output/validation --threads 3
```

Notes:
- Keep depth small and respect site policies; this is for light testing.
- If Playwright is installed, Siphon may switch to dynamic mode on pages that
  look client-rendered; otherwise it will remain static.

## Examples

-   **Basic scraping**: Scrape a website with default settings.
    ```bash
    python siphon.py https://example.com
    ```

-   **With file filtering**: Download only JPG images from a website.
    ```bash
    python siphon.py https://example.com --filetype jpg
    ```

-   **With proxies**: Use a list of proxies from `proxies.txt` for scraping.
    ```bash
    python siphon.py https://example.com --proxy-file proxies.txt
    ```

-   **Multi-threaded scraping**: Scrape a website using 5 concurrent threads.
    ```bash
    python siphon.py https://example.com --threads 5
    ```

-   **Recursive scraping**: Scrape a website up to a depth of 2.
    ```bash
    python siphon.py https://example.com --depth 2
    ```

-   **Stream events to stdout and inspect with jq**:
    ```bash
    python siphon.py https://example.com --events-ndjson - | jq -r '.event+"\t"+(.status//"" )+"\t"+(.url//"")'
    ```

-   **Write a manifest with hashes**:
    ```bash
    python siphon.py https://example.com --manifest output/manifest.ndjson
    ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
