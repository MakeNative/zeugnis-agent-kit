# zeugnis-kit

Agenten-Pipeline für Arbeitszeugnisse, in beiden Richtungen: ein vorliegendes
Zeugnis prüfen oder ein neues schreiben. Beide Strecken stehen auf derselben
Registerschicht.

Das Fachwissen kommt aus
[`arbeitszeugnispruefer-skill`](https://github.com/Klotzkette/arbeitszeugnispruefer-skill)
(Apache-2.0 OR MIT) und wird skriptbasiert extrahiert, nicht mitgeliefert.
Siehe `NOTICE`.

## Warum das Kit existiert

Der Upstream ist ein sehr guter Prompt: 3.193 Zeilen, Notenstufen,
Formulierungskatalog, Ampel-Flaggen, Normen, Entscheidungen, und — das
Wertvollste — fertige Artefakt-Schemata für Quellenstatus, Satzregister,
Anspruchsgate und eine Fertig-Definition.

Alles davon steht dort als **Anweisung an ein Modell, sich selbst zu
disziplinieren**. Die Einschätzungsmatrix soll kein Modell erfinden, das
Gegenseitenschreiben soll nicht mehr behaupten als die Matrix, die Ampel soll
keine Beweislast begründen. Genau das hält ein einzelner Durchlauf nicht ein,
und niemand merkt es.

Hier macht das jeweils eine andere Instanz: zwei Skripte prüfen, was prüfbar
ist, und ein Agent ohne Gedächtnis und ohne Schreibrechte sucht nach
erfundenen Geheimcodes.

## Strecken

```
                 satz-leser          Karten: Wortlaut, Seite, Q1–Q5, Typ, Achse
                     │
      ┌──────────────┴──────────────┐
   PRÜFEN                        ERSTELLEN
                                 │
   noten-bewerter                form-pruefer      Art, Norm, Mindestinhalt
   form-pruefer                  │
   schluss-pruefer               Achsen besetzen   Note nur mit Tatsachenkern
   drift-pruefer                 │
      │                          zeugnis-writer
   Befunde + Gate-Stufe 1–4      │
      │                          schluss-pruefer
   ▸ anspruchsgate.py            │
      │                          ▸ ueberdehnungs-pruefer   Note > Grundlage?
   schreiben-writer              │
      │                          ▸ fertig_definition.py
   ▸ anspruchsgate.py  (Texte)
      │
   ▸ ueberdehnungs-pruefer       Befund > Wortlaut?
      │
   ▸ fertig_definition.py
```

## Die zwei Gates

**`anspruchsgate.py`** — jeder verlangte Änderungsbaustein trägt eine Stufe:
1 Rechtsmangel plausibel, 2 Tatsachengrundlage offen, 3 nur freiwillig,
4 kein tragfähiger Punkt. Stufe 4 darf in keinem Schreiben stehen, Stufe 3
nicht neben einer Frist, Stufe 2 nicht neben einer Pflichtverletzung. Dazu:
Beweislast nicht aus der Ampelfarbe, kein Rechtsmangel auf Q4/Q5, keine
Satz-IDs und Ampeln im Klartext.

**`fertig_definition.py`** — der Fall als Ganzes: Pflichtfelder, Gesamtnote aus
Einzelkarten hergeleitet, Kopfdaten in allen Ausgaben identisch, Zeugnisart
und Personenstatus vereinbar, jede Fundstelle als geprüft oder ungeprüft
markiert, Abdeckung ausdrücklich erklärt.

Was beide nicht prüfen: ob ein Zieltext wahr und taktisch sinnvoll ist.

## Messung

`blindlauf.py` fährt die 25 Testzeugnisse des Upstreams und liefert zwei
Zahlen, die getrennt bleiben:

- **Korridortreffer** — liegt die Gesamtnote im Sollkorridor (rechnerisch)
- **Überdehnungsrate** — wie oft wurde ein Befund erfunden, den die Spalte
  `Nicht überdehnen` ausschließt (vom `lauf-auswerter` beurteilt)

Keine Gesamtpunktzahl: ein Prüfer, der überall Codes sieht, trifft mehr
Korridore und überdehnt mehr. Eine Summe würde das verstecken.

Vor einem Blindlauf muss das Regelwerk mit `--ohne-katalog` neu extrahiert
werden. Der Negativkatalog in `ueberdehnung.md` ist nach Rollen sortiert und
wäre sonst der Lösungsschlüssel zu dem Fall, den der Prüfer gerade beurteilt.
Er gehört beim Messen zum `lauf-auswerter`, nicht zum Prüfer.

## Was das Kit nicht leistet

**Keine Rechtsberatung und keine Rechtsstandsgarantie.** Normzitate und
Entscheidungen aus dem extrahierten Regelwerk sind Suchadressen. Jede
Fundstelle, die in ein Schreiben geht, wird vorher gegen die Primärquelle
geprüft (A-05).

**Keine kalibrierte Erstellen-Strecke.** Die 25 Testfälle sind fertige
Zeugnisse, also Prüf-Input. Für „gut geschriebenes Zeugnis" gibt es keine
Ground Truth, und bis es eine gibt, ist jede Qualitätsaussage über diese
Strecke eine Vermutung.

**Keine juristische Ground Truth.** Die Testakten sind laut Upstream
KI-generierte Fiktion; der Erwartungshorizont ist Autorenbehauptung. Er
kalibriert Konsistenz, nicht Richtigkeit (M-04).

## Einrichten

```
/zeugnis-kit:adopt [pfad]
```

Legt den Arbeitsordner an, klont den Upstream nach `upstream/` und extrahiert
`regelwerk/`. Beide Verzeichnisse sind gitignoriert — abgeleitet, kein
Quellstand.

## Skills

| Skill | Zweck |
| --- | --- |
| `/zeugnis-kit:adopt` | Arbeitsordner, Upstream, Regelwerk-Extraktion |
| `/zeugnis-kit:pruefen <fall-id>` | Prüf-Strecke bis zu beiden Schreiben |
| `/zeugnis-kit:erstellen <fall-id>` | Erstellen-Strecke bis zum Zeugnis |
| `/zeugnis-kit:blindlauf <name>` | Messung über die 25 Testfälle |

## Werkzeuge

| Werkzeug | Zweck |
| --- | --- |
| `regelwerk_extrahieren.py` | Fachregelwerk aus dem Upstream schneiden, wiederholbar |
| `uebernehmen.py` | Agentenbericht wortgleich in die Fallakte übernehmen |
| `anspruchsgate.py` | Gate-Stufen, Beweislast, interne Steuerung in Schreiben |
| `fertig_definition.py` | Pflichtfelder, Notenherleitung, Normzuordnung |
| `blindlauf.py` | Korridortreffer rechnen, Gegenüberstellung für die Beurteilung |

Agenten haben keine Schreibrechte (P-03). Die Skill kopiert ihren Bericht
wortgleich nach `faelle/<fall>/berichte/`, und `uebernehmen.py` formt ihn um.
Register und Befunde werden **nie** von Hand aufgebaut: wer eine Note beim
Übertragen in der Hand hält, kann sie anfassen, und bei hundert Karten je Fall
tippt sie ohnehin niemand ab.

Beide Gates nennen in ihrem Bericht, wie viele Fälle sie angesehen haben und
was sie nicht abdecken. Ein Gate, das „ohne Befund" meldet, ohne seinen Umfang
zu nennen, ist gefährlicher als keins.

## Agenten

| Agent | Rolle | Schreibrechte |
| --- | --- | --- |
| `satz-leser` | Zeugnis in Karten zerlegen, Quellenstatus setzen | nein |
| `noten-bewerter` | Notentendenz, Ampel, Rechtsstatus je Satz | nein |
| `drift-pruefer` | Schaufenster-/Bereichs-Drift, Auslassung, Widerspruch | nein |
| `form-pruefer` | Zeugnisart, Norm, Kopfdaten, Formalia | nein |
| `schluss-pruefer` | Signalwirkung, Anspruchslage, Abreden | nein |
| `zeugnis-writer` | Zeugnis aus dem Register schreiben | ja |
| `schreiben-writer` | Mandanten- und Gegenseitenschreiben | ja |
| `ueberdehnungs-pruefer` | erfundene Codes, Ampel-Beweislast, Wunsch als Anspruch | nein |
| `gegenanwalt` | liest das Schreiben als Empfänger: wo greift er an, was sitzt | nein |
| `lauf-auswerter` | Blindlauf beurteilen, Pipeline-Befunde | nein |

Wer fremden Text liest, schreibt nicht (P-03). Die zwei Writer schreiben,
weil sie nur das Register sehen — keine Rohunterlagen.

Drei Agenten sind **Messinstrumente** und haben deshalb weniger als die
anderen: `ueberdehnungs-pruefer` und `gegenanwalt` haben kein Memory, der
`gegenanwalt` zusätzlich kein Innenwissen — er liest das Schreiben und das
Zeugnis, nicht das Register, nicht die Befunde und nicht den Mandantenbrief.
Der echte Empfänger hat die auch nicht, und mit ihnen läse er wohlwollender
als er. Ein Messinstrument, dem man etwas wegnimmt, wird genauer.

## Datenschutz

Ein Arbeitszeugnis enthält Name, Beschäftigungszeitraum und
Leistungsbeurteilung einer identifizierbaren Person. `faelle/`, `gates/` und
`laeufe/` sind gitignoriert und gehören nicht in ein Remote (Z-07).

## Regelwerk

`docs/REGELWERK.md` — die Regeln der Pipeline (Z, A, P, M). Das Fachwissen
liegt in `regelwerk/` und ist dort Datum, nicht Regel: im Konflikt geht
`docs/REGELWERK.md` vor.
