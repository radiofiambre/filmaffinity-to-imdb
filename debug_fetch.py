import cloudscraper

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)
resp = scraper.get("https://www.filmaffinity.com/es/userlist.php?user_id=3859150&list_id=1002")

print("Status code:", resp.status_code)
print("Longitud del HTML:", len(resp.text))
print("¿Contiene 'list-row'?:", "list-row" in resp.text)
print("¿Contiene 'data-movie-id'?:", "data-movie-id" in resp.text)
print("¿Contiene 'Cloudflare' o 'challenge'?:", "cloudflare" in resp.text.lower() or "challenge" in resp.text.lower())

with open("debug.html", "w", encoding="utf-8") as f:
    f.write(resp.text)