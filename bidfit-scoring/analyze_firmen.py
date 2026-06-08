"""
Firmenbewerter für BidFit
Ordnerstruktur:
    - analyze_firmen.py  (dieses Script)
    - INPUT_FOLDER/ (CSV-Dateien aus Indeed-Scraping)
    - OUTPUT_FOLDER/ (Ausgabe der Bewertungen als CSV)

Workflow:
    - Keyword in Indeed scrapen mithilfe von Apify oder ändlichem Tool
    - Ergebnis in INPUT_FOLDER/ exportieren
    - von GPT bewerten lassen (diese Datei)
    - <keyword>Result.csv erscheint in OUTPUT_FOLDER/
    - ggf. Firmen kontaktieren bei Interesse

Anleitung:
  1- gültigen OpenAI API Key bei API_KEY eintragen
  2- GPT Modell eintragen (z.B. "gpt-4o-mini" oder neuer, wenn verfügbar)
  3- INPUT_FOLDER-Name eintragen (z.B. "gescrapte_listen")
  4- OUTPUT_FOLDER-Name eintragen (z.B. "results")
  5- Gescrapte CSV-Dateien in INPUT_FOLDER/ ablegen
     P.S.: Man muss die Ordner nicht manuell anlegen, das Script erstellt sie automatisch.
  6- gescrapte Keywords in KEYWORDS (Liste) eintragen,
    die Reihenfolge muss mit den CSV-Dateien übereinstimmen
  7- Ausführen: python analyze_firmen.py

VORAUSSETZUNGEN:
  pip install openai pandas --upgrade
  (min. openai 1.51.0 gebraucht)
"""

from pathlib import Path
from openai import OpenAI
from hilfsfunktionen import output_path_from_keyword, fetch_bidfit_context, process_file

API_KEY       = ""
MODEL         = "gpt-4o-mini"
INPUT_FOLDER  = "gescrapte_listen"
OUTPUT_FOLDER = "results"

client = OpenAI(api_key=API_KEY)

KEYWORDS = [
    "Angebotsmanagement",
    "Ausschreibungsmanagement",
    "Bid Management",
    "Business Development Logistik",
    "Head of Sales Logistik",
    "Key Account Manager Logistik"
    "Vertriebsleiter Logistik",
    "Tender Management"
]

def main() -> None:
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

    input_files = sorted(Path(INPUT_FOLDER).glob("*.csv"))

    if not input_files:
        print(f"Keine CSV-Dateien in '{INPUT_FOLDER}/' gefunden.")
        print(f"Lege deine gescrapten Listen dort ab und starte neu.")
        print(f"Namensschema: <keyword>IndeedScraped.csv")
        print(f"  z.B. tenderManagerIndeedScraped.csv")
        return

    pairs = list(zip(input_files, KEYWORDS))
 
    if len(input_files) > len(KEYWORDS):
        print(f"WARNUNG: {len(input_files)} Dateien, aber nur {len(KEYWORDS)} Keywords.")
        print(f"  Die letzten {len(input_files) - len(KEYWORDS)} Datei(en) werden übersprungen.")
        print(f"  → Keywords in KEYWORDS-Liste ergänzen und neu starten.\n")
    elif len(KEYWORDS) > len(input_files):
        print(f"INFO: {len(KEYWORDS)} Keywords, aber nur {len(input_files)} Datei(en).")
        print(f"  Nicht benötigte Keywords werden ignoriert.\n")
 
    print(f"Gefundene Listen ({len(pairs)}):")
    for csv_path, kw in pairs:
        print(f"  • [{kw}]  {csv_path.name}  →  {output_path_from_keyword(kw, OUTPUT_FOLDER).name}")
    print()

    bidfit_kontext = fetch_bidfit_context(client, MODEL)

    for csv_path, keyword in pairs:
        process_file(csv_path, keyword, OUTPUT_FOLDER, bidfit_kontext, client, MODEL)

    print("=" * 60)
    print(f"Alle Listen verarbeitet. Ergebnisse in '{OUTPUT_FOLDER}/'")


if __name__ == "__main__":
    main()
