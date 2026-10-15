# Offen: die Erstellen-Strecke

Die Prüf-Strecke ist an drei Fällen gelaufen und gehärtet (siehe
`BEFUNDE-ERSTER-LAUF.md`). Die Erstellen-Strecke ist **nie gelaufen**. Zwei
Inventuren haben gezeigt, woran das liegt und was zu tun wäre.

Dieses Dokument ist die Baustelle, nicht die Anleitung. Wer die Strecke
benutzt, bevor sie abgearbeitet ist, bekommt ein Zeugnis mit leeren Achsen —
und zwar aus einem Grund, der nichts mit dem Fall zu tun hat.

---

## Der blockierende Fehler ist klein

Zwei Dateien widersprechen sich:

- `skills/erstellen/SKILL.md:46-48` erlaubt die Note auf undokumentierter
  Grundlage ausdrücklich: „Eine Note, die am Ende nur auf `Q3` ruht, ist nicht
  falsch — aber sie ist nicht belegt."
- `agents/zeugnis-writer.md:31` verbietet sie faktisch: „Keine Karte, keine
  Note" — weil „Grundlage" dort unbestimmt bleibt und der Writer nur zwei
  Ausgänge kennt.

Eine Q3-Karte **ist** eine Karte. Die befürchteten leeren Achsen entstehen aus
diesem Prompt-Konflikt, nicht aus einer Regel. Das ist der erste und
billigste Fix.

---

## Was die Strecke in die falsche Richtung baut

| Befund | Stelle |
| --- | --- |
| `satz-leser` ist auf ein Zeugnis geschrieben, nicht auf Beurteilungsunterlagen; Beispielkarte trägt `"quelle":"zeugnis.pdf"` | `agents/satz-leser.md:3,14,109` |
| `form-pruefer` prüft Briefkopf, Unterschrift, Stempel, Seitenübergänge — an einem Dokument, das noch nicht existiert | `agents/form-pruefer.md:56-60` |
| `ueberdehnungs-pruefer` liest laut Beschreibung `befunde.jsonl`, die beim Erstellen nicht angelegt wird | `agents/ueberdehnungs-pruefer.md:26` |
| Q-Status-Semantik widersprüchlich: Skill definiert `Q1/Q2` als „dokumentiert", der Agent als „Original / OCR" | `skills/erstellen/SKILL.md:41-44` gegen `agents/satz-leser.md:46-50` |
| Niemand schreibt `gesamtnote`. F-03 verlangt sie, das Pflichtformat des Writers hat keine `GESAMTNOTE:`-Zeile, `uebernehmen.py` läuft nur in Schritt 1 | `tools/fertig_definition.py:179-181` gegen `agents/zeugnis-writer.md:73-94` |
| F-03 leitet die Gesamtnote nur aus `themenachse in (leistung, verhalten)` her. Beim Erstellen sind die Karten Beurteilungsgrundlage, oft `engagement` oder `kompetenz` — das Gate meldet dann korrekte Fälle | `tools/fertig_definition.py:184` |
| Die einzige Tabelle in **Schreibrichtung** (`F.2 Ausgangspunkt → Zielwortlaut`) liegt im Schnitt für `schreiben.md`; der `zeugnis-writer` sieht sie nicht | `tools/regelwerk_extrahieren.py` |
| Der Herkunftskopf verweist in allen neun Regelwerk-Dateien auf `docs/REGELWERK.md`; im Arbeitsordner existiert die Datei nicht | `tools/regelwerk_extrahieren.py` |

Maschinell ungeprüft bleiben beim Erstellen A-01, A-02, A-03, A-06 (das
Anspruchsgate läuft nicht und liest ohnehin nur `gegenseite` und `mandant`)
sowie A-05 (F-07 überspringt `zeugnis` ausdrücklich).

---

## Das Fachregelwerk ist Prüfmaterial, nicht Autorenmaterial

Die Formulierungskataloge haben durchgehend die Richtung „gegebene Formel →
Risiko". Zum Schreiben brauchbar sind:

- **`noten.md`** — die Notenstufen-Tabelle über alle fünf Stufen, rückwärts
  direkt benutzbar: Note 2 → „stets zu unserer vollen Zufriedenheit"
- **`form.md`** — alle fünf Zeugnisarten mit Norm und Mindestinhalt, Form,
  Unterschriftsberechtigung, und eine ausführliche Passage zum
  Ausstellungsdatum mit der Warnung, die drei Datumsfelder strikt zu trennen
- **`schluss.md`** — zwei 1:1 verwendbare Schlussformeln und die fünf Bausteine
- **`zeugnis-bauen.md`** — ein vollständiges Musterzeugnis (Note 1) als Gerüst,
  plus die Belegleiter in 21.2.4 und die Vergleichsmaßstab-Fragen in 21.2.3

Es fehlen: Gliederungsvorschrift für ein neues Zeugnis, Volltext-Muster für
Note 2, 3 und 5, Muster für Zwischen- und Ausbildungszeugnis,
Beendigungsgrund-Formulierungen, Aufgabenkatalog-Bausteine je Rolle.

---

## Der stärkste Hebel kostet keine Zeile Code

Die Prüf-Strecke ist der getestete Teil des Kits, und sie liest ein Zeugnis
kalt. Also: nachdem der `zeugnis-writer` den Entwurf geschrieben hat, läuft er
als **neuer, eigener Fall** durch die Prüf-Strecke — `satz-leser` →
`noten-bewerter` → `drift-pruefer` → `schluss-pruefer`, ohne Zugriff auf die
Beurteilungsgrundlage.

Liest sie die beabsichtigte Note heraus und findet keine Drift und keine
unbeabsichtigte Abwertung, ist das echte Evidenz, erzeugt vom geprüften Teil
der Pipeline. Liest sie eine andere Note, ist der Entwurf genau so defekt, wie
er beim nächsten Arbeitgeber defekt wäre.

Das ist für die Erstellen-Strecke dasselbe, was der `gegenanwalt` für die
Prüf-Strecke ist — nur muss nichts gebaut werden.

---

## Reihenfolge

1. **Prompt-Konflikt auflösen.** Der Writer bekommt drei Achsen-Ausgänge statt
   zwei: `benotet` / `bewertungsfrei` / `weggelassen`. Z-04 erlaubt
   `bewertungsfrei` wörtlich („Der Aufgabenteil darf vollständig und konkret
   sein und trotzdem bewertungsfrei"). Das ist das Heilmittel gegen leere
   Achsen und braucht keine neue Beweistheorie. Q-Semantik vereinheitlichen.
2. **Messen, bevor weiter gebaut wird.** Strecke einmal fahren, Block
   `ACHSENENTSCHEIDUNG` lesen. Nennt er drei von vier Achsen als
   `weggelassen`, gibt es ein Grundlagenproblem; nennt er eine, gibt es nichts
   zu reparieren. Nach weiteren Änderungen ist diese Messung nicht mehr
   möglich — dieselbe Disziplin wie M-01, angewandt auf eine
   Designentscheidung.
3. **`grundlagen-leser`** als eigener Agent für Projektabschlüsse, Kennzahlen,
   Lob-Mails und Interviewprotokolle. **Nicht** den `satz-leser` umnutzen: der
   ist der einzige getestete Leser und läuft in beiden Strecken.
4. **`form-pruefer`** und **`ueberdehnungs-pruefer`** bekommen je einen
   Abschnitt für diese Strecke — Art und Norm *vorwärts* bestimmen statt ein
   Dokument prüfen, das es noch nicht gibt; Belegkette als Eingabe statt
   `befunde.jsonl`.
5. **Vorgangs-Intake** in der Skill (P-01, nur sie kann fragen): je Achse
   fragen, an welchem Vorgang die Einschätzung festgemacht ist — was, wann,
   mit welchem Ergebnis. Fragen nicht erfinden, sondern aus
   `zeugnis-bauen.md` 21.2.3 und 21.2.5 nehmen. Protokoll nach
   `faelle/<fall>/unterlagen/` und vom `grundlagen-leser` kartieren, nicht von
   der Skill direkt verarbeiten (P-03, fremder Text).
6. **Zwei Routing-Fehler** im Extraktor beheben (F.2 in `zeugnis-bauen.md`,
   Verweis auf `docs/REGELWERK.md`).
7. **Kette schließen**: `GESAMTNOTE:` und `ABDECKUNG:` in das Pflichtformat
   des Writers, `uebernehmen.py` auch in Schritt 4 aufrufen, F-03 im
   `erstellen`-Zweig auf alle vier Achsen erweitern.
8. **Bindungsvermerk** als dritte Ausgabe: je Note, auf welchem Vorgang sie
   ruht, was dokumentiert ist und was nur Einschätzung. Das Erstellen-Pendant
   zum `mandant.md`/`gegenseite.md`-Paar.
9. **F-09 — interne Steuerung im Zeugnis.** `ausgaben["zeugnis"]` gegen das
   `INTERN`-Dict aus `tools/anspruchsgate.py` prüfen (dafür nach
   `gemeinsam.py` verschieben). Fängt den realistischen Unfall dieser Strecke
   — der Writer lässt „S4, S7" oder eine Ampel im Text stehen.

---

## Eine verworfene Idee, als Warnung

Ein erster Entwurf wollte eine eigene Belegregel für die Arbeitgeberseite
einführen, mit einem Kartenfeld `beurteilungsquelle` und der Begründung, die
Darlegungslast greife erst bei unterdurchschnittlicher Bewertung.

Das war ein Fehlschluss. Darlegungslast ist eine Prozess-Verlustregel, keine
Schreiberlaubnis — was geschrieben werden *darf*, bestimmt die
Zeugniswahrheit, und die liegt davor. Strukturell derselbe Kurzschluss, den
A-02 verbietet, nur aus der Rolle statt aus der Ampelfarbe.

Dazu zwei Gründe, die allgemein gelten:

- Ein Feld, das „kann der Arbeitgeber einen Vorgang benennen" prämiert, belohnt
  eine **sprachliche Fertigkeit**, keine Belegeigenschaft. Der vorgeschaltete
  Interview-Schritt wäre dann eine Maschine, die „sie war gut" in „sie hat die
  Migration X im März verantwortet" umwandelt — Etikett gewechselt, Prüfung
  unverändert null, und das Feld gesetzt von der Partei, die davon profitiert.
- Die Fehlerkosten sind asymmetrisch. Eine **strenge** Regel auf einer
  ungeprüften Rechtsannahme scheitert sichtbar: leere Achsen, jemand sieht es.
  Eine **lockere** scheitert unsichtbar: ein plausibles, unterschriebenes
  Dokument. Die ungeprüfte Annahme gehört auf die strenge Seite.

Wer die Belegschwelle doch staffeln will, soll sie an der **Notenrichtung**
aufhängen und nicht an der Rolle, und das Vokabular aus `zeugnis-bauen.md`
21.2.4 nehmen statt eines erfundenen Enums.
