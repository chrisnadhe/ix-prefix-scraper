# Coding Agent Instructions: IX Scraper Implementation

## Project Goal
Extract BGP prefixes from `ixp manager` by cross-referencing the API summary with the front-end route pages.

## Technical Specifications
1.  **Environment**: Python 3.10+, managed by `uv`.
2.  **Dependencies**: `playwright`, `httpx`, `pyyaml`.
3.  **Data Source A (Discovery)**: `api_summary_ur`
    * Extract `protocol` string from the JSON response.
4.  **Data Source B (Scraping)**: `route_base_url<protocol>`
    * Target the table rows.
    * The prefix is typically located in the first or second `<td>` of each row within the `<tbody>`.
    * Use a Regex pattern to validate CIDR notation: `^([0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$`.

## Extraction Logic
1.  **Wait**: Ensure the `tbody tr` is visible (JavaScript rendering required).
2.  **Prefix (CIDR)**: Found in the **first `<td>`** (index 0) inside an `<a>` tag.
3.  **Status**: Found in the **third `<td>`** (index 2). 
    - Check the text inside the `<span>` badge.
    - **"P"** = Primary/Active.
    - **"N"** = Inactive.
    - Presence of an `<i>` tag with class `fa-exclamation-triangle` = Blocked/Filtered.

## Output Requirements
- Maintain two sets: `primary_prefixes` and `all_prefixes`.
- Write `primary_prefixes` to `prefix.txt`.
- Write everything (union of sets) to `all-prefix.txt`.

## Concurrency Strategy
- **Library**: `asyncio` + `Playwright` (Async API).
- **Mechanism**: `asyncio.Semaphore(n)` where `n` is the max concurrent browser tabs.
- **Execution**: `asyncio.gather(*tasks)` to trigger all requests simultaneously while respecting the semaphore limit.

## Resource Management
1. **Browser Context**: Create a `new_context()` for each task to prevent cookie/session bleeding and improve memory cleanup.
2. **Timeouts**: Set a strict navigation timeout (30s) and selector timeout (10s) to prevent a single slow member from hanging the entire script.

## Data Integration
- Use `set.update()` to merge results from concurrent workers into the master `final_primary` and `final_all` sets.

## Performance Optimization
- **Do not loop through rows in Python**: This causes high latency due to Playwright's IPC (Inter-Process Communication).
- **Use `page.evaluate()`**: Inject a JavaScript function to parse the `#routes` table entirely on the browser side.
- **Return Type**: The JS function should return a list of dictionaries `[{prefix: str, status: str}]`.
- **Validation**: Perform Regex validation on the Python side after the JS returns the data to ensure clean results.

## Large Table Handling
- For tables exceeding 500 rows, ensure the Playwright `timeout` is increased to 60s if the IXP server is slow to respond, though `evaluate` will process the DOM in milliseconds once loaded.