# n8n Workflows

Die Research-Funktion ist bewusst in zwei eigenständige Workflows aufgeteilt. Die Missionsgenerierung verwendet zusätzlich den neu aufgebauten V2-Orchestrator und einen getrennten Single-Mission-Worker.

## AI Mission Generator V2

- Workflow-IDs: `MissionGeneratorV2Prod` und `MissionWorkerV2Prod`
- Produktiver Webhook: `POST /webhook/mission-generation`
- Interner Worker-Webhook: `POST /webhook/mission-generation-worker-v2`
- Vor einer Wochengenerierung ruft der Orchestrator den Research-Selector lokal auf. Bei einer normalen Woche werden
  abhängig von der Zahl der Quiz-Missionen höchstens zwei bis drei passende aktuelle Kontexte zugeordnet.
- Research-Kontext wird nur an die konkret ausgewählte Quiz-Mission weitergereicht. Generator, Reviewer und Repair
  erhalten denselben geprüften Kontext; Task-Missionen und die übrigen Quiz-Missionen bleiben Evergreen-Inhalte.
- Ein leerer Pool, eine nicht passende Auswahl oder ein Ausfall des Selectors blockiert die Missionsgenerierung nicht.
  Der Lauf wird dann ohne Research-Kontext fortgesetzt und hinterlegt eine Warnung im Review-Bericht.
- Modellaufrufe laufen in echten Zweier-Batches, damit die Kapazitätsgrenze des Modellendpunkts nicht überschritten wird.
- Jede Mission wird unabhängig validiert und reviewed; höchstens zwei gezielte Repair-Versuche sind möglich.
- Der semantische Reviewer erhält bei großen Task-Missionen nur eine kompakte, repräsentative Projektion; Schema,
  Zeilenzahlen, Berechnungen und Lösungen werden weiterhin deterministisch von Django geprüft.
- Task-Schwierigkeiten verwenden verbindliche Daten- und Ergebnisprofile: Easy hat weniger Datensätze und Kennzahlen,
  Medium erweitert beides, Hard verwendet den größten Datensatz und zusätzliche Prüfkennzahlen. Aufgabenformulierungen,
  auswertbare Ergebnisfelder und Punkte werden passend dazu deterministisch von Django synchronisiert.
- Repairs liefern kleine, whitelist-validierte `replace`-Patches statt die komplette Mission erneut zu erzeugen.
- Ein nicht anwendbarer Patch wird direkt erneut repariert; er durchläuft nicht unnötig nochmals Validierung und Review.
- Status-Callbacks werden vor Validierung, Review und Repair durch Merge-Gates abgeschlossen, damit die UI den
  aktuellen Schritt zuverlässig und auch nach einem Seitenwechsel anzeigt.
- Ein einzelner Fehlschlag beendet nicht die übrigen Missionen. Erfolgreiche Ergebnisse werden als Teilabschluss an Django übergeben.
- Generator-, Review- und Repair-Ausgaben werden zentral als JSON normalisiert und anschließend deterministisch durch Django validiert.

Die Datei `ai-mission-generator-v2.json` enthält beide zusammengehörigen Workflows. Beim Import müssen die vorhandenen Header-Auth-Credentials für Django/n8n und den KI-Endpunkt verfügbar sein. Der vorherige `AI Mission Generator` bleibt deaktiviert als Rückfalloption; `AI Mission Generator Backup` wurde nicht verändert.

## 1. AI Finance Research - Collector

- Workflow-ID: `RsrchCollect2026`
- Zeitplan: täglich um 06:15 Uhr, Zeitzone `Europe/Berlin`
- Manueller Trigger im n8n-Editor
- Authentifizierter Webhook: `POST /webhook/ai-finance-research-collector-run`
- Optionaler Request-Body für eine vollständige Neubewertung: `{"force_refresh": true}`

Der Collector liest ausschließlich konfigurierte Feeds offizieller Institutionen:

- European Banking Authority (EBA)
- Bank for International Settlements (BIS und FSI)
- European Central Bank (Presse und Blog)
- European Commission Digital Strategy
- BaFin

Die Verarbeitung besteht aus einem 45-Tage-Aktualitätsfilter, einer harten KI-und-Finanz-Relevanzprüfung, URL- und Inhalts-Deduplizierung, einer strukturierten KI-Bewertung und einer abschließenden deterministischen Validierung. RSS-Inhalte werden als nicht vertrauenswürdige Daten behandelt; Anweisungen aus einem Feed dürfen nicht ausgeführt werden. Nur direkt vom Feedtext gestützte Fakten werden übernommen.

Falls der KI-Endpunkt ausfällt oder eine nicht verwertbare Antwort liefert, greift ein konservativer Fallback. Vor einer erneuten Bewertung werden betroffene Datensätze vorsorglich deaktiviert und nur bei erfolgreicher Prüfung wieder freigegeben. Damit bleiben abgelehnte oder veraltete Ergebnisse nicht versehentlich auswählbar.

Gespeichert wird in der n8n Data Table `ai_finance_research_pool`. Die Tabelle wird beim ersten Lauf automatisch angelegt. Wichtige Felder sind:

- stabile `item_key` und `content_hash` für Idempotenz
- Quelle, Original-URL, Veröffentlichungs-, Abruf- und Ablaufzeit
- deutsche und englische Kurzfassung
- belegte Fakten mit Evidenzausschnitten
- Mission-Hooks und Tags
- Relevanz, Confidence, Risikoflags und Analysemethode
- `eligible` als harte Freigabe für den Selector

## 2. AI Finance Research - Context Selector

- Workflow-ID: `RsrchSelect2026A`
- Aufruf als n8n-Subworkflow über `Execute Workflow`
- Authentifizierter Webhook: `POST /webhook/ai-finance-research-context-selector`
- Manueller Test-Trigger mit Beispieldaten im Editor

Beispielinput:

```json
{
  "generation_run_id": "example-run",
  "generation_kind": "weekly_missions",
  "as_of": "2026-08-23T12:00:00Z",
  "max_research_missions": 2,
  "preferred_tags": ["ai_governance", "risk", "banking"],
  "requirements": [
    {
      "id": "2026-08-24",
      "scheduled_date": "2026-08-24",
      "output_type": "quiz_mission",
      "requested_mission_type": "single_choice"
    },
    {
      "id": "2026-08-25",
      "scheduled_date": "2026-08-25",
      "output_type": "task_mission",
      "mission_type": "invoice_extraction"
    }
  ]
}
```

Der Selector berücksichtigt nur freigegebene, noch gültige Einträge mit belegten Fakten und mittlerer oder hoher Confidence. Die Auswahl ist deterministisch und gewichtet Relevanz, Quellenstufe, Confidence, Aktualität, bevorzugte Tags und Missionstyp. Aktuell erhalten ausschließlich Anforderungen mit `output_type: "quiz_mission"` Research-Kontext. Task-Missionen bleiben unverändert.

Standardmäßig werden höchstens zwei Research-Beiträge gewählt; über `max_research_missions` sind null bis maximal drei möglich. Ein Pool-Eintrag wird innerhalb eines Aufrufs nur einmal verwendet. Bei leerem Pool, nicht passenden Anforderungen oder unterschrittenem Score liefert der Workflow erfolgreich einen leeren `research_context` samt Warnung zurück. Die Missionsgenerierung läuft dann normal mit Evergreen-Inhalten weiter.

Jeder ausgewählte Kontext enthält Sicherheitsanweisungen: nur `safe_facts` verwenden, Quelleninhalt als nicht vertrauenswürdig behandeln, keine Rechtsberatung ableiten, das Lernziel übertragbar halten und die Quelle im Review prüfen.

## Authentifizierung

Beide Webhooks erwarten den Header `X-N8N-Service-Secret`. In der lokalen n8n-Instanz verwenden sie die bereits vorhandene Header-Auth-Credential. Geheimnisse werden nicht in den exportierten Workflow-Dateien gespeichert.

## Integration in die Missionsgenerierung

Der V2-Orchestrator ruft den veröffentlichten Selector vor der eigentlichen Prompt-Erstellung über dessen internen,
authentifizierten Webhook auf. Die Zuordnung erfolgt über `context_by_requirement[requirement.id]`; damit kann kein
Research-Beitrag versehentlich in eine andere Mission oder Schwierigkeit rutschen. Der Prompt grenzt den Beitrag als
nicht vertrauenswürdige Referenzdaten ab und erlaubt ausschließlich die geprüften `safe_facts`. Bei vorhandenem Kontext
muss die Quiz-Mission Quelle und Veröffentlichungsdatum nennen, den aktuellen Anlass als Szenario verwenden und trotzdem
ein übertragbares Lernziel vermitteln. Der Reviewer prüft diese Regeln, und der Repair-Schritt erhält denselben Kontext.
