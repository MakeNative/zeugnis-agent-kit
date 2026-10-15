#!/usr/bin/env python3
"""Prüft Befunde und Schreiben gegen das Anspruchsgate.

    anspruchsgate.py [fall-id ...]

Prüft nach Regelwerk:
  A-01  jeder Befund trägt genau eine Gate-Stufe 1–4; Stufe 4 steht in keinem Schreiben
  A-02  Beweislast wird nicht aus der Ampelfarbe hergeleitet
  A-03  ein freiwilliger Wunsch steht nicht neben Frist, Klage oder Pflichtverletzung
  A-06  interne Steuerung (Satz-IDs, Ampeln, Q-Status, Prioritäten) bleibt aus den Schreiben
  Z-03  ein tragender Befund (Prio A) stützt sich auf einen sichtbaren Wortlaut
  Z-05  Konfidenz und Rechtsstatus sind gesetzt und passen zur Gate-Stufe
  Z-06  ein Befund aus Q4/Q5 behauptet keinen Rechtsmangel

Ein Schreiben verweist auf einen Befund über einen Marker am Absatzanfang:

    <!-- befund: B-03 -->
    Die Angabe des Beschäftigungszeitraums ist unrichtig. …

Der Marker ist für dieses Skript da. Im versandfertigen Text fällt er weg,
und das ist genau der Punkt von A-06: die Prüfbarkeit hängt nicht daran,
dass der Brief wie eine Datenbank aussieht.

Exit 0 wenn ohne Befund, 1 mit Befunden, 2 bei Abbruch.
Schreibt `gates/anspruchsgate.md`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

MARKER = re.compile(r"<!--\s*befund:\s*([A-Za-z0-9][\w-]*)\s*-->")

# Harte Anspruchsbehauptung: setzt eine Pflichtverletzung als feststehend.
# Erlaubt nur bei Gate-Stufe 1.
# Die erste Fassung kannte nur Verbformen. Ein Loch-Test fand damit die
# Lücke, die A-03 eigentlich schließen soll: „Wir bitten um eine Aussage …
# Eine Weigerung würden wir als Verstoss gegen Ihre Pflichten bewerten."
# Das ist eine freiwillige Bitte, als Pflichtverletzung verkleidet — und sie
# lief durch, weil „Verstoß gegen … Pflichten" die Substantivform ist und das
# Wort „Frist" fehlte.
#
# Aufgenommen sind deshalb Substantivformen und ASCII-Schreibungen. Nicht
# aufgenommen ist die bloße Nennung einer Pflicht: „ohne Anerkennung einer
# Rechtspflicht" ist der Verzicht auf die Behauptung, nicht die Behauptung.
HART = re.compile(
    r"\b(?:Pflichtverletzung|pflichtwidrig\w*|rechtswidrig|unzulässig|"
    r"nicht\s+zulässig|verstößt|verstoßen|verstoesst|verstossen|"
    r"zu\s+berichtigen|berichtigen\s+Sie|haben\s+Anspruch|"
    r"Anspruch\s+auf\s+Berichtigung|verpflichtet\s+sind|"
    r"Verletzung\s+(?:\w+\s+){0,2}Pflicht\w*|"
    r"Versto(?:ß|ss)\s+gegen)\b",
    re.I,
)
# Druckmittel. Darf nicht in einem Abschnitt stehen, der nur eine Bitte trägt.
DRUCK = re.compile(
    r"\b(Frist|fristgemäß|fristgerecht|Klage|klageweise|gerichtlich|"
    r"Zwangsvollstreckung|Zwangsgeld|Schadensersatz|Verzug|Rechtsweg)\b",
    re.I,
)
# Freiwilligkeit muss ausdrücklich werden, nicht bloß höflich klingen.
#
# Die erste Fassung war zu wörtlich und hat beim ersten Kontakt mit echtem
# Text vier Fehlalarme auf vier Befunde erzeugt: `\bfreiwillig\b` traf
# „freiwillige Anregung" nicht, `kein Anspruch` nicht „kein einklagbarer
# Anspruch", `bitten wir` nicht „können wir nur bitten". Drei Fehlerklassen —
# Flexion, Einschub, Wortstellung —, und in allen drei Fällen hatte der
# Writer die Freiwilligkeit sauber hingeschrieben.
#
# Deshalb: Wortstämme statt Wortformen, Einschübe erlaubt, und die
# Formulierungen aufgenommen, die ein Jurist tatsächlich wählt.
FREIWILLIG = re.compile(
    r"freiwillig\w*"
    r"|ohne\s+(?:\w+\s+){0,2}(?:rechtliche\w*\s+Verpflichtung|Anerkennung|"
    r"Rechtspflicht|Rechtsanspruch)"
    r"|kein\w*\s+(?:\w+\s+){0,3}(?:Rechts)?anspruch"
    r"|(?:nicht|kein\w*)\s+(?:\w+\s+){0,2}einklagbar\w*"
    r"|nicht\s+als\s+Forderung"
    r"|Entgegenkommen"
    r"|\bbitte\w*\b"
    r"|\banregen\b|\bAnregung\w*|regen\s+wir\b"
    r"|dankbar|begrüßen\w*|begruessen\w*"
    r"|darf\s+(?:\w+\s+){0,2}(?:nein\s+sagen|ablehnen|absehen)",
    re.I,
)
# A-02: Ampel und Darlegungslast im selben Satz.
AMPEL_WORT = re.compile(r"\b(Ampel|rote?s? Ampel|🔴|🟠|🟢|\[ROT\]|\[ORANGE\]|\[GRÜN\])", re.I)
LAST_WORT = re.compile(r"\b(Beweislast|Darlegungslast|darlegen|beweisen|Beweisführung)\b", re.I)
SATZ_TRENN = re.compile(r"(?<=[.!?;])\s+")

# A-06: was in einem Schreiben nichts zu suchen hat.
INTERN = {
    "Ampelsymbol": re.compile(r"🔴|🟠|🟢|⬜|\[ROT\]|\[ORANGE\]|\[GRÜN\]"),
    "Satz-ID": re.compile(r"(?<![\w-])S\d{1,3}(?![\w-])"),
    "Q-Status": re.compile(r"(?<![\w-])Q[1-5](?![\w-])"),
    "Gate-Stufe": re.compile(r"\bGate-?Stufe\b|\bStufe [1-4]\b", re.I),
    "Konfidenzangabe": re.compile(r"\bKonfidenz\b", re.I),
    "Prioritätsbuchstabe": re.compile(r"\bPrio(?:rität)?\s*[ABC]\b", re.I),
}


def befunde_pruefen(b: g.Befunde, fall: str, befunde: list[dict], register: list[dict]):
    karte = g.satz_karte(register)
    gesehen: set[str] = set()

    for eintrag in befunde:
        bid = eintrag.get("befund_id", "?")
        if bid in gesehen:
            b.add("A-01", fall, bid, "Befund-ID doppelt vergeben")
        gesehen.add(bid)

        for feld in g.PFLICHT_BEFUND:
            if not eintrag.get(feld):
                b.add("A-01", fall, bid, f"Pflichtfeld `{feld}` fehlt")

        stufe = eintrag.get("gate_stufe")
        if stufe not in (1, 2, 3, 4):
            b.add("A-01", fall, bid, f"gate_stufe ist `{stufe}` — erlaubt sind 1, 2, 3, 4")
            stufe = None

        prio = eintrag.get("prio")
        if prio not in g.PRIO:
            b.add("A-01", fall, bid, f"prio ist `{prio}` — erlaubt sind {', '.join(g.PRIO)}")

        konf = eintrag.get("konfidenz")
        if konf not in g.KONFIDENZ:
            b.add("Z-05", fall, bid, f"konfidenz ist `{konf}` — erlaubt sind {', '.join(g.KONFIDENZ)}")
        rs = eintrag.get("rechtsstatus")
        if rs not in g.RECHTSSTATUS:
            b.add("Z-05", fall, bid, f"rechtsstatus ist `{rs}` — erlaubt sind {', '.join(g.RECHTSSTATUS)}")

        # Z-05 als Kopplungsprüfung: ein Befund, dessen Tatsachengrundlage
        # unsicher ist, kann kein feststehender Rechtsmangel sein. Er wird
        # Stufe 2 — zu belegender Punkt —, nicht Stufe 1.
        if konf == "niedrig" and stufe == 1:
            b.add(
                "Z-05", fall, bid,
                "niedrige Konfidenz und Gate-Stufe 1: ein unsicherer Befund wird als "
                "feststehender Rechtsmangel verlangt. Stufe 2, bis die Tatsache bestätigt ist",
            )

        # Z-06: Schlussfolgerung und Ungeklärtes tragen keine Tatsache.
        ids = eintrag.get("satz_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        bekannt = [i for i in ids if i in karte]
        for i in ids:
            if i not in karte:
                b.add("Z-03", fall, bid, f"verweist auf `{i}` — im Register nicht vorhanden")
        if bekannt:
            status = {karte[i].get("q_status") for i in bekannt}
            if status and status <= set(g.Q_TRAEGT_KEINE_TATSACHE) and stufe == 1:
                b.add(
                    "Z-06", fall, bid,
                    f"stützt sich nur auf {'/'.join(sorted(status))} "
                    "(Schlussfolgerung oder ungeklärt) und behauptet trotzdem einen Rechtsmangel",
                )
            if prio == "A" and not any(
                karte[i].get("q_status") in ("Q1", "Q2") and karte[i].get("wortlaut") for i in bekannt
            ):
                b.add(
                    "Z-03", fall, bid,
                    "Prio A ohne sichtbaren Wortlaut: kein zitierter Satz ist Q1 oder Q2 mit Text",
                )
            # Hier stand eine Z-04-Prüfung: ein Befund der Stufe 1 oder 2, der
            # sich ausschließlich auf Aufgaben- oder Formsätze stützt, sollte
            # als unzulässige Notenableitung gemeldet werden.
            #
            # Entfernt nach dem ersten Lauf an echten Fällen, weil sie in beide
            # Richtungen falsch lag. Ein Formmangel — leere Unterschriftszeile,
            # falscher Beschäftigungszeitraum — ruht naturgemäß allein auf
            # einem Formsatz und ist trotzdem der stärkste Punkt eines Falls.
            # Ein Auslassungsbefund zitiert die Aufgabenliste als Beleg der
            # Erwartbarkeit: dass Führung ausdrücklich zu den Aufgaben zählte,
            # ist genau der Grund, warum eine fehlende Führungsbeurteilung
            # tragen kann.
            #
            # Ob ein Befund aus einer Aufgabenliste eine Note herleitet oder
            # die Erwartbarkeit belegt, steht nicht im Typ. Das ist eine
            # Wertung und gehört nach P-04 nicht in ein Skript — sie liegt
            # beim `ueberdehnungs-pruefer`. Z-04 wird an der Quelle geprüft,
            # in `fertig_definition.py`: dort darf eine Aufgabenkarte keine
            # Notenspanne tragen, und das ist entscheidbar.

        # A-02: Ampelfarbe als Beweislastargument.
        for satz in SATZ_TRENN.split(eintrag.get("begruendung", "")):
            if AMPEL_WORT.search(satz) and LAST_WORT.search(satz):
                b.add(
                    "A-02", fall, bid,
                    f"Begründung leitet Beweislast aus der Ampel ab: „{satz.strip()[:110]}…"
                    if len(satz.strip()) > 110 else
                    f"Begründung leitet Beweislast aus der Ampel ab: „{satz.strip()}"
                )


def schreiben_pruefen(b: g.Befunde, fall: str, name: str, text: str, befunde: list[dict]):
    stufen = {e.get("befund_id"): e.get("gate_stufe") for e in befunde}

    for art, rx in INTERN.items():
        for nr, zeile in enumerate(text.splitlines(), 1):
            if zeile.lstrip().startswith("<!--"):
                continue
            if rx.search(zeile):
                b.add("A-06", fall, f"{name}.md:{nr}", f"{art} im Schreiben: „{zeile.strip()[:90]}")

    zitiert: set[str] = set()
    for zeile_nr, titel, abschnitt in g.abschnitte(text):
        ids = MARKER.findall(abschnitt)
        # Marker stehen oft allein in einer Zeile und bilden dann mit dem
        # Absatz keinen gemeinsamen Block. Dann gilt der Marker der nächsten
        # Textzeile — deshalb wird der Rohtext mitgeprüft.
        if not ids:
            continue
        zitiert |= set(ids)
        ohne_marker = MARKER.sub("", abschnitt).strip()
        bezug = f"{name}.md:{zeile_nr}"

        for bid in ids:
            stufe = stufen.get(bid)
            if stufe is None:
                b.add("A-01", fall, bezug, f"verweist auf Befund `{bid}` — in befunde.jsonl nicht vorhanden")
                continue
            if stufe == 4:
                b.add(
                    "A-01", fall, bezug,
                    f"Befund `{bid}` ist Gate-Stufe 4 (kein tragfähiger Punkt) und steht trotzdem im Schreiben",
                )
            if stufe == 3:
                if DRUCK.search(ohne_marker):
                    b.add(
                        "A-03", fall, bezug,
                        f"Befund `{bid}` ist eine freiwillige Bitte, der Abschnitt nennt aber "
                        f"„{DRUCK.search(ohne_marker).group(0)}“",
                    )
                if HART.search(ohne_marker):
                    b.add(
                        "A-03", fall, bezug,
                        f"Befund `{bid}` ist eine freiwillige Bitte, wird aber als Anspruch formuliert: "
                        f"„{HART.search(ohne_marker).group(0)}“",
                    )
                elif not FREIWILLIG.search(ohne_marker):
                    b.add(
                        "A-03", fall, bezug,
                        f"Befund `{bid}` ist freiwillig, der Abschnitt macht das nicht ausdrücklich",
                    )
            if stufe == 2 and HART.search(ohne_marker):
                b.add(
                    "A-01", fall, bezug,
                    f"Befund `{bid}` hat offene Tatsachengrundlage (Stufe 2), der Abschnitt behauptet "
                    f"aber feststehend: „{HART.search(ohne_marker).group(0)}“",
                )

    # Gegenseitenschreiben ohne jeden Marker ist nicht prüfbar. Das ist kein
    # Formfehler, sondern ein blinder Fleck: ohne Zuordnung kann kein Gate
    # sagen, ob eine Bitte als Anspruch verkauft wird.
    if name == "gegenseite" and not zitiert:
        b.add(
            "A-01", fall, f"{name}.md",
            "kein einziger Befund-Marker — das Schreiben ist gegen die Befundlage nicht prüfbar",
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fall", nargs="*", help="Fall-IDs (Default: alle)")
    a = p.parse_args()

    w = g.wurzel()
    ziel = a.fall or g.faelle(w)
    if not ziel:
        g.fehler(f"Keine Fälle unter {w / 'faelle'}")

    b = g.Befunde()
    gezaehlt = {"faelle": 0, "befunde": 0, "schreiben": 0}

    for fall in ziel:
        register = g.register_lesen(w, fall)
        befunde = g.befunde_lesen(w, fall)
        gezaehlt["faelle"] += 1
        gezaehlt["befunde"] += len(befunde)

        if not register:
            b.add("Z-01", fall, "register.jsonl", "leer oder fehlt — ohne Register ist kein Befund prüfbar")
        if not befunde:
            b.add("A-01", fall, "befunde.jsonl", "leer oder fehlt")
            continue

        befunde_pruefen(b, fall, befunde, register)
        for name in ("gegenseite", "mandant"):
            text = g.schreiben_lesen(w, fall, name)
            if text is None:
                continue
            gezaehlt["schreiben"] += 1
            schreiben_pruefen(b, fall, name, text, befunde)

    zeilen = [
        "# Anspruchsgate",
        "",
        f"Stand: {g.heute()}",
        "",
    ] + g.umfang(w, ziel) + [
        f"- Befunde: {gezaehlt['befunde']}",
        f"- Geprüfte Schreiben: {gezaehlt['schreiben']}",
        f"- Gate-Befunde: {len(b)}",
    ]

    # Ohne Schreiben bleibt die Hälfte dieses Gates ungetestet. Das muss im
    # Bericht stehen, nicht im Kopf der Person, die ihn liest.
    offen = []
    if gezaehlt["schreiben"] == 0:
        offen.append(
            "**A-01 Stufenmischung, A-03 und A-06** — es lag kein Schreiben vor. "
            "Ob eine freiwillige Bitte neben einer Frist steht, ob ein Stufe-4-Punkt "
            "im Text auftaucht und ob interne Steuerung im Klartext landet, ist "
            "damit nicht geprüft, sondern ungeprüft."
        )
    if not any(g.befunde_lesen(w, f) for f in ziel):
        offen.append(
            "**alles Übrige** — kein Fall trug Befunde. Dieses Gate hat auf leerer "
            "Eingabe grün gemeldet; das ist keine Freigabe."
        )

    if b:
        zeilen += b.zeilen()
        zeilen += [
            "",
            "---",
            "",
            "Diese Befunde sind kein Urteil über die Sache. Sie sagen, dass ein Schritt",
            "übersprungen wurde — und die Skill entscheidet, was daraus folgt (P-02).",
        ]
    else:
        zeilen += [
            "",
            "Ohne Befund in dem oben genannten Umfang. Das ist keine Aussage über",
            "Fälle oder Schritte, die nicht geprüft wurden.",
        ]
    zeilen += g.nicht_geprueft_block(offen)

    pfad = g.bericht_schreiben(w, "anspruchsgate.md", zeilen)
    alle = g.faelle(w)
    print(
        f"Geprüft {len(ziel)} von {len(alle)} Fällen · "
        f"Befunde {gezaehlt['befunde']} · Schreiben {gezaehlt['schreiben']}"
    )
    for regel, gruppe in b.nach_regel().items():
        print(f"  {regel}: {len(gruppe)}")
    if b:
        print(f"BEFUNDE → {pfad}")
    else:
        print(f"OHNE BEFUND im geprüften Umfang → {pfad}")
        for o in offen:
            print(f"  UNGEPRÜFT: {o.split('—')[0].strip().replace('**', '')}")
    return 1 if b else 0


if __name__ == "__main__":
    raise SystemExit(main())
