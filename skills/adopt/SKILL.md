---
name: adopt
description: "Richtet einen Arbeitsordner ein, klont den Upstream und extrahiert daraus das Fachregelwerk. Triggers on: /zeugnis-kit:adopt [pfad]"
disable-model-invocation: true
argument-hint: "[pfad zum arbeitsordner]"
---

Du richtest den Arbeitsordner ein. Danach ist die Pipeline lauffähig; ohne
diesen Schritt fehlt ihr das Fachregelwerk, denn das Kit liefert keines mit.

## 1 — Arbeitsordner

Ohne Argument: der aktuelle Ordner. Lege an:

```bash
mkdir -p faelle gates laeufe upstream
```

Schreib eine `.gitignore`, falls keine da ist. Fälle enthalten Name,
Beschäftigungszeitraum und Leistungsbeurteilung einer identifizierbaren
Person (Z-07) — die dürfen nirgends mitversioniert werden:

```
faelle/
gates/
laeufe/
upstream/
regelwerk/
```

Ist der Ordner bereits ein Git-Repo mit Remote, frag nach, bevor du etwas
anlegst. Ein Arbeitsordner mit Zeugnisdaten gehört nicht in ein Remote.

## 2 — Upstream klonen

```bash
git clone --depth 1 https://github.com/Klotzkette/arbeitszeugnispruefer-skill \
  upstream/arbeitszeugnispruefer-skill
```

Das sind etwa 3 MB: das SKILL.md, vier Handbuchdateien, 25 Testzeugnisse als
PDF und die Testmatrix. Apache-2.0 OR MIT; die Attribution steht in `NOTICE`
und wird in jede erzeugte Regelwerk-Datei geschrieben.

## 3 — Regelwerk extrahieren

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/regelwerk_extrahieren.py" --pruefen
```

Erst `--pruefen`. Melden alle neun Schnitte Treffer, dann ohne das Flag
nochmal, und `regelwerk/` ist da.

Fehlt ein Schnitt, hat der Upstream umbenannt. Dann passt du `SCHNITTE` in
`tools/regelwerk_extrahieren.py` an — nicht die erzeugte Datei. Lauf nicht
mit halbem Regelwerk weiter: der betroffene Agent würde trotzdem urteilen,
nur schlechter, und man sähe es nicht.

Prüf danach die Größen. Erwartbar sind zwischen 10 KB und 75 KB je Datei.
Eine Datei über 150 KB heißt fast immer, dass ein Abschnitt bis zum Dateiende
durchläuft und Fremdes mitnimmt.

## 4 — Erster Fall oder erster Blindlauf

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/blindlauf.py" probe --vorbereiten
```

Listet die 25 Testzeugnisse. Damit lässt sich die Pipeline testen, bevor ein
echter Fall sie anfasst.

Für einen echten Fall: `faelle/<fall-id>/` mit dem Zeugnis und einer
`fall.json`:

```json
{
  "fall_id": "",
  "zeugnisart": "qualifiziert",
  "rechtsstatus_person": "arbeitnehmer",
  "anspruchsnorm": "",
  "ziel": "korrektur",
  "kopfdaten": {"name": "", "position": "", "beginn": "", "ende": "", "arbeitgeber": ""},
  "gesamtnote": "",
  "abdeckung": "",
  "quelle": "zeugnis.pdf"
}
```

`ziel` ist `verstehen`, `verhandeln`, `korrektur`, `klage-pruefen` oder
`erstellen`. Es steuert, welche Ausgaben die Fertig-Definition verlangt.

## 5 — Gates leer durchlaufen lassen

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/anspruchsgate.py"
python3 "${CLAUDE_PLUGIN_ROOT}/tools/fertig_definition.py"
```

Beide müssen laufen und dürfen Befunde melden — ein leerer Fall ist nicht
fertig, und dass sie das sagen, ist der Test.

## Zum Schluss

```
ARBEITSORDNER:  <pfad>
UPSTREAM:       <version> (<sha256 gekürzt>)
REGELWERK:      <n> Dateien, <kleinste>–<größte> KB
SCHNITTE:       <n> von 9 getroffen
TESTKORPUS:     <n> Zeugnisse gefunden
GATES:          anspruchsgate <lauffähig>, fertig_definition <lauffähig>
NÄCHSTER SCHRITT: /zeugnis-kit:blindlauf probe  oder  /zeugnis-kit:pruefen <fall-id>
```
