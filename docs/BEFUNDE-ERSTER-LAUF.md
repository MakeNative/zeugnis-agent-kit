# Befunde des ersten Laufs an echten Fällen

Lauf `2026-10-14-r1`, Stichprobe 3 von 25 Testzeugnissen (01 PTA, 05 ZFA,
09 Altenpflegerin/Wohnbereichsleitung). Gefahren wurde die Prüf-Strecke bis
zum Überdehnungs-Gate; ausgewertet hat der `lauf-auswerter` mit dem Katalog,
den das Gate bewusst nicht hatte.

Dieses Dokument hält fest, was der Lauf **über die Pipeline** gezeigt hat.
Behobene Punkte sind als behoben markiert; der Rest ist offen.

---

## Was gehalten hat

- **Registerschicht.** 103 Satzkarten über drei Fälle, kein einziger
  F-01-Befund. Pflichtfelder, Vokabular und Z-04 (keine Note auf Aufgaben-
  und Formsätzen) überall eingehalten.
- **Fundstellen nicht erfunden.** 14 von 14 zitierten Entscheidungen und
  Normen existieren im extrahierten Regelwerk; alle als `ungeprueft`
  markiert, wie A-05 es verlangt.
- **Das Überdehnungs-Gate hat gegriffen.** 1 von 24 Befunden überdehnt, und
  zwar ein echter: der `noten-bewerter` las aus „im Wesentlichen
  ordnungsgemäß" eine Ausnahme *wesentlicher* Arbeitsteile, während der
  Wortlaut den *unwesentlichen* Rest vorbehält — eine Umkehrung mit
  Verschärfung. Gefunden von einer Instanz ohne Gedächtnis und ohne
  Schreibrechte, die nichts zu verteidigen hatte.
- **Guardrails eingehalten.** Alle Ausschlussregeln der drei Fälle wurden
  getroffen und ausdrücklich abgelehnt, nicht übersehen — Gesundheitswunsch
  ≠ Krankheitscode, neutrales Enddatum ≠ Kündigungscode, warme Schlussformel
  ≠ Anspruch, Geselligkeit ≠ Alkoholbehauptung.

---

## Behoben

**B1 — Die Messung las die falsche Datei.** `blindlauf.py` bewertete die
handgeschriebene Prosa-Laufdatei, während die echten Befunde mit Gate-Stufe,
Konfidenz und Gate-Urteil in `befunde.jsonl` stehen. Vier belegte Verluste,
alle in Richtung „sieht wie Überdehnung aus": eine vom Gate erzwungene
Korrektur fehlte, eine entfernte Absolutheit war wiederhergestellt, eine am
Dokument verankerte Belastungsaussage las wie eine Branchenprämisse, eine
eingehaltene Ausschlussregel war halbiert. **Der erste Durchgang hat damit
die unkorrigierte Pipeline gemessen.** Jetzt liest `befunde_aus_akte()` die
Akte, die Laufdatei ist nur noch Fallback.

**B2 — Gate-4-Absagen wurden als Behauptungen gezählt.** 7 von 24 Befunden
stehen auf Stufe 4 „nicht aufnehmen", und alle 7 sind Absagen an eine
Fehllesart. Sie gegen den Negativkatalog zu prüfen verwechselt Einhaltung mit
Bruch — das erzeugte 3 Fehlalarme bei 3 Markierungen. Jetzt getrennt
ausgewiesen als Einhaltung.

**B3 — Der Verdachtsfilter war antikorreliert zu dem, was er findet.** Drei
Ursachen: „keinen" überlebte die Stammkürzung, so dass der Filter auf die
Wörter feuerte, die eine Ablehnung beweisen; keine Umlaut-Normalisierung, so
dass „Kuendigungscode" (Agent) und „Kündigungscode" (Matrix) nie trafen; der
Zitat-Pfad feuerte vor der Negationsprüfung. Neu modelliert: entscheidend ist,
ob der **verbotene Begriff negiert** ist. 19 Testfälle, alle bestanden.

**B4 — Gemessen wurde gegen die schwächere von zwei Ground Truths.** Die
`TESTFALL-MATRIX.md` nennt sich „die kompakte Ground Truth" und ist genau das:
verlustbehaftet. Die Erwartungshorizonte tragen zwei bis drei Ausschlussregeln
je Fall. In zwei von drei Fällen fehlte in der Matrix genau die Regel, an die
der Lauf gerührt hat — in 05 die schärfste („Geselligkeit nicht als
Alkoholbehauptung"). Jetzt werden beide gelesen, die Herkunft wird ausgewiesen.

**B5 — `noten_menge()` las Regelcodes als Noten.** Aus
`"keine (Z-04, Aufgabensatz)"` wurde die Note 4 — das Gate meldete also den
Agenten, der die Regel befolgt. 16 Testfälle.

**B6 — Eine Gate-Regel war nicht maschinell entscheidbar.** Die Z-04-Prüfung
im Anspruchsgate lag in beide Richtungen falsch: ein Formmangel ruht
naturgemäß allein auf einem Formsatz, und ein Auslassungsbefund zitiert die
Aufgabenliste als Beleg der Erwartbarkeit. Entfernt — die Wertung gehört nach
P-04 zum Prüfer.

**B7 — Der Scorer bestrafte ehrliche Spannen.** Reine Teilmengenprüfung
machte aus „2 bis 3, Schwerpunkt 2" gegen Korridor 2 einen Teiltreffer. Wer
dafür abgestuft wird, lernt Punktnoten zu behaupten, die er nicht hat.
Schwerpunkt-Konvention ergänzt, kenntlich gemacht.

**B8 — Kein Automatismus von `überdehnt` zur Gate-Stufe.** Die improvisierte
Zuordnung 1→2 war falsch: Stufe 2 heißt „Tatsachengrundlage offen", und offen
war nichts. Jetzt A-07.

**B9 — Zweideutige Q-Status-Regel im `satz-leser`.** Bei identischer Lage —
Platzhalter-Stempelfeld, leere Unterschriftslinie — setzte Fall 01 `Q1` und
Fall 09 `Q5`. Beides war von der Beschreibung gedeckt. Jetzt getrennt: der
sichtbare Zustand ist `Q1`, die offene Ausfertigungsfrage gehört in den
`hinweis`. Wer den leeren Strich auf `Q5` setzt, legt nach Z-06 den stärksten
Formbefund des Falls still.

---

## Offen

**O1 — M-01 ist auf Orchestrierungsebene gebrochen.** Die Agenten waren blind,
die Extraktion war sauber (`--ohne-katalog`, 0 Treffer auf „Sollkorridor").
Der Orchestrator kannte die Sollkorridore — und hat die Stichprobe gezogen.
Gezogen wurden drei Fälle mit einwertigem Korridor und in sich konsistentem
Dokument; ungezogen blieb jeder Fall, den die Matrix selbst als schwer
markiert (07 „3 bis 4", 14 „2 mit Bereichsdrift", 15 „4 bis 5 / lückenhaft",
16 Statusfrage, 25 „3 mit Führungsdrift"). **3 von 3 darf deshalb nicht als
blinde Messung der Pipeline berichtet werden.** Ein belastbarer Lauf braucht
einen Orchestrator, der die Lösung nicht kennt.

**O2 — Die Stichprobe trug fast keinen scharfen Köder.** In 01 und 09 nennt
das Dokument den Beendigungsgrund selbst; nur 05 hat ein nacktes Enddatum.
Die Fälle, die das Gate wirklich fordern würden (03 „hat sich in das Team
integriert", 04, 08, 10, 12, 17, 18), liefen nicht. Der Recall des
`ueberdehnungs-pruefer` ist bei 0 echten Überdehnungen in 3 Fällen **nicht
messbar**.

**O3 — Kein `quelle`-Feld je Befund.** Die Entscheidungsregel der Skill
`blindlauf` Schritt 6.2 — „wenn dieselbe Fehllesart bei mehreren Fällen aus
demselben Agenten kommt, ist es seine Beschreibung" — ist aus der Laufakte
nicht ausführbar. Zur Frage, ob eine Überdehnung aus dem `noten-bewerter`
oder erst aus dem `drift-pruefer` kommt, lässt sich nichts sagen.

**O4 — A-02 ist durch das Schema unerreichbar.** `befunde.jsonl` hat kein
Ampelfeld, also kann die Regel „Beweislast nicht aus der Ampel" nicht
verletzt und damit auch nicht geprüft werden. Geprüft wird derzeit nur der
Begründungstext.

**O5 — A-01-Stufenmischung und A-03 sind ungetestet.** Es entstand kein
Schreiben; `gates/anspruchsgate.md` meldet „Geprüfte Schreiben: 0 — Ohne
Befund". Ein Gate, das mit leerer Eingabe grün durchläuft, und daneben
`gates/fertig.md` „Alle maschinell prüfbaren Bedingungen erfüllt" bei 22
nicht gelaufenen Fällen: beide Dateien caveaten sich selbst, nebeneinander im
Ordner liest sich das als vollständiger Lauf.

**O6 — Der Unterschrifts-/Stempelbefund ist ein Fixture-Artefakt.** Er tritt
in 3 von 3 Fällen auf, weil der Korpus den Stempel als Textfeld und die
Unterschrift als Unterstrichzeile rendert. Kein Zeugnis dieses Korpus kann je
unterschrieben sein; der Befund ist in allen 25 Fällen garantiert und wird
jede Befundstatistik dominieren. In Fall 01 ist er der einzige Punkt über
Gate 4 — ohne ihn erzeugte 01 null Handlungspunkte, genau wie der
Erwartungshorizont es verlangt. Der zuständige `form-pruefer` lief nicht.

**O7 — `--ohne-katalog` widerspricht der Beschreibung des
`ueberdehnungs-pruefer`.** Sie verspricht ihm den Katalog der 25 Fälle, und
sein Pflichtformat hat ein `KATALOG:`-Feld, das unter dem Flag nur „keine"
lauten kann. Entweder eine modusabhängige Variante oder der Katalog wird in
der Beschreibung als optional markiert.

**O8 — Reststreufehler des Filters.** Ein Befund bleibt markiert, weil
„gesetztes Textfeld" bei Sechs-Zeichen-Stämmen mit „gesetzlichen Anspruch"
kollidiert. Das ist die bekannte Grenze der Stammkürzung. Ein Fehlalarm
kostet einen Blick; eine feinere Normalisierung wäre die nächste Stufe.

---

## Befund über den Prüfkorpus

**Fall 09: der Erwartungshorizont übersieht die Führungslücke.** Das Dokument
weist „fachliche und disziplinarische Führung von vierzehn Pflegekräften" als
Kernfunktion aus, sechzehn Jahre lang, zweiunddreißig Bewohner — und der
gesamte Beurteilungsteil beurteilt die Mitarbeiterführung nicht; die
Verhaltensformel nennt Heimleitung und Bewohner, nicht die Unterstellten. Der
Erwartungshorizont kennt als einzige Einschränkung „eine begrenzte
Dokumentationsschwäche" und erwartet, ohne Tatsachenfehler keinen Streit zu
erzeugen. Derselbe Korpus modelliert genau diesen Defekt anderswo ausdrücklich
als Sollbefund (14 Bereichsdrift, 25 Führungsdrift, 08 inhaltsarme
Führungsaussage, 23 negatives Führungsbild).

Die Pipeline hat in 09 den konsequenzreichsten Punkt des Dokuments gefunden,
und die Ground Truth honoriert ihn nicht und verbietet ihn nicht. Das ist ein
Befund über den Korpus, nicht über die Pipeline (M-04).

---

# Nachtrag: die Schreiben-Strecke (O5 erledigt)

Gefahren auf Fall 05 (4/4/2/2 über die Gate-Stufen) und Fall 09 (1/2/3/2 —
ein tragender Rechtsmangel, drei Bitten). Der zweite Fall war der schärfere
Test: ein Brief, der überwiegend aus freiwilligen Punkten besteht, ist genau
die Lage, in der die Versuchung am größten ist, einem Wunsch Nachdruck zu
verleihen.

## Der Writer war beide Male sauber

Keine Stufenmischung, kein Stufe-4-Befund im Text, keine interne Steuerung im
Klartext, Befund-Marker durchgehend gesetzt. Beide Male hat er die Frist in
einen eigenen Abschnitt gelegt und **ausdrücklich auf den Berichtigungsteil
begrenzt** — in Fall 09 trägt der Fristabsatz sogar den Marker des tragenden
Befunds, damit maschinell prüfbar ist, dass die Frist nicht auf einer Bitte
sitzt. Das stand so in keiner Anweisung.

In beiden Mandantenbriefen steht der Pflichtteil, den ich für den
wahrscheinlichsten Ausfall gehalten hätte: was der Mandant **nicht** bekommt,
samt dem Satz, dass der Arbeitgeber nein sagen darf.

## Die Gates waren es nicht

Neun Fehlalarme über zwei Läufe, null echte Befunde. Alle behoben; das Muster
ist einheitlich und lehrreich: **die Gates waren gegen die Prosa gebaut, die
ich mir vorgestellt hatte, nicht gegen die, die ein Jurist schreibt.**

| Prüfung | Fehler | Ursache |
| --- | --- | --- |
| A-03 `FREIWILLIG` | 4 Fehlalarme | Flexion („freiwillige"), Einschub („kein *einklagbarer* Anspruch"), Wortstellung („können wir nur bitten") |
| F-07 `MARKER_UNGEPRUEFT` | 3 Fehlalarme | suchte „ungeprüft", der Writer schrieb „noch nicht geprüft"; und das ±400-Zeichen-Fenster erreicht keinen Vorbehalt am Dokumentfuß |
| F-04 Kopfdaten | 5 Fehlalarme | keine Normalisierung der Leerzeichen (umbrochener Satz), Mandantenbrief zur Vollständigkeit verpflichtet, Freitextfeld wörtlich verglichen |

Das dritte F-04-Problem ist das interessanteste: `position` war
`"examinierte Altenpflegerin, seit 2010 Wohnbereichsleitung"` — ein String,
den die Skill selbst zusammengesetzt hatte. Der Brief schrieb „seit 2010
**als** Wohnbereichsleitung". Das Gate prüfte gegen das eigene Phrasing statt
gegen das Dokument. Atomare Felder (Name, Daten, Arbeitgeber) werden jetzt
streng verglichen, Freitextfelder über Kernwörter.

## Und ein echtes Loch, gefunden durch gezielten Gegentest

Nach dem Weiten der Regex habe ich einen Loch-Test gebaut, statt auf den
nächsten Lauf zu warten. Er fand sofort, was A-03 eigentlich schließen soll:

> „Wir bitten um eine Aussage zur Belastbarkeit … Eine Weigerung würden wir
> als Verstoss gegen Ihre Pflichten bewerten."

Eine freiwillige Bitte, als Pflichtverletzung verkleidet — durchgelaufen, weil
`HART` nur Verbformen kannte („verstößt"), nicht die Substantivform „Verstoß
gegen … Pflichten", und weil das Wort „Frist" fehlte. Jetzt geschlossen, mit
12 HART- und 10 FREIWILLIG-Testfällen abgesichert, darunter acht Negativfälle.

Der wichtigste Negativfall: **„ohne Anerkennung einer Rechtspflicht"** nennt
eine Pflicht, behauptet aber keine. Das darf kein Treffer sein — sonst meldet
das Gate genau den Writer, der sauber arbeitet.

## Absicherung gegen Blindheit

Regex zu weiten, bis es grün ist, ist der naheliegende Fehler. Vier
Gegenbeispiel-Fixtures laufen deshalb mit:

| Eingebauter Verstoß | gefangen |
| --- | --- |
| Stufe-2-Befund als „Pflichtverletzung" | ja |
| Stufe-4-Befund im Schreiben | ja |
| Bitte neben Frist und Klageandrohung | ja |
| Bitte als „Verstoß gegen Ihre Pflichten" | ja |
| Satz-ID, Ampel, Konfidenz, Prio im Klartext | ja, alle vier |
| Beschäftigungsbeginn verfälscht | ja |
| Frische-Kennzeichnung entfernt | ja |
| **alle** Vorbehalte entfernt (Test des globalen Pfads) | ja |

Der dokumentweite Vorbehalt verlangt einen echten Marker **plus**
Dokumentbezug; „Entwurf, nicht versandfertig" allein genügt nicht.

## Was damit erledigt ist und was nicht

**Erledigt:** O5. A-01-Stufenmischung, A-03 und A-06 sind an echtem Output
geprüft, nicht mehr nur an einer künstlichen Fixture.

**Nicht erledigt:** O1 bis O4, O6 bis O8 stehen unverändert. Der Writer ist
jetzt n=2 — besser als n=1, immer noch keine Aussage über 25 Fälle.
