# Firmenbewerter
Ein konfigurierbares Tool zur automatischen Recherche und Bewertung von Unternehmen aus CSV-Listen mithilfe von GPT und Live-Websuche.

## Ordnerstruktur:
    - analyze_firmen.py
    - hilfsfunktionen.py  (Hilfsfunktionen)
    - INPUT_FOLDER/ (CSV-Dateien aus Indeed-Scraping)
    - OUTPUT_FOLDER/ (Ausgabe der Bewertungen als CSV)
    - ExampleForPrompts (wo man ein Beispiel für die Prompts für eine gewählte Beispielfirma)

## Workflow:
    - über eine Liste von Firmen verfügen (zB aus Indeed)
    - Liste in INPUT_FOLDER/ exportieren
    - von GPT bewerten lassen
    - <keyword>Result.csv mit neuen Bewertungsspalten erscheint in OUTPUT_FOLDER/
    - Dateien öffnen und prüfen

## Anleitung:
  1. gültigen OpenAI API Key bei API_KEY eintragen ("sk-...")
  2. GPT Modell eintragen (z.B. "gpt-4o-mini" oder neuer, wenn verfügbar)
  3. INPUT_FOLDER-Name anpassen (als Default: `gescrapte_listen`)
  4. OUTPUT_FOLDER-Name anpassen (als Default: `results`)
  5. Gescrapte CSV-Dateien in INPUT_FOLDER/ ablegen
     P.S.: Man muss die Ordner nicht manuell anlegen, das Script erstellt sie automatisch.
     Achtung: Man sollte die Name der Spalten für das Parsen in der Funktion process_file evt. anpassen,
              sodass die mit den Spaltennamen in den CSV-Dateien übereinstimmen
              (als Default: "company", "description", "positionName", "companyInfo/url")
  6. Keyword-Liste ausfüllen mit den Keywords, die die Liste erzeugt hat (beim Scrapen).
     Das Ablegen von Keyword muss gemacht werden, auch wenn die Liste mit keinem Keyword erstellt wurde,
     in diesem Fall kann man einfach der Name der CSV-Datei übernehmen (ohne .csv-Endung)
     Die Reihenfolge muss bei mehreren Listen mit den CSV-Dateien übereinstimmen (wichtig für den Namen)
  7. Prompts richtig ausfüllen:
      - in `fetchContext()`: 2 Optionen:
        *erstmal Websuche, dann gibt man Anleitungen zu GPT mit einer Internetquelle
        *als Default in return selbst die Informationen schreiben.
          (Muss aber dann den try except Block entfernen)
      - in `analyze_company()`: Hauptprompt 2 Optionen:
        *man kann seinen Prompt einfügen (muss den Template löschen)
        *man kann den als Default angelegten Template ausfüllen
  8. `default_result()` kann weiterangepasst werden. Die Spalten da sind nur als Default für das Scoring gedacht
     Man muss dafür aber auch dann den Hauptprompt und die Funktion process_file() anpassen
  9. Ausführen: `python analyze_firmen.py`
  P.S.: Wenn es mit den Prompts zu Hürden kommt, habe ich auch in `ExampleForPrompts/`
    ein Beispiel für die Prompts für eine gewählte Beispielfirma. Man kann einfach nachmachen

## Voraussetzungen:
  `pip install openai pandas --upgrade`
  (min. openai 1.51.0 gebraucht)
