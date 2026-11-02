#!/usr/bin/env python3
"""Open the collector's private browser profile for human sign-in/renewal."""
import argparse
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sync_playwright() as p:
        # Use Chrome's normal macOS Keychain integration, not Playwright's
        # default mock keychain/basic password store. Never export storageState.
        context = p.chromium.launch_persistent_context(str(args.profile), channel='chrome', headless=False,
            ignore_default_args=['--use-mock-keychain', '--password-store=basic'])
        for url in ['https://www.instagram.com/', 'https://yaaytravel.com/login']:
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
        print('Sign in to Instagram and Yaay in the collector browser; close that browser when finished.', flush=True)
        try:
            while context.pages:
                context.pages[0].wait_for_timeout(1000)
        except Exception:
            pass  # Closing the browser is the successful human handoff.
        finally:
            context.close()


if __name__ == '__main__':
    main()
