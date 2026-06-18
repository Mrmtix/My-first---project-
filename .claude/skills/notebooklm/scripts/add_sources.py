#!/usr/bin/env python3
"""
Add Sources to a NotebookLM Notebook
Browser automation to add one or more links (e.g. YouTube videos) as
sources to an existing NotebookLM notebook.

NOTE: The "Add source" dialog selectors in config.py are best-effort,
based on NotebookLM's known UI structure, but have not been live-tested
against notebooklm.google.com (this skill was built in a sandboxed
environment with no network access to Google services). Run once with
--show-browser to confirm the flow works, and update the selector lists
in config.py if NotebookLM's UI has changed.
"""

import argparse
import sys
import time
from pathlib import Path

from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from config import (
    ADD_SOURCE_BUTTON_SELECTORS,
    SOURCE_LINK_TAB_SELECTORS,
    SOURCE_WEBSITE_OPTION_SELECTORS,
    SOURCE_URL_INPUT_SELECTORS,
    SOURCE_INSERT_BUTTON_SELECTORS,
)
from browser_utils import BrowserFactory, StealthUtils


def _click_first_match(page, selectors, timeout=10000):
    """Try each selector in order, click the first one that appears."""
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                element.click()
                return selector
        except Exception:
            continue
    return None


def add_source(page, source_url: str) -> bool:
    """Add a single source URL to the currently open notebook."""
    print(f"  ➕ Adding source: {source_url}")

    if not _click_first_match(page, ADD_SOURCE_BUTTON_SELECTORS):
        print("  ❌ Could not find 'Add source' button")
        return False
    StealthUtils.random_delay(300, 700)

    if not _click_first_match(page, SOURCE_LINK_TAB_SELECTORS):
        print("  ❌ Could not find 'Link' tab")
        return False
    StealthUtils.random_delay(300, 700)

    # YouTube links are accepted via the generic "Website" link option
    _click_first_match(page, SOURCE_WEBSITE_OPTION_SELECTORS, timeout=3000)
    StealthUtils.random_delay(300, 700)

    url_input = None
    for selector in SOURCE_URL_INPUT_SELECTORS:
        try:
            url_input = page.wait_for_selector(selector, timeout=5000, state="visible")
            if url_input:
                StealthUtils.human_type(page, selector, source_url)
                break
        except Exception:
            continue

    if not url_input:
        print("  ❌ Could not find URL input field")
        return False

    StealthUtils.random_delay(300, 700)

    if not _click_first_match(page, SOURCE_INSERT_BUTTON_SELECTORS, timeout=5000):
        print("  ❌ Could not find 'Insert' button")
        return False

    # Give NotebookLM a moment to register and start processing the source
    # before moving on to the next one.
    StealthUtils.random_delay(2000, 4000)
    print("  ✅ Source submitted")
    return True


def add_sources_to_notebook(notebook_url: str, source_urls: list, headless: bool = True) -> dict:
    """
    Open a notebook and add a list of source URLs to it.

    Returns a dict with 'succeeded' and 'failed' lists of URLs.
    """
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️ Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return {"succeeded": [], "failed": list(source_urls)}

    print(f"📚 Notebook: {notebook_url}")
    print(f"🔗 Sources to add: {len(source_urls)}")

    playwright = None
    context = None
    succeeded, failed = [], []

    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)

        page = context.new_page()
        print("  🌐 Opening notebook...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=30000)
        StealthUtils.random_delay(1000, 2000)

        for url in source_urls:
            try:
                if add_source(page, url):
                    succeeded.append(url)
                else:
                    failed.append(url)
            except Exception as e:
                print(f"  ❌ Error adding {url}: {e}")
                failed.append(url)

            # Close any leftover dialog before moving to the next source
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            StealthUtils.random_delay(1000, 2500)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        failed.extend(u for u in source_urls if u not in succeeded and u not in failed)

    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass

    return {"succeeded": succeeded, "failed": failed}


def main():
    parser = argparse.ArgumentParser(description="Add sources (links) to a NotebookLM notebook")
    parser.add_argument("--notebook-url", help="NotebookLM notebook URL")
    parser.add_argument("--notebook-id", help="Notebook ID from library")
    parser.add_argument("--url", action="append", default=[], help="A source URL to add (repeatable)")
    parser.add_argument("--urls-file", help="Path to a text file with one source URL per line")
    parser.add_argument("--show-browser", action="store_true", help="Show browser")
    args = parser.parse_args()

    notebook_url = args.notebook_url
    if not notebook_url and args.notebook_id:
        library = NotebookLibrary()
        notebook = library.get_notebook(args.notebook_id)
        if notebook:
            notebook_url = notebook["url"]
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found")
            return 1

    if not notebook_url:
        library = NotebookLibrary()
        active = library.get_active_notebook()
        if active:
            notebook_url = active["url"]
            print(f"📚 Using active notebook: {active['name']}")
        else:
            print("❌ No notebook specified and no active notebook set.")
            print("   Use --notebook-url, --notebook-id, or set an active notebook:")
            print("   python scripts/run.py notebook_manager.py activate --id ID")
            return 1

    source_urls = list(args.url)
    if args.urls_file:
        path = Path(args.urls_file)
        if not path.exists():
            print(f"❌ URLs file not found: {path}")
            return 1
        source_urls += [
            line.strip() for line in path.read_text().splitlines() if line.strip()
        ]

    if not source_urls:
        print("❌ No source URLs given. Use --url and/or --urls-file.")
        return 1

    result = add_sources_to_notebook(
        notebook_url=notebook_url,
        source_urls=source_urls,
        headless=not args.show_browser,
    )

    print("\n" + "=" * 60)
    print(f"✅ Succeeded: {len(result['succeeded'])}")
    for url in result["succeeded"]:
        print(f"   {url}")
    print(f"❌ Failed: {len(result['failed'])}")
    for url in result["failed"]:
        print(f"   {url}")
    print("=" * 60)

    return 0 if not result["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
