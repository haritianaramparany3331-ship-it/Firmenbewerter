import json
import time
from pathlib import Path
import pandas as pd
from openai import OpenAI


def words_to_camel(text: str) -> str:
    """
    Wandelt einen Keyword-String in camelCase um (für den Ausgabe-Dateinamen). ok
      'Tender Manager'              → 'tenderManager'
      'Key Account Manager Logistik'→ 'keyAccountManagerLogistik'
      '3PL'                         → '3PL'
    """
    words = text.strip().split()
    if not words:
        return "output"
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def output_path_from_keyword(keyword: str, output_folder: str) -> Path:
    """
    Berechnet den Ausgabepfad aus dem Keyword.
      'Tender Manager' → results/tenderManagerResult.csv
      '3PL'            → results/3PLResult.csv
    """
    return Path(output_folder) / f"{words_to_camel(keyword)}Result.csv"


def extract_text(response) -> str:
    """Extrahiert reinen Text aus einer OpenAI Responses-API-Antwort."""
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
    """Entfernt Markdown-Backticks, die das Modell manchmal trotz Anweisung setzt."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    return raw


def _default_result(reason: str) -> dict:
    """Standardwerte bei API-Fehler oder ungültigem JSON."""
    return {
        "website":                              None,
        "telefon":                              None,
        "email":                                None,
        "score":                                0,
        "qualified":                            False,
        "nimmt_an_ausschreibungen_teil":        "keine Info",
        "schreibt_ausschreibungen_auf_website": "keine Info",
        "beweis_teilnahme":                     "keine Info",
        "beweis_ausschreibungen_website":       "keine Info",
        "meinung":                              reason,
    }

def fetch_bidfit_context(client: OpenAI, model: str) -> str:
    """
    Lädt per Web-Suche gründliche Informationen über BidFit.
    Wird einmal beim Start geladen und für alle CSV-Dateien wiederverwendet.
    """
    print("Lade BidFit-Kontext per Web-Suche (einmalig für alle Listen)...")
    try:
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search_preview"}],
            input=(
                "Besuche https://www.bidfit.de/ vollständig – alle Unterseiten, die du "
                "findest (z. B. /about, /features, /leistungen, /de, /en). "
                "Fasse auf Deutsch in 6–10 präzisen Sätzen zusammen:\n"
                "1. Was macht BidFit genau?\n"
                "2. Welches Problem löst BidFit?\n"
                "3. Für welche Art von Unternehmen und Branchen ist BidFit gedacht?\n"
                "4. Welchen konkreten Mehrwert hat BidFit für seine Kunden?\n"
                "5. Was unterscheidet BidFit von manuellen Prozessen?"
            ),
        )
        ctx = extract_text(response)
        if ctx:
            print(f"  → BidFit-Kontext geladen ({len(ctx)} Zeichen).\n")
            return ctx
    except Exception as e:
        print(f"  WARNUNG: Web-Suche für BidFit fehlgeschlagen ({e}). Nutze Fallback.\n")

    return (
        "BidFit (https://www.bidfit.de/) ist ein KI-gestütztes SaaS-Tool, das "
        "Ausschreibungs- und Tender-Management-Prozesse für Unternehmen automatisiert "
        "und vereinfacht – insbesondere in der Logistik- und Supply-Chain-Branche. "
        "BidFit richtet sich an zwei Zielgruppen: (A) Unternehmen, die als Bieter "
        "an externen Ausschreibungen/Vergabeverfahren teilnehmen, sowie (B) Unternehmen, "
        "die selbst Ausschreibungen veröffentlichen und Angebote einholen. "
        "Das Tool hilft dabei, relevante Ausschreibungen zu identifizieren, zu analysieren "
        "und effizienter darauf zu reagieren."
    )


def analyze_company(
    company_name: str,
    description:  str,
    position:     str,
    company_url:  str,
    keyword:      str,
    bidfit_kontext: str,
    client: OpenAI,
    model: str
) -> dict:
    """
    Bewertet eine einzelne Firma mit GPT + Web-Suche.
    Das keyword wird aus dem Dateinamen abgeleitet und in den Prompt injiziert.
    """
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

    prompt = f"""Du bist ein präziser, emotionsloser B2B-Sales-Analyst für BidFit.

=== WAS IST BIDFIT? ===
{bidfit_kontext}

BidFit sucht als potenzielle Kunden Unternehmen, die:
  (A) Regelmäßig an Ausschreibungen / Tenders / Vergabeverfahren teilnehmen (als Bieter), ODER
  (B) Selbst Ausschreibungen veröffentlichen und Angebote einholen (als Auftraggeber).

=== WOHER KOMMT DIESE FIRMA? ===
Diese Firmenliste wurde durch ein Indeed-Scraping mit dem Suchbegriff "{keyword}" erstellt.
Die Firma hat irgendwann eine Stelle ausgeschrieben, die zu diesem Keyword passte.
Das ist ein schwacher erster Hinweis – kein Beweis für Tender-Aktivität.

WICHTIG: Indeed-Daten dürfen MAXIMAL 10 % deiner Gesamtbewertung ausmachen.
Du sollst Indeed NICHT erneut durchsuchen und keine Informationen hauptsächlich von
Indeed-URLs holen. Nutze externe Quellen: Firmenwebsite, Google, LinkedIn, Xing,
Unternehmensregister, Branchenverzeichnisse, Pressemitteilungen usw.

Firmenname: {company_name}
Positionsname (Indeed, max. 10 % Gewichtung): {position}
Stellenbeschreibung (Indeed, max. 10 % Gewichtung): {description[:800]}
{url_hint}

=== DEINE AUFGABE – SCHRITT FÜR SCHRITT ===

1. RECHERCHE (Web-Suche aktiv nutzen):
   - Finde und besuche die offizielle Firmenwebsite
   - Prüfe Unterseiten: /ausschreibungen, /vergabe, /leistungen, /services, /impressum, /kontakt
   - Suche: "{company_name} Ausschreibung", "{company_name} Tender", "{company_name} Vergabe"
   - Suche auf LinkedIn, Xing, Unternehmensregister
   - Extrahiere Telefonnummer und E-Mail aus dem Impressum

2. BEWERTUNGSFRAGEN:
   a) Nimmt das Unternehmen an externen Ausschreibungen teil (als Bieter/Dienstleister)?
   b) Veröffentlicht das Unternehmen selbst Ausschreibungen auf der eigenen Website?
   c) Welche Kontaktdaten (Telefon, E-Mail) stehen im Impressum?
   d) Wie lautet die korrekte offizielle Website-URL?

3. SCORING – schonungslos ehrlich:
   • score  0–20 : Keine Belege, keine Relevanz für BidFit → qualified = false
   • score 21–49 : Schwache oder indirekte Hinweise         → qualified = false
   • score 50–79 : Konkrete externe Belege vorhanden        → qualified = true
   • score 80–100: Starke, mehrfach belegte Tender-Aktivität → qualified = true

   ⚠ Es ist AUSDRÜCKLICH ERWÜNSCHT, dass die Firmen realistisch und kritisch für BidFit bewertet werden.
   ⚠ Kein score > 30 ohne konkrete externe Belege aus Non-Indeed-Quellen.
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
  "nimmt_an_ausschreibungen_teil":        "Ja" | "Nein" | "keine Info",
  "schreibt_ausschreibungen_auf_website": "Ja" | "Nein" | "keine Info",
  "beweis_teilnahme": "Konkreter Fund mit Quellenlink am Ende, z.B. 'Firmenwebsite listet öffentliche Ausschreibungen als Kernleistung (https://firma.de/leistungen)' – oder 'keine Info' – oder 'kein Teilnehmer'",
  "beweis_ausschreibungen_website": "Konkreter Fund mit Quellenlink am Ende, z.B. 'Vergabeseite auf Firmenwebsite gefunden (https://firma.de/ausschreibungen)' – oder 'keine Info' – oder 'keine Ausschreibungen in der Webseite'",
  "meinung": "2–3 Sätze: Einschätzung der BidFit-Relevanz + ggf. Anmerkungen zu Fehlern oder Besonderheiten (z.B. 'Website nicht erreichbar', 'Nur telefonisch erreichbar laut Impressum', 'KMU ohne nachweisbare Tender-Aktivität trotz passender Branche', 'Firma ist Behörde und vergabt selbst – kein Bieter')."
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
    


def process_file(csv_path: Path, keyword: str, output_folder: str, bidfit_kontext: str, client: OpenAI, model: str) -> None:
    """Liest eine gescrapte CSV-Datei ein, bewertet alle Firmen und speichert results."""
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
            company_name, description, position, company_url, keyword, bidfit_kontext, client, model
        )

        # Website: GPT-Fund bevorzugen, sonst CSV-URL, sonst "keine Info"
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
            "Nimmt an Ausschreibungen teil":         result.get("nimmt_an_ausschreibungen_teil",        "keine Info"),
            "Schreibt Ausschreibungen auf Website":  result.get("schreibt_ausschreibungen_auf_website", "keine Info"),
            "Beweis Teilnahme":                      result.get("beweis_teilnahme",                     "keine Info"),
            "Beweis Ausschreibungen auf Website":    result.get("beweis_ausschreibungen_website",        "keine Info"),
            "Meinung / Anmerkungen":                 result.get("meinung", ""),
        })

        time.sleep(2.0)  # Pause: Web-Suche braucht mehr Zeit als reine Completions

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    # utf-8-sig: Excel zeigt Umlaute korrekt an

    qualified = results_df["Qualified"].value_counts().get("Ja", 0)
    print(f"\n  → Gespeichert: {output_file}")
    print(f"  → Qualifiziert: {qualified} von {total}\n")
