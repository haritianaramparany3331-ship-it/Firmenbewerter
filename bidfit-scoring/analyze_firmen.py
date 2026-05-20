"""
analyze_firmen.py
-----------------
Liest firmenliste.csv ein, analysiert jede Zeile mit GPT-4.1-mini
und speichert die Ergebnisse in results.csv.

ANLEITUNG:
1. Trage deinen OpenAI API Key unten bei API_KEY ein (Zeile 22)
2. Stelle sicher, dass firmenliste.csv im gleichen Ordner liegt
3. Starte das Script mit: python analyze_firmen.py
"""

import pandas as pd
import json
import time
from openai import OpenAI

# ============================================================
# HIER deinen OpenAI API Key eintragen:
API_KEY = "REMOVED"
# ============================================================

# OpenAI Client erstellen
client = OpenAI(api_key=API_KEY)

# Die Begriffe, nach denen GPT suchen soll
KEYWORDS = [
    "Tender Management",
    "Tender Manager",
    "Bid Management",
    "Ausschreibungsmanagement",
    "Angebotsmanagement",
    "Kontraktlogistik",
    "3PL",
    "Supply Chain Solutions",
    "Strategic Sales",
    "Key Account Manager Logistik",
]

def analyze_company(company_name: str, description: str, position: str) -> dict:
    """
    Schickt die Unternehmensdaten an GPT und bekommt eine JSON-Analyse zurück.
    Gibt ein dict mit: qualified, score, evidence, reason
    """

    # Prompt für GPT aufbauen
    prompt = f"""
Du bist ein Experte für Logistik und Ausschreibungen (Tenders/Bids).

Analysiere folgendes Unternehmen und entscheide, ob es wahrscheinlich 
an Ausschreibungen/Tendern teilnimmt oder diese durchführt.

Unternehmen: {company_name}
Position: {position}
Beschreibung: {description[:3000]}

Suche besonders nach diesen Begriffen oder ähnlichen Konzepten:
{", ".join(KEYWORDS)}

Antworte NUR mit einem JSON-Objekt in diesem Format (kein Text davor oder danach):
{{
  "qualified": true oder false,
  "score": Zahl zwischen 0 und 100,
  "evidence": ["gefundener Begriff 1", "gefundener Begriff 2"],
  "reason": "Kurze Begründung auf Deutsch"
}}

- qualified: true wenn score >= 50
- score: 0 = kein Hinweis, 100 = sehr starke Hinweise
- evidence: Liste der gefundenen Schlüsselbegriffe aus dem Text
- reason: 1-2 Sätze Begründung
"""

    try:
        # API-Aufruf an GPT-4.1-mini
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,  # 0 = konsistentere Antworten
            max_tokens=400,
        )

        # Antwort-Text aus dem Response holen
        raw_text = response.choices[0].message.content.strip()

        # JSON parsen
        result = json.loads(raw_text)
        return result

    except json.JSONDecodeError:
        # Falls GPT kein gültiges JSON zurückgibt
        print(f"  WARNUNG: Ungültiges JSON für '{company_name}' – setze Standardwerte")
        return {
            "qualified": False,
            "score": 0,
            "evidence": [],
            "reason": "Fehler beim Parsen der GPT-Antwort"
        }
    except Exception as e:
        # Falls ein anderer Fehler auftritt (z.B. API-Problem)
        print(f"  FEHLER bei '{company_name}': {e}")
        return {
            "qualified": False,
            "score": 0,
            "evidence": [],
            "reason": f"API-Fehler: {str(e)}"
        }


def main():
    # ---- Schritt 1: CSV einlesen ----
    print("Lese firmenliste.csv ein...")
    df = pd.read_csv("firmenliste.csv")
    print(f"  -> {len(df)} Zeilen gefunden\n")

    # Neue Spalten vorbereiten (leer, werden später befüllt)
    df["qualified"] = None
    df["score"] = None
    df["evidence"] = None
    df["reason"] = None

    # ---- Schritt 2: Jede Zeile analysieren ----
    total = len(df)

    for index, row in df.iterrows():
        # Daten aus der Zeile holen (leere Felder = leerer String)
        company_name = str(row.get("company", "")) or ""
        description  = str(row.get("description", "")) or ""
        position     = str(row.get("positionName", "")) or ""

        print(f"[{index + 1}/{total}] Analysiere: {company_name} – {position}")

        # GPT-Analyse durchführen
        result = analyze_company(company_name, description, position)

        # Ergebnisse in den DataFrame schreiben
        df.at[index, "qualified"] = result.get("qualified", False)
        df.at[index, "score"]     = result.get("score", 0)
        df.at[index, "evidence"]  = json.dumps(result.get("evidence", []), ensure_ascii=False)
        df.at[index, "reason"]    = result.get("reason", "")

        # Kurze Pause zwischen den API-Aufrufen (verhindert Rate-Limit-Fehler)
        time.sleep(0.3)

    # ---- Schritt 3: Ergebnisse speichern ----
    output_file = "results.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    # utf-8-sig sorgt dafür, dass Excel Umlaute richtig anzeigt

    # Zusammenfassung anzeigen
    qualified_count = df["qualified"].sum()
    print(f"\nFertig! Gespeichert als '{output_file}'")
    print(f"Qualifizierte Unternehmen: {qualified_count} von {total}")


# Script starten
if __name__ == "__main__":
    main()
