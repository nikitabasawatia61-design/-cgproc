"""
Legacy entry point — use run_daily.py for scheduled runs instead.

This script runs the scraper with a visible browser window.
"""

from scraper.runner import run_scraper

if __name__ == "__main__":
    result = run_scraper(headless=False)
    print(f"\nDone: {result['new']} new, {result['skipped']} skipped")
    input("\nPress Enter to Exit...")