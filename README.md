# IIX Prefix Scraper (Dual-Output)
Extracts BGP prefixes from IIX Looking Glass with status-based filtering.

## 🚀 Features
* **Dynamic Discovery**: Automatically fetches the latest protocol IDs (ASNs) from the IX API summary.
* **Headless Scraping**: Uses Playwright to render dynamic JavaScript tables that standard HTTP clients can't read.
* **UV Optimized**: Leverages `uv` for lightning-fast dependency resolution and virtual environment management.
* **Smart Filtering**: Uses Regex to validate CIDR notation and ensures unique prefix output.
* **Dual Output**:
  1. `prefix.txt`: Contains only **Primary (P)** active routes.
  2. `all-prefix.txt`: Contains **all** discovered routes (Primary, Inactive, and Blocked).
* **Config-Driven**: Fully customizable target URLs and output paths via YAML.

## 📊 Workflow
1.  **Discovery**: Queries the Bird's Eye API for a JSON summary of all active BGP sessions.
2.  **Navigation**: Loops through the discovered protocols and launches a headless Chromium instance.
3.  **Extraction**: Waits for the dynamic route table to render and scrapes the prefix column.
4.  **Validation**: Filters results using IPv4 CIDR regex and removes duplicates.
5.  **Persistence**: Writes the final sorted list to `prefix.txt`.

## 🛠 Prerequisites
* [uv](https://github.com/astral-sh/uv) installed.
* Python 3.10+

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd iix-prefix-scraper
    ```

2.  **Initialize environment and install dependencies:**
    ```bash
    uv sync
    uv run playwright install chromium
    ```

## ⚙️ Configuration
Edit `config.yaml` to set your target exchange and output file:

```yaml
ix_name: "IIX-Jakarta"
api_summary_url: "[https://squad.iix.net.id/api/v4/lg/rs1-ipv4/bgp-summary](https://squad.iix.net.id/api/v4/lg/rs1-ipv4/bgp-summary)"
route_base_url: "[https://squad.iix.net.id/lg/rs1-ipv4/routes/protocol/](https://squad.iix.net.id/lg/rs1-ipv4/routes/protocol/)"
primary_output: "prefix.txt"
all_output: "all-prefix.txt"
concurrency: 10
```

## 🏃 Usage
Run the scraper using the uv wrapper:
    ```bash
    uv run main.py


## 📄 Output Example
The resulting prefix.txt will look like this:

    ```plaintext
    103.10.10.0/24
    103.11.12.0/23
    202.158.0.0/19

Disclaimer: Please ensure you comply with the IIX Terms of Service regarding automated access to their Looking Glass infrastructure.