import asyncio
import httpx
import yaml
import re
from playwright.async_api import async_playwright

# Load Configuration
def load_config():
    try:
        with open("configx.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "api_summary_url": "https://squad.iix.net.id/api/v4/lg/rs1-ipv4/bgp-summary",
            "route_base_url": "https://squad.iix.net.id/lg/rs1-ipv4/routes/protocol/",
            "primary_output": "prefixs.txt",
            "all_output": "all-prefixs.txt"
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

    page = await browser.new_page()

    print(f"[*] Scraping {protocol}...")
    try:
        # Networkidle is important here because the table is rendered via JS
        await page.goto(target_url, wait_until="networkidle", timeout=70000)
        
        # Wait for the table rows to actually exist
        await page.wait_for_selector("table#routes tbody tr", timeout=50000)
        
        # --- TURBO SECTION: Extract all rows at once inside the browser ---
        data = await page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('table#routes tbody tr'));
            return rows.map(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 3) return null;
                const prefixLink = cells[0].querySelector('a');
                const statusSpan = cells[2].querySelector('span');
                return {
                    prefix: prefixLink ? prefixLink.innerText.trim() : '',
                    status: statusSpan ? statusSpan.innerText.trim().toUpperCase() : ''
                };
            }).filter(item => item !== null);
        }""")
        # -----------------------------------------------------------------

        local_primary = set()
        local_all = set()
        cidr_regex = re.compile(r'^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$')

        for item in data:
            if cidr_regex.match(item['prefix']):
                local_all.add(item['prefix'])
                if item['status'] == "P":
                    local_primary.add(item['prefix'])
        
        return local_primary, local_all
                    
    except Exception as e:
        print(f"[!] Error on {protocol}: {str(e)[:50]}...")
        return set(), set()
    finally:
        await page.close()

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