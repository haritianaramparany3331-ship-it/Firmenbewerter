import json
import time
from pathlib import Path
import pandas as pd
from openai import OpenAI


def words_to_camel(text: str) -> str:
    words = text.strip().split()
    if not words:
        return "output"
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def output_path_from_keyword(keyword: str, output_folder: str) -> Path:
    return Path(output_folder) / f"{words_to_camel(keyword)}Result.csv"


def extract_text(response) -> str:
    parts = []
    try:
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []):
                    text = getattr(part, "text", None)
                    if text:
                        parts.append(text)
    except Exception:
        pass
    return "".join(parts).strip()


def clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    return raw


def _default_result(reason: str) -> dict:
    return {
        "website":                              None,
        "telefon":                              None,
        "email":                                None,
        "score":                                0,
        "qualified":                            False,
        "meinung":                              reason,
    }

def fetchContext(client: OpenAI, model: str) -> str:
    print("Lade Kontext per Web-Suche (einmalig für alle Listen)...")
    try:
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search_preview"}],
            input=(
                #Prompt für den Kontext (zB über meine Firma), es macht hier Websuche,
                #wenn es Informationen übers Internet suchen soll.
                #also worauf sich GPT konzentrieren soll, wenn es die Firmen bewertet
                #Ansonsten kann man selber in return als default selbst schreiben, was GPT wissen soll.
                #in diesem Fall sollte man das ganze try except Block entfernen
            ),
        )
        ctx = extract_text(response)
        if ctx:
            print(f"  → Kontext geladen ({len(ctx)} Zeichen).\n")
            return ctx
    except Exception as e:
        print(f"  WARNUNG: Web-Suche für den Kontext fehlgeschlagen ({e}). Nutze Fallback.\n")

    return (
        #hier Default Text, wenn Websuche nicht nötig ist
    )


def analyze_company(
    company_name: str,
    description:  str,
    position:     str,
    company_url:  str,
    keyword:      str,
    kontext: str,
    client: OpenAI,
    model: str
) -> dict:
    if company_url and company_url.lower() not in ("nan", "", "none"):
        url_hint = (
            f"URL aus den Indeed-Daten: {company_url}\n"
            f"(Prüfe, ob das die echte Firmenwebsite ist – korrigiere falls nötig. "
            f"Indeed-interne URLs wie 'indeed.com/cmp/...' sind keine Firmenwebsites.)"
        )
    else:
        url_hint = (
            "Keine URL bekannt – suche im Web selbst nach der offiziellen Website "
            f"von '{company_name}'."
        )
    #hier der Hauptprompt einfügen oder diesen Template ausfüllen
    prompt = f"""

=== WAS IST DER KONTEXT? ===
{kontext}

=== WOHER KOMMT DIESE FIRMEN? ===

=== DEINE AUFGABE – SCHRITT FÜR SCHRITT ===

1. RECHERCHE (Web-Suche aktiv nutzen):

2. BEWERTUNGSFRAGEN:

3. SCORING – schonungslos ehrlich:
   • score  0–20 : ...  → qualified = false
   • score 21–49 : ...  → qualified = false
   • score 50–79 : ...  → qualified = true
   • score 80–100: ...  → qualified = true

   ⚠ Es ist AUSDRÜCKLICH ERWÜNSCHT, dass die Firmen realistisch und kritisch für {kontext} bewertet werden.
   ⚠ Kein score > 30 ohne konkrete externe Belege.
   ⚠ Keine Empathie. Keine Schönfärberei. Wenn keine Evidenz vorhanden ist: score niedrig.
   ⚠ Wenn du die Website nicht findest oder sie nicht erreichbar ist: score ≤ 15.

=== AUSGABEFORMAT ===
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt.
Kein Text davor oder danach. Keine Markdown-Backticks. Kein Kommentar.

=== AUSGABE ===
Nur JSON. Kein Text davor/danach. Keine Markdown-Backticks. Kein Kommentar.

{{
  "website":  "https://... (offizielle Firmenwebsite) oder null",
  "telefon":  "Telefonnummer aus Impressum oder null",
  "email":    "E-Mail-Adresse aus Impressum oder null",
  "score":    (Integer 0–100),
  "qualified": (true oder false),
  "meinung": "2–3 Sätze: ..."
}}"""

    try:
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        raw = clean_json(extract_text(response))
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    WARNUNG: Ungültiges JSON für '{company_name}' – {e}")
        return _default_result(f"JSON-Fehler: {e}")
    except Exception as e:
        print(f"    FEHLER bei '{company_name}': {e}")
        return _default_result(f"API-Fehler: {str(e)}")
    


def process_file(csv_path: Path, keyword: str, output_folder: str, kontext: str, client: OpenAI, model: str) -> None:
    output_file = output_path_from_keyword(keyword, output_folder)

    print(f"\n{'=' * 60}")
    print(f"  Datei:    {csv_path.name}")
    print(f"  Keyword:  {keyword}")
    print(f"  Ausgabe:  {output_file}")
    print(f"{'=' * 60}\n")

    df = pd.read_csv(csv_path)
    total = len(df)
    print(f"  → {total} Firmen gefunden.\n")

    results = []
    
    for index, row in df.iterrows():
        company_name = str(row.get("company",         "") or "").strip()
        description  = str(row.get("description",     "") or "").strip()
        position     = str(row.get("positionName",    "") or "").strip()
        company_url  = str(row.get("companyInfo/url", "") or "").strip()

        print(f"  [{index + 1}/{total}] {company_name}  –  {position}")

        result = analyze_company(
            company_name, description, position, company_url, keyword, kontext, client, model
        )

        website = result.get("website")
        if not website or str(website).lower() in ("null", "none", ""):
            website = (
                company_url
                if company_url and company_url.lower() not in ("nan", "")
                else "keine Info"
            )

        results.append({
            "Firmenname":                            company_name,
            "Website":                               website,
            "Kontakt Telefon":                       result.get("telefon") or "keine Info",
            "Kontakt E-Mail":                        result.get("email")   or "keine Info",
            "Score (/100)":                          result.get("score", 0),
            "Qualified":                             "Ja" if result.get("qualified") else "Nein",
            "Meinung / Anmerkungen":                 result.get("meinung", ""),
        })

        time.sleep(2.0) 

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    qualified = results_df["Qualified"].value_counts().get("Ja", 0)
    print(f"\n  → Gespeichert: {output_file}")
    print(f"  → Qualifiziert: {qualified} von {total}\n")
