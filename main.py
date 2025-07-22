import requests
import json
import time

WEBHOOK_URL = "https://maker.ifttt.com/trigger/marktplaats_alert/json/with/key/gClaiN28VHmKjbq40-UIMGRpJnzUigSEyK9hvDUWu80"


def load_seen():
    """
    Laadt de eerder geziene advertentie-ID's uit seen.json.
    Retourneert een dictionary met zoektermen als sleutels en lijsten van ID's als waarden.
    """
    try:
        with open("seen.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_seen(seen_ads):
    """
    Slaat de geziene advertentie-ID's op in seen.json.
    """
    with open("seen.json", "w") as f:
        json.dump(seen_ads, f, indent=4)


def notify(title, link, image_url=None, raw_ad_data=None):
    """
    Verzorgt de IFTTT-notificatie met extra ruwe advertentiedata.
    """
    payload = {
        "value1": title,
        "value2": f"https://www.marktplaats.nl{link}",
        "value3": image_url or "",
        "rawData": raw_ad_data
    }
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.ok:
        print(f"✅ IFTTT-notificatie verzonden: {title}")
    else:
        print(f"❌ Fout bij verzenden notificatie: {response.text}")


def check_marktplaats(keywords, seen_ads):
    """
    Controleert Marktplaats op nieuwe advertenties voor de gegeven zoekwoorden.
    Haalt de eerste pagina op en verwerkt maximaal 50 advertenties per zoekterm
    die overeenkomen met de zoekterm in de titel of beschrijving.
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    for term in keywords:
        print(f"\n🔎 Zoeken naar: {term}")
        normalized_term = term.lower()

        if term not in seen_ads:
            seen_ads[term] = []

        url = f"https://www.marktplaats.nl/lrp/api/search?query={term.replace(' ', '%20')}&offset=0&limit=50"

        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()

            for ad in data.get("listings", []):
                title = ad.get("title", "")
                description = ad.get("description", "")

                if normalized_term not in title.lower(
                ) and normalized_term not in description.lower():
                    continue

                ad_id = ad.get("itemId")
                link = ad.get("vipUrl")
                image_url = None
                if ad.get("pictures"):
                    image_url = ad["pictures"][0].get(
                        "largeUrl") or ad["pictures"][0].get("mediumUrl")

                if ad_id not in seen_ads[term]:
                    seen_ads[term].append(ad_id)
                    print(f"✨ Nieuw gevonden: {title}")

                    # *** ENIGE WIJZIGING HIER: VOEG 'search_term' TOE AAN raw_ad_data ***
                    ad_with_search_term = ad.copy()
                    ad_with_search_term['search_term'] = term
                    notify(title, link, image_url, ad_with_search_term)
                    # ******************************************************************

        except requests.exceptions.RequestException as e:
            print(f"❌ Netwerkfout bij ophalen advertenties voor '{term}': {e}")
        except json.JSONDecodeError as e:
            print(f"❌ Fout bij parsen JSON voor '{term}': {e}")
        except Exception as e:
            print(
                f"❌ Algemene fout bij ophalen/parsen van advertenties voor '{term}': {e}"
            )


if __name__ == "__main__":
    while True:
        try:
            with open("zoekwoorden.txt", "r") as f:
                new_keywords = [x.strip() for x in f.readlines() if x.strip()]
            if not new_keywords:
                print(
                    "🛑 Geen zoekwoorden gevonden in 'zoekwoorden.txt'. Script wacht tot er zoekwoorden zijn."
                )
                time.sleep(60)
                continue
            zoekwoorden = new_keywords
        except FileNotFoundError:
            print(
                "🛑 'zoekwoorden.txt' niet gevonden. Maak dit bestand aan en voeg zoekwoorden toe (één per regel)."
            )
            time.sleep(60)
            continue

        seen = load_seen()
        print(
            f"Geladen geziene advertenties ({len(seen)} zoektermen): {sum(len(v) for v in seen.values())} advertenties"
        )
        check_marktplaats(zoekwoorden, seen)
        save_seen(seen)
        print("⏳ Even wachten...\n")
        time.sleep(60)
