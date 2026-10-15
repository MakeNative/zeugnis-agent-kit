---
name: erstellen
description: "Fährt die Erstellen-Strecke: Beurteilungsgrundlage ins Register, Note je Achse nur mit Tatsachenkern, Zeugnis schreiben, gegen Katalog und Überdehnung prüfen. Triggers on: /zeugnis-kit:erstellen <fall-id>"
disable-model-invocation: true
argument-hint: "<fall-id>"
---

Du schreibst ein Zeugnis. Die Strecke ist dieselbe Registerschicht wie beim
Prüfen, nur in die andere Richtung: nicht „was steht da und was folgt daraus",
sondern „was ist belegt und was darf daraus geschrieben werden".

Der Unterschied zu einem Textbaustein-Generator ist eine einzige Regel: **jede
Note braucht einen Tatsachenkern** (Z-03). Wer die weglässt, baut schneller
und liefert ein Zeugnis, das im Streitfall nicht zu halten ist.

## 0 — Intake

Les `fall.json`. Setz `ziel: "erstellen"`. Frag nach, was die Bewertung ändert
(P-01):

- Zeugnisart und Anlass: Zwischenzeugnis, Endzeugnis, Ausbildungszeugnis,
  Entwurf
- Personenstatus — Arbeitnehmer, Auszubildender, Organmitglied. Davon hängt
  die Norm ab, und bei einem Geschäftsführer ist sie eine andere
- Führungsverantwortung ja/nein
- Welche Beurteilungsgrundlage liegt vor: Beurteilungsbögen,
  Zielvereinbarungen, Boni, Projektabschlüsse, Vorgesetztenvermerke
- Gibt es ein früheres Zwischenzeugnis? Das bindet in Grenzen
- Gewünschte Gesamttendenz — **und** ob die Grundlage sie trägt

Die letzte Frage ist die unbequeme. Wird eine Note gewünscht, die die Belege
nicht hergeben, sag es jetzt. Später steht sie im Dokument.

## 1 — Beurteilungsgrundlage ins Register

Spawn `satz-leser` über die Beurteilungsunterlagen. Er legt Karten an, wie beim
Prüfen — nur sind die Quellen hier Bögen und Vermerke statt eines Zeugnisses.

Der Quellenstatus trägt hier besonders viel Gewicht:

- `Q1`/`Q2` — in einer Unterlage dokumentiert
- `Q3` — mündliche Einschätzung einer Führungskraft, nicht dokumentiert
- `Q4` — aus der Rolle geschlossen
- `Q5` — gar nichts dazu vorhanden

Eine Note, die am Ende nur auf `Q3` ruht, ist nicht falsch — aber sie ist nicht
belegt, und das muss im Nachweis stehen. `Q4` und `Q5` tragen keine Note
(Z-06).

Der Agent darf nicht schreiben (P-03). Kopier seinen Bericht wortgleich nach
`faelle/<fall-id>/berichte/satz-leser.md` und lass ihn umformen:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/uebernehmen.py" <fall-id> \
  faelle/<fall-id>/berichte/satz-leser.md
```

Nicht von Hand aufbauen. Ein Konflikt oder eine Abbruchwarnung hält den Fall
an, statt ihn mit halben Daten weiterlaufen zu lassen.

## 2 — Form zuerst

Spawn `form-pruefer`. Er bestimmt Zeugnisart, Anspruchsnorm, Mindestinhalt und
die Kopfdaten gegen Vertrag und Lohnabrechnung.

Das steht **vor** der ersten Formulierung. Ein formal defektes Zeugnis wird
durch gute Sätze nicht besser, und der Mindestinhalt entscheidet, welche
Abschnitte überhaupt hineingehören.

Bei einem Ausbildungszeugnis: Verhalten und Leistung nur auf Verlangen. Frag,
ob verlangt wurde.

## 3 — Achsen besetzen

Jetzt entscheidest du, welche Achse welche Note bekommt — mit Satz-IDs:

| Achse | Note | Tragende Karten | Tatsachenkern |
| --- | --- | --- | --- |
| Leistung | | | |
| Verhalten | | | |
| Engagement | | | |
| Kompetenz | | | |

Eine Achse ohne tragende Karte bleibt **leer**. Füll sie nicht mit einer
Durchschnittsformel: eine erfundene Note bindet den Arbeitgeber und ist für
ihn das größere Risiko als eine fehlende.

Aufgabenbeschreibungen bekommen keine Note (Z-04). Der Aufgabenteil darf
vollständig und konkret sein und trotzdem bewertungsfrei.

## 4 — Schreiben

Spawn `zeugnis-writer`. Er liest nur das Register, nie die Rohunterlagen, und
schreibt `schreiben/zeugnis.md` plus die Belegkette daneben.

Beachte seinen Block `OHNE NOTE GEBLIEBEN`. Das sind die Lücken, die er
gemeldet statt gefüllt hat — und die Entscheidung darüber ist deine, nicht
seine.

Und `KATALOGABGLEICH`: dort stehen die Formeln, die stärker oder schwächer
wirken als beabsichtigt. Der häufigste Unfall dieser Strecke ist die
unbeabsichtigte Abwertung. „War stets bemüht" wollte niemand schreiben.

## 5 — Schlussformel

Spawn `schluss-pruefer` über den Entwurf. Er sagt, welche Signalwirkung der
Schluss hat — hier in umgekehrter Richtung nützlich: ob der Schluss kühler
wirkt als die Gesamtnote und damit einen Widerspruch ins Dokument schreibt.

## 6 — Überdehnungs-Gate, umgekehrt

Spawn `ueberdehnungs-pruefer` über die Belegkette. Beim Prüfen fragt er, ob
ein Befund mehr behauptet als das Zeugnis trägt. Hier fragt er, ob eine
**Note** mehr behauptet als die Beurteilungsgrundlage trägt.

Sein Urteil `überdehnt` heißt: Note runter oder Achse leer lassen. Nicht
umformulieren (P-05).

## 7 — Fertig-Definition

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/tools/fertig_definition.py" <fall-id> --ziel erstellen
```

Geprüft werden Pflichtfelder, Herleitung der Gesamtnote aus Einzelkarten,
Kopfdaten in allen Ausgaben, Zuordnung von Zeugnisart und Status.

Das Anspruchsgate läuft hier **nicht** — es prüft Änderungsverlangen, und die
gibt es in dieser Strecke nicht. Gibt es sie doch, weil ein Entwurf
nachverhandelt wird, ist das die Prüf-Strecke.

## Was diese Strecke noch nicht kann

Es gibt keine Ground Truth für „gut geschriebenes Zeugnis". Die 25 Testfälle
des Upstreams sind fertige Zeugnisse, also Prüf-Input. Wer diese Strecke
kalibrieren will, muss rückwärts arbeiten: aus einem Testfall die
Beurteilungsgrundlage ziehen, schreiben lassen, das Ergebnis gegen das
Original stellen. Das ist nicht gebaut — und solange es fehlt, ist jede
Qualitätsaussage über diese Strecke eine Vermutung (P-06).

## Zum Schluss

```
FALL:          <fall-id>  —  <zeugnisart>, <status>
GRUNDLAGE:     <n> Karten — Q1/Q2 <n>, Q3 <n>, Q4/Q5 <n>
ACHSEN:        Leistung <note|leer>, Verhalten <…>, Engagement <…>, Kompetenz <…>
OHNE NOTE:     <welche Achse, und was gefehlt hat>
NUR Q3:        <welche Noten nur auf undokumentierter Einschätzung ruhen>
KATALOG:       <Formeln, die anders wirken als beabsichtigt — und was daraus wurde>
ÜBERDEHNUNG:   <n> Noten überdehnt — <korrigiert wie>
SCHLUSS:       <stimmig zur Gesamtnote | kühler — Widerspruch>
FERTIG:        formal abgeschlossen | offen: <was>
GESCHRIEBEN:   schreiben/zeugnis.md
```
