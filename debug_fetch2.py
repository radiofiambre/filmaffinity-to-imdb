import cloudscraper

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

base_url = "https://www.filmaffinity.com/es/userlist.php?user_id=3859150&list_id=1002"

resp1 = scraper.get(base_url)
resp2 = scraper.get(f"{base_url}&page=2")

import re
ids_page1 = set(re.findall(r'data-movie-id="(\d+)"', resp1.text))
ids_page2 = set(re.findall(r'data-movie-id="(\d+)"', resp2.text))

print("IDs únicos en página 1:", len(ids_page1))
print("IDs únicos en página 2:", len(ids_page2))
print("¿Son exactamente los mismos IDs?:", ids_page1 == ids_page2)
print("IDs en página 2 pero no en página 1:", list(ids_page2 - ids_page1)[:5])