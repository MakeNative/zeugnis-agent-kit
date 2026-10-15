#!/usr/bin/env python3
"""Stellt einen Blindlauf den Sollkorridoren der Upstream-Testmatrix gegenüber.

    blindlauf.py <lauf-name> [--upstream PFAD] [--vorbereiten]

`--vorbereiten` legt die Laufordner an und listet die zu prüfenden PDFs, ohne
die Lösung anzufassen. Ohne `--vorbereiten` wird ausgewertet.

Zwei Zahlen, getrennt gehalten (M-02):

  Korridortreffer   liegt die Gesamtnote im Sollkorridor — rein rechnerisch
  Überdehnung       hat der Lauf einen Befund erfunden, den die Spalte
                    `Nicht überdehnen` ausschließt — das entscheidet ein Agent

Die zweite Zahl kann ein Skript nicht bestimmen. „Gesundheitswunsch nicht als
Krankheitscode lesen" ist keine Zeichenkette, die man suchen kann. Das Skript
stellt deshalb je Fall die Ausschlussregel neben die eigenen Befunde und
markiert Verdachtsfälle über Wortüberlappung; geurteilt wird im
`lauf-auswerter` (P-04 von der anderen Seite: was nicht deterministisch ist,
gehört nicht ins Skript).

Keine Gesamtpunktzahl. Ein Prüfer, der überall Codes sieht, trifft mehr
Korridore und überdehnt mehr — eine addierte Note würde das verstecken.

Exit 0 immer bei --vorbereiten, sonst 0 ohne Verfehlung, 1 mit.
Schreibt `laeufe/<lauf-name>/AUSWERTUNG.md` und `GEGENUEBERSTELLUNG.md`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

GESAMTNOTE = re.compile(r"^\s*GESAMTNOTE:\s*(.+?)\s*$", re.M)
# Der Schwerpunkt darf in der GESAMTNOTE-Zeile stehen („2 bis 3, Schwerpunkt 2")
# oder als eigene Zeile. Beides kommt vor, weil die Agenten ihn in Prosa
# formulieren.
SCHWERPUNKT = re.compile(r"Schwerpunkt\s*(?:bei\s*|auf\s*)?([1-5])", re.I)
BEFUND_BLOCK = re.compile(r"^\s*BEFUNDE\s*$(.*?)(?=^\s*[A-ZÄÖÜ]{4,}:|\Z)", re.M | re.S)
BULLET = re.compile(r"^\s*[-*]\s+(.*\S)", re.M)

# Wörter, die in fast jedem Zeugnisbefund vorkommen und deshalb keine
# Überlappung belegen.
RAUSCHEN = {
    "zeugnis", "arbeitszeugnis", "formulierung", "bewertung", "leistung",
    "verhalten", "satz", "aussage", "arbeitgeber", "arbeitnehmer", "note",
    "gesamtbild", "einschränkung", "schlussformel",
    "werden", "wurde", "sollte", "können", "dieser", "diese", "dieses",
    # Wertende Beiwörter der Ausschlussregeln selbst. Sie beschreiben, WIE
    # eine Lesart falsch wäre („nicht als *sicheren* Kündigungscode"), und
    # sind nie der verbotene Begriff. In einem Befund stehen sie harmlos
    # („sicher feststellbar") und erzeugten dort Fehlalarme.
    "sicher", "sicheren", "sichere", "feste", "fester", "festen",
    "automatisch", "isoliert", "neutral", "neutrale", "neutralen",
    "allein", "behandeln", "ableiten", "darstellen", "lesen", "werten",
    "konstruieren", "unterstellen", "gleichsetzen", "beanstanden",
}
# Negationen und Ablehnungswörter werden vor dem Vergleich gelöscht, nicht als
# Rauschen abgezogen. Über die Stammkürzung überlebte sonst „keinen" aus
# „begründet keinen Anspruch" — und der Filter feuerte ausgerechnet auf die
# Wörter, die beweisen, dass der Befund die Fehllesart ABLEHNT. Der Filter war
# damit antikorreliert zu dem, was er finden soll.
NEGATION = re.compile(
    r"\b(nicht|kein|keine|keinen|keiner|keines|niemals|weder|noch|ohne|"
    r"unzulässig|abgelehnt|ausgeschlossen|verworfen)\b",
    re.I,
)
WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{5,}")
# Für die Schlüsselbegriffe der verbotenen Lesart reichen vier Zeichen.
WORT_KURZ = re.compile(r"[A-Za-zÄÖÜäöüß]{4,}")
# Die Ausschlussregeln zitieren die Formulierung, um die es geht — „Hat sich in
# das Team integriert", „im Großen und Ganzen". Taucht so ein Zitat im eigenen
# Befund auf, ist das der stärkste Verdacht, den ein Skript haben kann.
ZITAT = re.compile(r"[„\"»]([^„\"»«\n]{8,})[\"«“]")
LEER = re.compile(r"\s+")


UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def stamm(wort: str) -> str:
    """Erste sechs Zeichen als Stamm, Umlaute gefaltet.

    „Negativnote" und „Negativcode" sind dasselbe Argument in zwei Wörtern;
    auf Wortgleichheit zu prüfen würde den Fall übersehen. Sechs Zeichen
    fangen die deutschen Zusammensetzungen, ohne „Leistung" und „Leiter"
    zu verschmelzen.

    Die Faltung ist nötig, weil die Agenten ASCII schreiben
    („Kuendigungscode") und die Matrix Umlaute („Kündigungscode"). Ohne sie
    konnte der Filter genau die Begriffe nie treffen, auf die es ankommt.
    """
    return wort.lower().translate(UMLAUT)[:6]


def normal(text: str) -> str:
    return LEER.sub(" ", text.lower().replace("„", "").replace("“", "").replace('"', "")).strip()


def matrix_lesen(wz: Path) -> dict[str, dict]:
    datei = wz / "testakten" / "TESTFALL-MATRIX.md"
    if not datei.is_file():
        g.fehler(
            f"`{datei}` nicht gefunden. Der Prüfkorpus kommt aus dem Upstream; "
            "klone ihn mit der Skill `adopt`."
        )
    faelle: dict[str, dict] = {}
    for tab in g.tabellen(datei.read_text(encoding="utf-8")):
        for zeile in tab:
            nr = (zeile.get("Nr.") or "").strip()
            if not nr.isdigit():
                continue
            faelle[nr.zfill(2)] = {
                "nr": nr.zfill(2),
                "rolle": (zeile.get("Rolle") or "").strip(),
                "sollkorridor": (zeile.get("Sollkorridor") or "").strip(),
                "kernbefund": (zeile.get("Kernbefund") or "").strip(),
                "nicht_ueberdehnen": (zeile.get("Nicht überdehnen") or "").strip(),
            }
    if not faelle:
        g.fehler(f"`{datei}` enthält keine lesbare Fallmatrix — Spaltennamen geändert?")

    # Die Matrix nennt sich selbst „die kompakte Ground Truth" und ist genau
    # das: eine verlustbehaftete Zusammenfassung. Die Erwartungshorizonte der
    # Testaktensätze tragen je Fall zwei bis drei Ausschlussregeln statt einer.
    # Im ersten Lauf fehlte dadurch in zwei von drei Fällen genau die Regel,
    # an die der Lauf tatsächlich gerührt hat — darunter der schärfste des
    # Falls 05. Wer nur die Matrix liest, untercountet systematisch.
    for horizont in sorted((wz / "testakten").rglob("90-erwartungshorizont-und-pruefpunkte.md")):
        text = horizont.read_text(encoding="utf-8")
        for block in re.split(r"^###\s+Fall\s+", text, flags=re.M)[1:]:
            nr = re.match(r"(\d+)", block)
            if not nr or nr.group(1).zfill(2) not in faelle:
                continue
            zusatz = [
                m.group(1).strip()
                for m in re.finditer(r"\*\*Nicht überdehnen:\*\*\s*(.+?)(?=\n\s*[-*]|\n\n|\Z)",
                                     block, re.S)
            ]
            if zusatz:
                eintrag = faelle[nr.group(1).zfill(2)]
                vorher = eintrag["nicht_ueberdehnen"]
                voll = " ".join(z.replace("\n", " ") for z in zusatz)
                eintrag["nicht_ueberdehnen"] = voll if voll else vorher
                eintrag["matrix_kurzfassung"] = vorher
                eintrag["quelle_guardrail"] = horizont.name
    return faelle


def befunde_aus_akte(w: Path, nr: str) -> tuple[list[str], list[str]] | None:
    """Liest die echten Befunde des Falls aus `faelle/blind-<nr>/befunde.jsonl`.

    Die Prosa-Laufdatei ist eine Abschrift und verliert, was die Messung
    braucht. Im ersten Lauf an echten Fällen gingen dabei vier Dinge verloren,
    alle in Richtung „sieht wie Überdehnung aus": eine vom Gate erzwungene
    Korrektur fehlte, eine entfernte Absolutheit war wiederhergestellt, eine
    am Dokument verankerte Belastungsaussage las wie eine Branchenprämisse,
    und eine eingehaltene Ausschlussregel war halbiert.

    Gibt (behauptungen, absagen) zurück. Ein Befund auf `gate_stufe: 4` ist
    eine **Absage** — die Pipeline sagt dort selbst, dass der Punkt nicht
    trägt. Ihn gegen den Negativkatalog zu prüfen verwechselt die Einhaltung
    einer Regel mit ihrem Bruch; genau das erzeugte im ersten Lauf drei
    Fehlalarme bei drei Markierungen.
    """
    for fall in (f"blind-{nr}", nr):
        datei = w / "faelle" / fall / "befunde.jsonl"
        if datei.is_file():
            behauptungen, absagen = [], []
            for e in g.jsonl_lesen(datei):
                text = str(e.get("begruendung", "")).strip()
                if not text:
                    continue
                zeile = f"[{e.get('befund_id','?')} Stufe {e.get('gate_stufe','?')}] {text}"
                (absagen if e.get("gate_stufe") == 4 else behauptungen).append(zeile)
            return behauptungen, absagen
    return None


def lauf_lesen(ordner: Path, nr: str, w: Path | None = None) -> dict | None:
    datei = ordner / f"{nr}.md"
    if not datei.is_file():
        return None
    text = datei.read_text(encoding="utf-8")
    note = GESAMTNOTE.search(text)
    block = BEFUND_BLOCK.search(text)
    sp = SCHWERPUNKT.search(note.group(1)) if note else None
    if sp is None:
        sp = SCHWERPUNKT.search(text)
    befunde = BULLET.findall(block.group(1)) if block else []
    absagen: list[str] = []
    quelle = "laufdatei"
    if w is not None:
        akte = befunde_aus_akte(w, nr)
        if akte is not None:
            befunde, absagen = akte
            quelle = "befunde.jsonl"
    return {
        "note_text": note.group(1) if note else "",
        "noten": g.noten_menge(note.group(1)) if note else set(),
        "schwerpunkt": int(sp.group(1)) if sp else None,
        "befunde": befunde,
        "absagen": absagen,
        "befundquelle": quelle,
        "datei": datei,
    }


def korridor_urteil(soll: set[int], ist: set[int], schwerpunkt: int | None = None) -> str:
    """Vergleicht die eigene Notenspanne mit dem Sollkorridor.

    Der Schwerpunkt ist nötig, weil eine reine Teilmengenprüfung ehrliche
    Spannen bestraft. „2 bis 3, Schwerpunkt 2" gegen Korridor 2 ist keine
    halbe Leistung — die Pipeline hat die Note getroffen und zusätzlich
    offengelegt, wohin sie abweichen könnte. Wer dafür abgestuft wird, lernt,
    Punktnoten zu behaupten, die er nicht hat; genau das verbietet die
    Scheingenauigkeitsregel.

    Eine Spanne, deren Schwerpunkt im Korridor liegt und die ihn berührt,
    zählt deshalb als Treffer — kenntlich gemacht, nicht stillschweigend.
    """
    if not ist:
        return "keine Note"
    if ist <= soll:
        return "treffer"
    if schwerpunkt is not None and schwerpunkt in soll and (ist & soll):
        return "treffer (schwerpunkt)"
    if ist & soll:
        return "teiltreffer"
    return "verfehlt"


def schluesselbegriffe(regel: str) -> set[str]:
    """Zieht aus der Ausschlussregel die Begriffe der *verbotenen* Lesart.

    Die Regeln sind gebaut als „<Gegenstand> nicht als <verbotene Lesart>":

        Gesundheitswunsch zum Ruhestand nicht als Krankheitscode lesen.
        Das neutrale Enddatum allein ist kein Kündigungscode.

    Entscheidend ist allein, was nach der Negation steht. „Gesundheitswunsch"
    und „Ruhestand" teilen beide Texte — der Befund, der die Lesart behauptet,
    und der, der sie ablehnt. Nur „Krankheitscode" unterscheidet sie, und auch
    das erst zusammen mit der Frage, ob er im Befund negiert ist.
    """
    begriffe: set[str] = set()
    # Das Fenster endet am ersten Satzgliedwechsel. Ohne diese Grenze griff es
    # über den verbotenen Begriff hinaus in den Folgesatz: aus „nicht als
    # Alkoholbehauptung und das neutrale Enddatum nicht als sicheren
    # Kündigungscode" wurden auch „neutral", „sicher" und „Enddatum" zu
    # Schlüsselbegriffen — Wörter, die in jedem zweiten Befund harmlos stehen.
    grenze = re.compile(r"\b(?:und|oder|sondern|aber|sowie|bzw)\b|[;,.]")
    for m in re.finditer(
        r"\b(?:nicht|kein|keine|keinen|keiner|keines|weder|noch)\b\s*"
        r"(?:als\s+|automatisch\s+|ohne\s+\w+\s+|isoliert\s+(?:als\s+)?)?(.{0,60})",
        regel, re.I,
    ):
        # Vier Zeichen, nicht fünf: „Code" ist in mehreren Ausschlussregeln
        # genau der verbotene Begriff („nicht isoliert als Code behandeln").
        # Mit der Fünf-Zeichen-Schwelle fiel die Regel auf den Stammfilter
        # zurück und markierte dort die Ablehnung.
        fenster = m.group(1)
        if (schnitt := grenze.search(fenster)):
            fenster = fenster[: schnitt.start()]
        for w in WORT_KURZ.findall(fenster):
            # Die Rauschliste greift auf ganze Wörter, nicht auf Stämme.
            # Sonst löscht das Rauschwort „leistung" über die
            # Sechs-Zeichen-Kürzung auch „Leistungsminus" — und damit genau
            # den Begriff, auf den die Ausschlussregel zielt.
            if w.lower() in RAUSCHEN:
                continue
            st = stamm(w)
            if st:
                begriffe.add(st)
    return begriffe


def negiert(text: str, st: str) -> bool:
    """Steht der Begriff im Befund unter einer Negation?

    Gesucht wird eine Negation in den 45 Zeichen vor dem Begriff — die
    Reichweite, in der „ausdrücklich kein Krankheitscode" und „ist kein
    Konfliktsignal" liegen, aber nicht ein zwei Sätze entfernter Nebensatz.
    """
    gefalten = text.lower().translate(UMLAUT)
    for m in re.finditer(re.escape(st), gefalten):
        vorher = gefalten[max(0, m.start() - 45):m.start()]
        if NEGATION.search(vorher):
            return True
    return False


def ueberdehnung_verdacht(regel: str, befunde: list[str]) -> list[str]:
    """Markiert Befunde, die der ausgeschlossenen Lesart nahekommen.

    Drei Stufen, von scharf nach grob:

    1. Der von der Regel zitierte Wortlaut taucht im Befund auf.
    2. Ein Begriff der verbotenen Lesart taucht **unnegiert** auf. Steht er
       unter einer Negation, lehnt der Befund die Lesart ab — das ist
       Einhaltung, nicht Bruch, und darf nicht markiert werden.
    3. Nur wenn sich aus der Regel kein Begriff ziehen ließ: zwei überlappende
       Wortstämme als Notfallfilter.

    Die erste Fassung hatte nur Stufe 3 und war dadurch **antikorreliert** zu
    dem, was sie finden soll: weil die Agenten angewiesen sind, die abgelehnte
    Lesart zu benennen, maximiert Wortüberlappung genau dort, wo die Pipeline
    am korrektesten arbeitet. Drei Markierungen im ersten Lauf, drei
    Fehlalarme, und alle drei trafen eine korrekte Ablehnung.

    Bleibt ein Filter, kein Urteil: geurteilt wird im `lauf-auswerter`.
    """
    zitate = [normal(z) for z in ZITAT.findall(regel) if len(normal(z)) >= 8]
    schluessel = schluesselbegriffe(regel)
    staemme = {stamm(w) for w in WORT.findall(NEGATION.sub(" ", regel))
               if w.lower() not in RAUSCHEN}
    staemme = {x for x in staemme if x}

    verdacht = []
    for b in befunde:
        nb = normal(b)
        gefalten = nb.translate(UMLAUT)

        # Die Negationsprüfung kommt VOR dem Zitat-Pfad. Ein Befund zitiert die
        # Formulierung oft gerade, um die Lesart abzulehnen — „die Wendung ‚hat
        # sich in das Team integriert' ist keine feste Negativnote". Zitat und
        # Ablehnung stehen dann im selben Satz, und wer das Zitat zuerst prüft,
        # markiert die Einhaltung.
        # Ließ sich aus der Regel ein Begriff der verbotenen Lesart ziehen,
        # entscheidet er allein. Taucht er nicht auf, berührt der Befund die
        # ausgeschlossene Lesart nicht — dann ist auch der Stammfilter nicht
        # zuständig. Der darf nur einspringen, wo die Regel keine auswertbare
        # Struktur hat, denn er kann Ablehnung und Behauptung prinzipiell
        # nicht unterscheiden: nach dem Löschen der Negationen sehen beide
        # gleich aus.
        if schluessel:
            vorhanden = [st for st in schluessel if st in gefalten]
            if [st for st in vorhanden if not negiert(b, st)]:
                verdacht.append(b)
            continue

        if any(z in nb for z in zitate):
            verdacht.append(b)
            continue

        eigen = {stamm(w) for w in WORT.findall(NEGATION.sub(" ", b))
                 if w.lower() not in RAUSCHEN}
        if staemme and len(staemme & eigen) >= 2:
            verdacht.append(b)
    return verdacht


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lauf", help="Name des Laufs, z. B. 2026-10-14-runde1")
    p.add_argument("--upstream", type=Path)
    p.add_argument("--vorbereiten", action="store_true", help="Laufordner anlegen, Lösung nicht anfassen")
    a = p.parse_args()

    w = g.wurzel()
    wz = (a.upstream or w / "upstream" / "arbeitszeugnispruefer-skill").resolve()
    ordner = w / "laeufe" / a.lauf
    pdfs = sorted((wz / "testakten").rglob("Arbeitszeugnis_*.pdf"))

    if a.vorbereiten:
        ordner.mkdir(parents=True, exist_ok=True)
        print(f"Laufordner: {ordner}")
        print(f"Testzeugnisse im Upstream: {len(pdfs)}")
        print()
        print("Je Fall eine Datei `<nr>.md` mit mindestens:")
        print("  FALL: <nr>")
        print("  GESAMTNOTE: <1–5, Spanne erlaubt>")
        print("  BEFUNDE")
        print("  - <ein Befund je Zeile>")
        print()
        for pdf in pdfs:
            nr = re.match(r"(\d+)", pdf.parent.name)
            print(f"  {nr.group(1) if nr else '??':>3}  {pdf.parent.name}")
        print()
        print("TESTFALL-MATRIX.md und die Erwartungshorizonte bleiben zu. Ein Lauf,")
        print("der die Lösung im Kontext hatte, hat nichts gemessen (M-01).")
        return 0

    if not ordner.is_dir():
        g.fehler(f"`{ordner}` gibt es nicht. Erst `blindlauf.py {a.lauf} --vorbereiten`.")

    faelle = matrix_lesen(wz)
    zeilen_aus = [
        "# Blindlauf-Auswertung",
        "",
        f"Lauf: `{a.lauf}`   Stand: {g.heute()}",
        f"Prüfkorpus: {len(faelle)} Fälle aus der Upstream-Testmatrix",
        "",
        "## Korridortreffer",
        "",
        "| Nr. | Rolle | Soll | Ist | Urteil |",
        "| --- | --- | --- | --- | --- |",
    ]
    zeilen_geg = [
        "# Gegenüberstellung für den Lauf-Auswerter",
        "",
        f"Lauf: `{a.lauf}`   Stand: {g.heute()}",
        "",
        "Je Fall: die ausdrücklich ausgeschlossene Fehllesart, daneben die eigenen",
        "Befunde. Die Verdachtsmarkierung ist Wortüberlappung, kein Urteil — ein",
        "nicht markierter Befund kann trotzdem überdehnen, ein markierter kann",
        "völlig in Ordnung sein.",
        "",
    ]

    zaehler = {"treffer": 0, "treffer (schwerpunkt)": 0, "teiltreffer": 0,
               "verfehlt": 0, "keine Note": 0, "kein Lauf": 0}
    verdacht_gesamt = 0
    absagen_gesamt = 0

    for nr, fall in sorted(faelle.items()):
        soll = g.noten_menge(fall["sollkorridor"])
        lauf = lauf_lesen(ordner, nr, w)
        if lauf is None:
            zaehler["kein Lauf"] += 1
            zeilen_aus.append(f"| {nr} | {fall['rolle']} | {fall['sollkorridor']} | — | **kein Lauf** |")
            continue
        urteil = korridor_urteil(soll, lauf["noten"], lauf["schwerpunkt"])
        zaehler[urteil] += 1
        zeilen_aus.append(
            f"| {nr} | {fall['rolle']} | {fall['sollkorridor']} | {lauf['note_text'] or '—'} | {urteil} |"
        )

        verdacht = ueberdehnung_verdacht(fall["nicht_ueberdehnen"], lauf["befunde"])
        verdacht_gesamt += len(verdacht)
        absagen_gesamt += len(lauf["absagen"])
        zeilen_geg += [
            f"## {nr} — {fall['rolle']}",
            "",
            f"**Nicht überdehnen:** {fall['nicht_ueberdehnen'] or '—'}",
            "",
            f"**Kernbefund laut Matrix:** {fall['kernbefund'] or '—'}",
            "",
            f"**Eigene Gesamtnote:** {lauf['note_text'] or '—'}   (Soll: {fall['sollkorridor']}, {urteil})",
            "",
            "**Eigene Befunde:**",
        ]
        if lauf["befunde"]:
            for b in lauf["befunde"]:
                zeilen_geg.append(f"- {'⚑ ' if b in verdacht else ''}{b}")
        else:
            zeilen_geg.append("- *keine*")
        zeilen_geg.append("")
        # Gate-4-Einträge sind Absagen, keine Behauptungen. Sie gehören in den
        # Bericht, weil sie belegen, dass die Pipeline eine Fehllesart gesehen
        # und verworfen hat — die Information, die die Messung eigentlich will.
        if lauf["absagen"]:
            zeilen_geg.append("**Ausdrücklich abgelehnt (Gate 4, nicht aufgenommen):**")
            for absage in lauf["absagen"]:
                zeilen_geg.append(f"- {absage}")
            zeilen_geg.append("")
        zeilen_geg.append(f"*Befundquelle: {lauf['befundquelle']}*")
        if fall.get("matrix_kurzfassung") and fall["matrix_kurzfassung"] != fall["nicht_ueberdehnen"]:
            zeilen_geg.append(
                f"*Guardrail aus {fall.get('quelle_guardrail', '?')}; "
                f"Matrix-Kurzfassung lautete nur: {fall['matrix_kurzfassung']}*"
            )
        zeilen_geg.append("")

    gelaufen = sum(v for k, v in zaehler.items() if k != "kein Lauf")
    zeilen_aus += [
        "",
        "## Zahlen",
        "",
        f"- Gelaufen: {gelaufen} von {len(faelle)}",
        f"- Treffer: {zaehler['treffer']}",
        f"- Treffer über Schwerpunkt: {zaehler['treffer (schwerpunkt)']}"
        "   (Spanne weiter als der Korridor, Schwerpunkt darin)",
        f"- Teiltreffer: {zaehler['teiltreffer']}",
        f"- Verfehlt: {zaehler['verfehlt']}",
        f"- Ohne Gesamtnote: {zaehler['keine Note']}",
        f"- Nicht gelaufen: {zaehler['kein Lauf']}",
        "",
        f"- Überdehnungs-Verdachtsfälle: {verdacht_gesamt} (Wortüberlappung, ungeprüft)",
        f"- Ausdrücklich abgelehnte Fehllesarten (Gate 4): {absagen_gesamt}"
        "   — Einhaltung, nicht Bruch; nicht als Befund gezählt",
        "",
        "Keine Gesamtpunktzahl, und die Überdehnungsrate steht hier nicht: sie",
        "entsteht erst, wenn der `lauf-auswerter` die Gegenüberstellung",
        "beurteilt hat (M-02).",
        "",
        "Eine Abweichung vom Korridor ist nicht automatisch falsch. Sie zählt als",
        "vertretbar, wenn die Begründung am vollständigen Wortlaut hängt — nicht",
        "an einem Katalogeintrag (M-03).",
        "",
        "Die Sollkorridore sind Autorenbehauptung über fiktive Fälle. Sie messen",
        "Konsistenz, nicht juristische Richtigkeit (M-04).",
    ]

    (ordner / "AUSWERTUNG.md").write_text("\n".join(zeilen_aus) + "\n", encoding="utf-8")
    (ordner / "GEGENUEBERSTELLUNG.md").write_text("\n".join(zeilen_geg) + "\n", encoding="utf-8")

    print(f"Lauf `{a.lauf}`: {gelaufen}/{len(faelle)} gelaufen")
    for k in ("treffer", "treffer (schwerpunkt)", "teiltreffer", "verfehlt",
              "keine Note", "kein Lauf"):
        print(f"  {k:12} {zaehler[k]}")
    print(f"  {'verdacht':12} {verdacht_gesamt}  (ungeprüft)")
    print(f"  {'absagen':12} {absagen_gesamt}  (Gate 4, Einhaltung)")
    print(f"→ {ordner / 'AUSWERTUNG.md'}")
    print(f"→ {ordner / 'GEGENUEBERSTELLUNG.md'}  — an den lauf-auswerter")
    return 1 if (zaehler["verfehlt"] or zaehler["keine Note"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
