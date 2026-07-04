#Anleitung in readme.md folgen

from pathlib import Path
from openai import OpenAI
from hilfsfunktionen import output_path_from_keyword, fetchContext, process_file

API_KEY       = ""
MODEL         = "gpt-4o-mini"
INPUT_FOLDER  = "gescrapte_listen"
OUTPUT_FOLDER = "results"

client = OpenAI(api_key=API_KEY)

KEYWORDS = []

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

    kontext = fetchContext(client, MODEL)

    for csv_path, keyword in pairs:
        process_file(csv_path, keyword, OUTPUT_FOLDER, kontext, client, MODEL)

    print("=" * 60)
    print(f"Alle Listen verarbeitet. Ergebnisse in '{OUTPUT_FOLDER}/'")


if __name__ == "__main__":
    main()
