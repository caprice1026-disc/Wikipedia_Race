import logging
import random
import time
import requests

WIKI_API = "https://ja.wikipedia.org/w/api.php"
USER_AGENT = "WikiRaceApp/1.0 (+https://example.com)"
logger = logging.getLogger(__name__)


def check_link_exists(source_title: str, target_title: str, retries: int = 3) -> bool:
    """`source_title`から`target_title`へのリンク有無を確認"""
    base_params = {
        "action": "query",
        "prop": "links",
        "titles": source_title,
        "pllimit": "max",
        "format": "json",
        "redirects": 1,
    }
    attempt = 0
    while attempt < retries:
        try:
            next_cursor = None
            while True:
                params = dict(base_params)
                if next_cursor:
                    params["plcontinue"] = next_cursor
                resp = requests.get(
                    WIKI_API,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page in pages.values():
                    for link in page.get("links", []):
                        if link.get("title") == target_title:
                            logger.debug("FOUND link %s → %s", source_title, target_title)
                            return True
                next_cursor = data.get("continue", {}).get("plcontinue")
                if not next_cursor:
                    break
            logger.debug("NOT FOUND link %s → %s", source_title, target_title)
            return False
        except Exception as e:  # noqa: BLE001
            logger.warning("Link check error (%s → %s) %s", source_title, target_title, e)
            time.sleep((2 ** attempt) + random.random())
            attempt += 1
    raise RuntimeError("Wikipedia API unreachable")
