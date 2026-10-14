"""Bouwt channable-image-swap-en.csv voor het Channable DK-project.

Combineert:
- image-map-en.csv   : vaste beeldkoppelingen (schone dealbeelden), handmatig beheerd
- dk.boxrstore.com   : actuele Deense marktprijzen in DKK (wat de klant ziet)

Kolommen: id, nieuwe_image_link, productnaam, old_image_link, price_dkk, sale_price_dkk
price_dkk = normale prijs (compare_at als die hoger is), sale_price_dkk = verkoopprijs bij korting.
"""
import csv, json, sys, time, urllib.request

URL = "https://dk.boxrstore.com/products.json?limit=250&page={}"
HEADERS = {
    "Cookie": "localization=DK; cart_currency=DKK",
    "Accept-Language": "da-DK",
    "User-Agent": "Mozilla/5.0 (feed-price-sync)",
}


def fetch(page):
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL.format(page), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["products"]
        except Exception as e:
            print(f"pagina {page} poging {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise SystemExit(f"pagina {page} niet op te halen")


prices, page, probe = {}, 1, []
while True:
    products = fetch(page)
    if not products:
        break
    for p in products:
        for v in p["variants"]:
            price, compare = float(v["price"]), float(v["compare_at_price"] or 0)
            if compare > price:
                prices[str(v["id"])] = (f"{compare:.2f}", f"{price:.2f}")
            else:
                prices[str(v["id"])] = (f"{price:.2f}", "")
            if "kob-2-fa-3" in p["handle"]:
                probe.append(price)
    page += 1
    time.sleep(1)

# zonder DK-markt geeft de shop EUR (< 150); dan niets overschrijven
if not probe or max(probe) < 150:
    raise SystemExit(f"geen DKK-prijzen ontvangen (2+3 = {probe[:1]}), bestand niet overschreven")

images = {}
with open("image-map-en.csv", newline="") as f:
    for r in csv.DictReader(f):
        images[r["id"]] = (r["nieuwe_image_link"], r["productnaam"], r["old_image_link"])

with open("channable-image-swap-en.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["id", "nieuwe_image_link", "productnaam", "old_image_link", "price_dkk", "sale_price_dkk"])
    for vid in sorted(set(prices) | set(images)):
        img = images.get(vid, ("", "", ""))
        pr = prices.get(vid, ("", ""))
        w.writerow([vid, *img, *pr])
print(f"{len(prices)} prijzen, {len(images)} beeldkoppelingen")
