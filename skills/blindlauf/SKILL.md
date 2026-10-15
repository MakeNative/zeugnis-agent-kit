---
name: blindlauf
description: "Fährt die Prüf-Strecke blind über die 25 Upstream-Testzeugnisse und wertet sie gegen Sollkorridor und Überdehnungskatalog aus. Triggers on: /zeugnis-kit:blindlauf <lauf-name> [--nur 01,03,09]"
disable-model-invocation: true
argument-hint: "<lauf-name> [--nur <nummern>]"
---

Du messt die Pipeline. Zwei Zahlen, die sich nicht gemeinsam optimieren
lassen: Korridortreffer und Überdehnungsrate (M-02).

Der Lauf heißt blind, weil er blind sein muss. Ein Lauf, der den
Erwartungshorizont im Kontext hatte, hat nichts gemessen (M-01).

## 1 — Vorbereiten

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/blindlauf.py" <lauf-name> --vorbereiten
```

Legt `laeufe/<lauf-name>/` an und listet die 25 Testzeugnisse mit ihren
Nummern.

## 2 — Die Lösung bleibt zu

Ab hier gilt bis Schritt 5:

- `upstream/.../testakten/TESTFALL-MATRIX.md` — **nicht öffnen**
- `.../90-erwartungshorizont-und-pruefpunkte.md` — **nicht öffnen**
- `.../README.md` der Testaktensätze — **nicht öffnen**, sie nennen Tendenzen

Auch nicht „nur um die Nummern zuzuordnen". Die Zuordnung steht in der
Vorbereitungsausgabe.

Und der Katalog muss raus. Der `ueberdehnungs-pruefer` liest normalerweise den
Negativkatalog in `regelwerk/ueberdehnung.md` — nach Rollen sortierte Einträge
aus genau dieser Matrix. Im Produktivbetrieb ist das ein Regelkatalog; hier
wäre es der Lösungsschlüssel zu dem Fall, den er gerade beurteilt. Also vor
dem Lauf neu extrahieren:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/regelwerk_extrahieren.py" --ohne-katalog
```

Dann hat er nur D.5 aus dem SKILL.md — allgemeine Regeln über sensible
Kontextsignale, keine fallbezogene Antwort. Den Katalog bekommt der
`lauf-auswerter`, und zwar erst in Schritt 5.

Nach dem Lauf ohne `--ohne-katalog` neu extrahieren, sonst läuft der
Produktivbetrieb mit halbem Regelwerk.

Prüf einmal, dass in `ueberdehnung.md` keine Sollnoten stehen:

```bash
grep -c 'Sollkorridor' regelwerk/ueberdehnung.md   # muss 0 sein
```

## 3 — Je Fall die Prüf-Strecke

Für jeden Fall: `faelle/blind-<nr>/` anlegen, das PDF hineinkopieren oder
verlinken, `fall.json` mit `ziel: "verstehen"` und `zeugnisart` aus dem
Dokument selbst.

Dann die Strecke aus `/zeugnis-kit:pruefen` fahren — mindestens:
`satz-leser` → `noten-bewerter` → `drift-pruefer` → `schluss-pruefer` →
Befunde → `ueberdehnungs-pruefer`.

Fahr die Fälle **in Wellen von vier bis sechs**, nicht alle gleichzeitig: bei
vielen parallelen Agenten ist der Verbindungsabbruch der Normalfall, nicht die
Ausnahme (P-07), und ein halber Bericht sieht brauchbar aus.

Die Übernahme läuft über `uebernehmen.py`, nicht von Hand — bei 25 Fällen ist
das nicht Bequemlichkeit, sondern die Bedingung dafür, dass die Messung etwas
wert ist. Wer Karten abtippt, hält jede Note einmal in der Hand.

Der `form-pruefer` liefert bei den Testakten wenig — es gibt keine
Vergleichsunterlagen und keine Bilder zu prüfen. Lass ihn weg und schreib das
in den Bericht, statt seine Befunde als „ohne Beanstandung" zu zählen (P-06).

Schreib je Fall `laeufe/<lauf-name>/<nr>.md`:

```
FALL: 03
GESAMTNOTE: 3
BEFUNDE
- <ein Befund je Zeile, in einem Satz>
- <…>
```

Die Befundzeilen sind das, was später gegen den Überdehnungskatalog läuft.
Schreib sie so, wie sie in einem Prüfvermerk stünden — nicht abgeschwächt.
Eine vorsichtig formulierte Behauptung ist für die Messung eine Fälschung.

## 4 — Auswerten

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/blindlauf.py" <lauf-name>
```

Schreibt `AUSWERTUNG.md` mit den Korridortreffern — rein rechnerisch — und
`GEGENUEBERSTELLUNG.md`: je Fall die ausgeschlossene Fehllesart neben den
eigenen Befunden, Verdachtsfälle mit `⚑` markiert.

## 5 — Beurteilen

Jetzt darf die Lösung auf. Spawn `lauf-auswerter` mit der Gegenüberstellung.

Er liefert die Überdehnungsrate, die kein Skript bestimmen kann, und Befunde
über die Pipeline selbst. Beachte zwei Blöcke besonders:

- `davon vom Skript übersehen` — steht die Zahl hoch, gehört die
  Verdachtserkennung in `blindlauf.py` nachgeschärft, nicht die Pipeline
- `VOM ÜBERDEHNUNGS-PRÜFER VERPASST` — Fälle, in denen das Gate durchgelassen
  hat, was der Auswerter findet. Das ist der ernsteste Befund überhaupt, denn
  dann ist nicht ein Agent schlecht, sondern das Gate blind

## 6 — Was daraus folgt

Du entscheidest, nicht der Auswerter (P-02). In dieser Reihenfolge:

1. **Gate blind** — der `ueberdehnungs-pruefer` lässt Überdehnungen durch.
   Sein Regelwerk oder seine Beschreibung ändern, dann denselben Lauf erneut
2. **Überdehnung aus einem Agenten** — wenn dieselbe Fehllesart bei mehreren
   Fällen aus demselben Agenten kommt, ist es seine Beschreibung, nicht der Fall
3. **Korridor systematisch verfehlt in einer Fallgruppe** — Leitungsfunktionen,
   Wissenschaft, Probezeit. Dann fehlt Rollenkontext in Schritt 3
4. **Filter zu grob** — `ueberdehnung_verdacht()` in `blindlauf.py`
5. **Erwartungshorizont fragwürdig** — als Befund über den Korpus notieren,
   nicht als Pipelinefehler behandeln (M-04)

Erscheint ein Befund in zwei Läufen hintereinander unverändert, hör auf, ihn
zu reparieren, und sag es. Dann ist er kein Agentenproblem, sondern eines des
Regelwerks oder der Registerschicht.

## Wiederholen

Nach einer Änderung denselben Korpus erneut, unter neuem Lauf-Namen. Die
Vergleichbarkeit hängt daran, dass der Korpus gleich bleibt — und daran, dass
du nicht die Fälle auswählst, bei denen es gut lief.

Läuft nur eine Teilmenge, steht die Zahl im Bericht. `blindlauf.py` zählt
`kein Lauf` getrennt mit, damit 3 von 25 nicht wie 3 von 3 aussehen.

## Zum Schluss

```
LAUF:            <name>
GELAUFEN:        <n> von 25   <bei Teilmenge: welche und warum>
KORRIDOR:        im Korridor <n>, vertretbar abweichend <n>, verfehlt <n>
ÜBERDEHNUNG:     <n> Befunde in <m> Fällen
  vom Skript markiert:   <n>
  vom Skript übersehen:  <n>
  Fehlalarme:            <n>
GATE BLIND BEI:  <fallnummern, in denen der ueberdehnungs-pruefer durchgelassen hat>
WEGGELASSEN:     <Agenten, die nicht gelaufen sind — z. B. form-pruefer>
BEFUNDE PIPELINE: <priorisiert>
BEFUNDE KORPUS:   <Fälle mit fragwürdigem Erwartungshorizont>
NÄCHSTER SCHRITT: <welche Änderung, dann welcher Lauf>
```

Keine Gesamtpunktzahl. Die beiden Zahlen stehen nebeneinander, weil ein
Prüfer, der überall Codes sieht, in der einen besser und in der anderen
schlechter wird.
