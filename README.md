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

## License

This project is licensed under the MIT License - see the LICENSE file for details.
