import asyncio
import httpx
import yaml
import re
from playwright.async_api import async_playwright

# Load Configuration
def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "api_summary_url": "https://squad.iix.net.id/api/v4/lg/rs1-ipv4/bgp-summary",
            "route_base_url": "https://squad.iix.net.id/lg/rs1-ipv4/routes/protocol/",
            "primary_output": "prefix.txt",
            "all_output": "all-prefix.txt"
        }


async def get_protocols(api_url):
    """Fetch the list of BGP protocols from the API summary."""
    print(f"[*] Fetching protocol summary from {api_url}...")
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()
        # Extract protocol names from the Bird's Eye JSON structure
        # Usually: data['protocols'] keys
        return list(data.get("protocols", {}).keys())


async def scrape_prefixes(browser, base_url, protocol):
    """Navigate to the protocol page and extract prefixes."""
    target_url = f"{base_url}{protocol}"
    primary_prefixes = set()
    all_prefixes = set()

    page = await browser.new_page()

    print(f"[*] Scraping {protocol}...")
    try:
        # Networkidle is important here because the table is rendered via JS
        await page.goto(target_url, wait_until="networkidle", timeout=70000)
        
        # Wait for the table rows to actually exist
        await page.wait_for_selector("table#routes tbody tr", timeout=50000)
        
        # Extract text from rows.   
        rows = await page.query_selector_all("table#routes tbody tr")
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) >= 3:
                # Based on your HTML:
                # Column 1 (index 0): The <a> tag containing the Prefix
                # Column 3 (index 2): The <span> badge containing P or N
                
                prefix_element = await cells[0].query_selector("a")
                if not prefix_element:
                    continue
                
                prefix_text = (await prefix_element.inner_text()).strip()
                
                # Identify status by looking at the span inside the 3rd column
                status_element = await cells[2].query_selector("span")
                status_text = ""
                if status_element:
                    status_text = (await status_element.inner_text()).strip().upper()
                
                # Regex to validate IPv4 CIDR
                if re.match(r'^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$', prefix_text):
                    all_prefixes.add(prefix_text)
                    
                    # 'P' = Primary / Active
                    if status_text == "P":
                        primary_prefixes.add(prefix_text)
                    
    except Exception as e:
        print(f"[!] Error on {protocol}: {e}")
    finally:
        await page.close()
    
    return primary_prefixes, all_prefixes

async def main():
    config = load_config()
    final_primary = set()
    final_all = set()
    
    # 1. Get Protocols
    protocols = await get_protocols(config["api_summary_url"])
    print(f"[*] Found {len(protocols)} members. Starting serial scrape...")
    
    # 2. Start Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Start with a small batch to verify. Change [:] to scrape everything.
        for protocol in protocols[:]: 
            p_found, a_found = await scrape_prefixes(browser, config["route_base_url"], protocol)
            final_primary.update(p_found)
            final_all.update(a_found)
            
        await browser.close()

    # Write Primary only
    with open(config["primary_output"], "w") as f:
        for p in sorted(list(final_primary)):
            f.write(f"{p}\n")

    # Write All (Primary, Inactive, Blocked)
    with open(config["all_output"], "w") as f:
        for p in sorted(list(final_all)):
            f.write(f"{p}\n")
    
    print(f"\n[+] FINISHED")
    print(f"\n[+] Saved {len(final_primary)} primary prefixes to {config['primary_output']}. Extracted {len(final_primary)} Primary prefixes.")
    print(f"[+] Saved {len(final_all)} total prefixes to {config['all_output']}. Extracted {len(final_all)} Total prefixes (Primary + Inactive/Filtered).")

if __name__ == "__main__":
    asyncio.run(main())