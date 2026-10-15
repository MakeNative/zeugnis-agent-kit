---
name: pruefen
description: "Fährt die Prüf-Strecke über einen Fall: Register, Notenmatrix, Drift, Form, Schluss, Anspruchsgate, Schreiben, Überdehnungs-Gate, Fertig-Definition. Triggers on: /zeugnis-kit:pruefen <fall-id> [...]"
disable-model-invocation: true
argument-hint: "<fall-id> [fall-id ...]"
---

Du prüfst ein vorliegendes Zeugnis und entscheidest, was daraus folgt. Die
Agentenberichte sind Material, keine Ergebnisse (P-02) — du schreibst Register
und Befunde, nicht sie.

## 0 — Intake

Les `faelle/<fall-id>/fall.json`. Fehlt etwas, das die **Bewertung** ändert,
frag jetzt — ein Subagent kann es nicht (P-01):

- Rolle und Ziel: nur verstehen, verhandeln, anschreiben, Klage prüfen
- Führungsverantwortung ja/nein — entscheidet, ob eine schwache
  Führungsaussage tragend oder bedeutungslos ist
- Vergleichsmaterial: Vorzeugnis, Zwischenzeugnis, Zielvereinbarungen, Boni,
  Beurteilungsbögen, Lob-Mails
- Abreden: Aufhebungsvertrag, Vergleich, Erledigungsklausel, Zeugnisverzicht
  — und **wann** erklärt
- Fristen: steht eine im Raum, ist schon eine Berichtigungsbitte raus

Frag nach dem, was die Bewertung verschiebt, nicht nach allem. Die übrigen
Lücken laufen als Annahme mit, sichtbar in `fall.json`.

## 1 — Register

Spawn `satz-leser`, **einen je Zeugnis**. Mehrere Zeugnisse derselben Person
bekommen getrennte Fall-IDs und getrennte Register; ein Vergleich entsteht erst
danach.

Er darf nicht schreiben (P-03). Die Übernahme läuft deshalb in zwei Schritten,
und keiner davon ist Abtippen:

```bash
# 1. Bericht wortgleich kopieren — eine Kopie, keine Umformung
#    (Write-Tool, Inhalt unverändert aus dem Agentenbericht)
#    → faelle/<fall-id>/berichte/satz-leser.md

# 2. Umformen lassen
python3 "${CLAUDE_PLUGIN_ROOT}/tools/uebernehmen.py" <fall-id> \
  faelle/<fall-id>/berichte/satz-leser.md
```

Bau `register.jsonl` **nicht** von Hand. Das war bis zum ersten echten Lauf so
vorgesehen und hat sich als zweifach falsch erwiesen: hundert Karten je Fall
tippt niemand ab, und wer eine Note beim Übertragen in der Hand hält, kann sie
anfassen. Das Skript kann nicht urteilen — das ist sein Wert.

Meldet `uebernehmen.py` einen **Konflikt**, ist der Fall angehalten: zwei
Berichte zitieren denselben Satz verschieden. Einer hat abgetippt statt
kopiert, oder die Satz-IDs sind verschoben. Kläre das am Dokument.

Warnt es über eine abgeschnittene JSON-Zeile, ist der Bericht abgebrochen —
Agent einmal neu starten (P-07), nicht weiterarbeiten.

Meldet der Agent eine fehlende Hauptformel, ist das schon ein tragender Befund.
Notier ihn, bevor du weitergehst.

## 2 — Bewerten, parallel

Spawn gleichzeitig:

- `noten-bewerter` — satzweise Notentendenz, Ampel, Rechtsstatus
- `form-pruefer` — Zeugnisart, Kopfdaten, Formalia
- `schluss-pruefer` — Signalwirkung, Anspruchslage, Abreden

Die drei brauchen einander nicht. Der `drift-pruefer` dagegen schon: er
vergleicht bewertete Sätze, also läuft er **nach** dem `noten-bewerter`.

Führ die Ergänzungen des `noten-bewerter` genauso zusammen — Bericht kopieren,
dann `uebernehmen.py`. Es ergänzt die bestehenden Karten um Notenspanne, Ampel,
Rechtsstatus und Konfidenz und übernimmt `GESAMTNOTE` samt `GETRAGEN VON` in
`fall.json`.

Der `form-pruefer` liefert oft den stärksten Punkt des Falls — ein falscher
Beschäftigungszeitraum ist ein Anspruch ohne Auslegungsfrage. Behandle seine
Befunde nicht als Formalie.

Meldet der `schluss-pruefer` eine Abrede, hör hier auf und kläre sie. Ein
Schreiben über einen abgegoltenen Anspruch ist schlimmer als keins.

## 3 — Drift

Spawn `drift-pruefer`. Meldet er einen Widerspruch zwischen Hauptnote und
Schlussformel, spring zurück zu Schritt 2 und lass den `noten-bewerter` die
betroffenen Sätze neu einordnen. Das ist der einzige erlaubte Rücksprung.

## 4 — Befunde bilden

Jetzt entscheidest du, nicht die Agenten. Je Streitpunkt eine Zeile in
`befunde.jsonl`:

```json
{"befund_id":"B-01","satz_ids":["S4"],"prio":"A","gate_stufe":1,
 "begruendung":"","zieltext":"","konfidenz":"hoch",
 "rechtsstatus":"korrekturanspruch-plausibel","norm":"","frische":"ungeprueft"}
```

Die Gate-Stufe ist dein Urteil, nicht das des Bewerters:

1. Rechtsmangel plausibel
2. Tatsachengrundlage offen
3. nur freiwillige Verbesserung
4. kein tragfähiger Punkt — kommt nicht ins Schreiben

Zwei Regeln, bei denen die meisten Fälle kippen: Eine Ampelfarbe ist kein
Anspruch und keine Beweislast (A-02). Und ein Befund mit `konfidenz: niedrig`
ist Stufe 2, nicht Stufe 1 — er wird belegt, nicht behauptet (Z-05).

## 5 — Frische

Für jede Norm und jede Entscheidung, die in ein Schreiben soll: gegen die
Primärquelle prüfen (A-05). `regelwerk/rechtsprechung.md` ist eine Suchadresse,
kein Beleg. Setz danach `frische` auf `geprueft` und trag die Fundstelle im
Wortlaut ein, oder lass sie draußen.

Eine richtige Entscheidung für eine falsche Aussage zu zitieren fällt erst vor
Gericht auf. Deshalb steht dieser Schritt vor dem Schreiben, nicht danach.

## 6 — Anspruchsgate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/anspruchsgate.py" <fall-id>
```

Befunde hier sind kein Stilhinweis — sie sagen, dass ein Schritt übersprungen
wurde. Arbeite sie ab, bevor geschrieben wird. Ein Gate nach dem Schreiben
findet dieselben Fehler teurer.

## 7 — Schreiben

Spawn `schreiben-writer`. Er schreibt `schreiben/mandant.md` und
`schreiben/gegenseite.md` mit Befund-Marker je Absatz.

Dann das Gate erneut — jetzt prüft es auch die Texte: Stufe-4-Befunde im
Schreiben, Bitten neben Fristen, Satz-IDs und Ampeln im Klartext.

## 8 — Überdehnungs-Gate

Spawn `ueberdehnungs-pruefer`. Er bekommt die Befunde und sein Regelwerk, und
sonst nichts.

Sein Urteil `überdehnt` heißt: Gate-Stufe runter oder Befund raus. Nicht
umformulieren — die Behauptung ist das Problem, nicht ihr Ton (P-05).

Beachte `SCHÄRFSTER BEFUND`. Das ist der eine, der dem Fall am meisten
schadet, und er steht oft nicht an erster Stelle der Liste.

Räumt er einen Befund ab, der deiner Einschätzung nach trägt, entscheidest du
— aber begründe es am Wortlaut, nicht am Gefühl. Er hat nichts zu verteidigen,
du schon.

## 8b — Gegenanwalt

Spawn `gegenanwalt` über `schreiben/gegenseite.md` und das Zeugnis. Er bekommt
**nicht** das Register, nicht die Befunde, nicht den Mandantenbrief — sonst
liest er wohlwollender als der echte Empfänger und misst nichts.

Er ist die einzige Instanz, die sagt, ob der Brief **wirkt**. Die Gates prüfen
nur, ob er formal in Ordnung ist.

Drei Blöcke seines Berichts entscheiden:

- `WAS MICH AM MEISTEN KOSTET` — der Punkt, der tatsächlich sitzt. Der gehört
  nach vorn, falls er das nicht schon ist.
- `SCHWÄCHSTE STELLE` — die eine Stelle, die er zuerst angreift. Nimmt sie den
  Rest in der Glaubwürdigkeit mit, ist sie entweder zu entschärfen oder zu
  streichen, auch wenn jedes Gate sie durchlässt.
- `WIRKUNG INSGESAMT` — „zu weich" ist ein genauso ernster Befund wie
  „überzogen". Ein Brief, der die Gegenseite kaltlässt, hat sein Ziel verfehlt.

Sein Block `NICHT ANGEGRIFFEN` geht zurück an Schritt 4: er nennt, was im
Zeugnis angreifbar war und im Brief fehlt.

Was du mit seinem Urteil **nicht** machst: den Brief weichspülen, bis er
niemanden provoziert. Er ist die Gegenseite, nicht der Maßstab — ein Punkt,
den er „bestreitet", kann trotzdem richtig sein. Entscheiden tust du (P-02).

## 9 — Fertig-Definition

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/fertig_definition.py" <fall-id>
```

Läuft es ohne Befund, ist der Fall **formal** abgeschlossen. Das ist nicht
dasselbe wie geprüft: ob ein Zieltext wahr und taktisch sinnvoll ist, sieht
kein Skript.

Les deshalb zum Schluss selbst gegen: trägt jeder Absatz des
Gegenseitenschreibens genau so viel, wie die Karte darunter hergibt?

## Wenn ein Agent stirbt

Ein Agent ohne vollständigen Bericht zählt nie als „nichts gefunden" (P-07).
Prüf jeden Bericht auf seine Pflichtblöcke — ein abgebrochener Bericht sieht
oft brauchbar aus, das ist die Gefahr. Starte einmal neu mit dem Hinweis, knapp
zu bleiben. Beim zweiten Fehlschlag meld den Auftrag als unerledigt, mit
Fall-ID.

## Priorisieren

Nicht alles gleich wichtig behandeln. In dieser Reihenfolge:

1. **Abrede gefunden** — kann den ganzen Fall erledigen
2. **Status oder Zeugnisart falsch zugeordnet** — trägt Norm, Rechtsweg, Kosten
3. **Überdehnung in einem Stufe-1-Befund** — eine unbelegte Behauptung mit
   Anspruchsgeste ist schlimmer als ein fehlender Punkt
4. **Formmangel und falsche Kopfdaten** — stärkste Punkte, kein Streit
5. **Hauptnote ohne Herleitung aus Karten** (Z-03)
6. **Widerspruch Hauptnote/Schlussformel**
7. **Drift und Auslassung mit Rollenbezug**
8. **freiwillige Wünsche** — zuletzt, als Bitte

## Zum Schluss

```
FALL:            <fall-id>  —  <zeugnisart>, <status>, Ziel <ziel>
REGISTER:        <n> Sätze — Q1 <n>, Q2 <n>, Q3 <n>, Q4 <n>, Q5 <n>
GESAMTNOTE:      <spanne>  getragen von <satz-ids>
BEFUNDE:         <n> — Stufe 1: <n>, Stufe 2: <n>, Stufe 3: <n>, Stufe 4: <n>
ANSPRUCHSGATE:   <n> Befunde — <m> behoben
ÜBERDEHNUNG:     <n> von <m> Befunden überdehnt — <behoben wie>
FRISCHE:         <n> Fundstellen geprüft, <m> als ungeprüft gekennzeichnet
FERTIG:          formal abgeschlossen | offen: <was>
ABDECKUNG:       <vollständig | welcher Teil nicht>
NÄCHSTER SCHRITT: <…>
```
