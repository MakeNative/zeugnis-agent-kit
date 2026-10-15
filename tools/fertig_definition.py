#!/usr/bin/env python3
"""Prüft, ob ein Fall nach der Fertig-Definition abgeschlossen ist.

    fertig_definition.py [fall-id ...] [--ziel korrektur|verstehen|erstellen]

Das Anspruchsgate prüft die Befunde. Dieses Skript prüft den Fall als Ganzes:
sind die Pflichtstücke da, hängt die Gesamtnote an Einzelkarten, stimmen
Kopfdaten in allen Ausgaben überein, ist jede Fundstelle als geprüft oder als
ungeprüft gekennzeichnet.

Geprüft wird der maschinelle Teil der Fertig-Definition:
  F-01  register.jsonl und befunde.jsonl vorhanden und vollständig in den Pflichtfeldern
  F-02  jeder Prio-A-Befund hat Wortlaut, Gegenlesart, Rechtsstatus und Zielwortlaut
  F-03  die Gesamtnote liegt in der Spanne der tragenden Leistungssätze
  F-04  Kopfdaten stehen in jeder Ausgabe identisch
  F-05  bei Ziel `korrektur` liegen Mandanten- und Gegenseitenschreiben vor
  F-06  Zeugnisart, Personenstatus und Anspruchsnorm passen zusammen
  F-07  jede Fundstelle in einer Ausgabe ist als geprüft oder ungeprüft markiert (A-05)
  F-08  die Abdeckung ist ausdrücklich erklärt (P-06)

Was ein Skript nicht prüfen kann — ob der Zieltext wahr und taktisch sinnvoll
ist —, steht nicht hier. Das macht der `belegkette`-Durchgang der Skill.

Exit 0 wenn fertig, 1 wenn nicht, 2 bei Abbruch.
Schreibt `gates/fertig.md`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

AUSGABEN = ("mandant", "gegenseite", "pruefvermerk", "zeugnis")

# Normzuordnung nach Zeugnisart. Quelle ist der Upstream; hier steht nur die
# Zuordnung, die das Skript vergleichen kann — nicht ihre Begründung.
NORM_ERWARTET = {
    "einfach": "§ 109 Abs. 1 S. 2 GewO",
    "qualifiziert": "§ 109 Abs. 1 S. 3 GewO",
    "zwischenzeugnis": "§ 241 Abs. 2 BGB",
    "ausbildungszeugnis": "§ 16 BBiG",
    "dienstzeugnis": "§ 630 BGB",
}
# Ein Organmitglied ist kein Arbeitnehmer. Wer § 109 GewO für einen
# Geschäftsführer bemüht, hat den Status übersprungen — und damit Rechtsweg
# und Kostenregime gleich mit.
STATUS_UNVEREINBAR = {
    ("organperson", "einfach"),
    ("organperson", "qualifiziert"),
    ("auszubildender", "qualifiziert"),
    ("arbeitnehmer", "dienstzeugnis"),
}

FUNDSTELLE = re.compile(
    r"§+\s*\d+[\w\s.,§]*?(?:GewO|BGB|BBiG|ArbGG|ZPO|GmbHG|HGB)"
    r"|\b(?:BAG|BGH|LAG|ArbG|BVerfG)\b[^.;\n]{0,60}?\d+\s*[A-Za-z]+\s*\d+/\d+"
)
# Die Kennzeichnung einer ungeprüften Fundstelle schreibt niemand zweimal
# gleich. Die erste Fassung suchte nur „ungeprüft" und meldete deshalb einen
# Writer, der sauber „[Fundstelle noch nicht geprüft]" geschrieben hatte.
MARKER_UNGEPRUEFT = re.compile(
    r"ungeprüft|ungepruef|nicht\s+(?:\w+\s+){0,2}geprüft|nicht\s+(?:\w+\s+){0,2}gepruef"
    r"|nicht\s+verifiziert|noch\s+zu\s+prüfen|live\s+zu\s+prüfen|zu\s+verifizieren"
    r"|Rechtsstand\s+offen|vor\s+Versand\s+zu\s+(?:prüfen|verifizieren)",
    re.I,
)

# Ausgaben, die Kopfdaten tragen müssen. Der Mandantenbrief ist ausgenommen:
# er redet die Person mit „Sie" an und wiederholt ihren vollen Namen, ihre
# Position und ihre Beschäftigungsdaten nicht — sie kennt sie. Ihn zur
# Vollständigkeit zu verpflichten erzeugte im ersten Lauf drei Fehlalarme.
AUSGABEN_MIT_KOPFDATEN = ("gegenseite", "zeugnis", "pruefvermerk")
LEER = re.compile(r"\s+")

# Atomare Kopfdaten: Name, Daten, Arbeitgeber. Sie stehen im Schreiben so da
# oder gar nicht, und eine Abweichung ist ein Widerspruch — genau das soll
# F-04 finden.
#
# `position` gehört nicht dazu. „examinierte Altenpflegerin, seit 2010
# Wohnbereichsleitung" ist Freitext und wurde von der Skill zusammengesetzt;
# der Brief schrieb „Altenpflegerin, seit 2010 **als** Wohnbereichsleitung".
# Ein Wort Unterschied, kein Widerspruch. Darauf zu bestehen heißt, gegen das
# eigene Phrasing zu prüfen statt gegen das Dokument.
KOPFDATEN_ATOMAR = ("name", "beginn", "ende", "arbeitgeber", "geburtsdatum")
KERNWORT = re.compile(r"[A-Za-zÄÖÜäöüß]{6,}")

# Ein Vorbehalt bezieht sich auf das ganze Dokument, wenn er das Dokument oder
# die Gesamtheit der Fundstellen nennt. „Die zu Abschnitt I und II vorliegenden
# Fundstellen sind ebenfalls ungeprüft" ist so ein Satz.
GLOBAL_BEZUG = re.compile(
    r"\b(?:in\s+diesem\s+Schreiben|dieses\s+Schreibens?|Entwurfsnotiz|Entwurf\b"
    r"|sämtliche?\w*|samtliche?\w*|alle\s+(?:\w+\s+){0,2}Fundstellen?"
    r"|die\s+(?:\w+\s+){0,4}Fundstellen?|Anspruchsgrundlage)\b",
    re.I,
)


def fall_kopf(w: Path, fall: str) -> dict:
    p = g.fall_pfad(w, fall) / "fall.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        g.fehler(f"faelle/{fall}/fall.json: kein gültiges JSON — {e.msg}")


def ausgaben_lesen(w: Path, fall: str) -> dict[str, str]:
    out = {}
    for name in AUSGABEN:
        text = g.schreiben_lesen(w, fall, name)
        if text is not None:
            out[name] = text
    return out


def pruefen(b: g.Befunde, w: Path, fall: str, ziel_vorgabe: str | None):
    kopf = fall_kopf(w, fall)
    register = g.register_lesen(w, fall)
    befunde = g.befunde_lesen(w, fall)
    ausgaben = ausgaben_lesen(w, fall)
    karte = g.satz_karte(register)
    ziel = ziel_vorgabe or kopf.get("ziel", "")

    # F-01
    if not kopf:
        b.add("F-01", fall, "fall.json", "fehlt — ohne Mandatsblatt ist kein Abschluss prüfbar")
    if not register:
        b.add("F-01", fall, "register.jsonl", "leer oder fehlt")
    if not befunde and ziel in ("korrektur", "verhandeln", "klage-pruefen"):
        b.add("F-01", fall, "befunde.jsonl", f"leer, aber Ziel ist `{ziel}`")

    for satz in register:
        sid = satz.get("satz_id", "?")
        for feld in g.PFLICHT_SATZ:
            if not satz.get(feld):
                b.add("F-01", fall, sid, f"Satzkarte ohne `{feld}`")
        if satz.get("q_status") not in g.Q_STATUS:
            b.add("F-01", fall, sid, f"q_status ist `{satz.get('q_status')}`")
        if satz.get("typ") not in g.SATZ_TYP:
            b.add("F-01", fall, sid, f"typ ist `{satz.get('typ')}`")
        if satz.get("ampel") and satz["ampel"] not in g.AMPEL:
            b.add("F-01", fall, sid, f"ampel ist `{satz['ampel']}`")
        # Z-04 an der Quelle: eine Aufgabenbeschreibung mit Note.
        #
        # Geprüft wird auf eine *Note*, nicht auf ein belegtes Feld. Ein Agent,
        # der die Abwesenheit ausdrücklich hinschreibt — `"keine (Z-04,
        # Aufgabensatz)"` —, befolgt die Regel und darf nicht dafür gemeldet
        # werden. Entscheidend ist, ob eine Stufe 1 bis 5 darin steht.
        if satz.get("typ") in g.TYP_OHNE_NOTE and g.noten_menge(str(satz.get("notenspanne") or "")):
            b.add(
                "F-01", fall, sid,
                f"Typ `{satz['typ']}` trägt eine Notenspanne `{satz['notenspanne']}` — "
                "Aufgaben- und Formsätze werden nicht benotet",
            )

    # F-02
    for e in befunde:
        if e.get("prio") != "A":
            continue
        bid = e.get("befund_id", "?")
        ids = e.get("satz_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        if not any(karte.get(i, {}).get("wortlaut") for i in ids):
            b.add("F-02", fall, bid, "tragender Befund ohne Originalwortlaut im Register")
        if not any(karte.get(i, {}).get("gegenlesart") for i in ids):
            b.add("F-02", fall, bid, "tragender Befund ohne Gegenlesart — die neutrale Erklärung fehlt")
        if not e.get("zieltext") and not any(karte.get(i, {}).get("zielwortlaut") for i in ids):
            b.add("F-02", fall, bid, "tragender Befund ohne Zieltext — was soll stattdessen dort stehen")

    # F-03
    gesamt = g.noten_menge(str(kopf.get("gesamtnote", "")))
    if kopf and not gesamt:
        b.add("F-03", fall, "fall.json", "keine Gesamtnote gesetzt")
    elif gesamt:
        traeger = [
            s for s in register
            if s.get("notenspanne") and s.get("themenachse") in ("leistung", "verhalten")
        ]
        belegt: set[int] = set()
        for s in traeger:
            belegt |= g.noten_menge(str(s["notenspanne"]))
        if not traeger:
            b.add("F-03", fall, "register.jsonl", "Gesamtnote ohne einen einzigen benoteten Leistungs- oder Verhaltenssatz")
        elif not gesamt & belegt:
            b.add(
                "F-03", fall, "fall.json",
                f"Gesamtnote {sorted(gesamt)} liegt außerhalb der Einzelspannen {sorted(belegt)} — "
                "sie ist nicht aus den Karten hergeleitet",
            )

    # F-04
    kopfdaten = {k: str(v) for k, v in (kopf.get("kopfdaten") or {}).items() if v}
    # Vor dem Vergleich werden Leerzeichen und Zeilenumbrüche normalisiert.
    # Ohne das scheitert jede Kopfdatenprüfung an einem umbrochenen Satz:
    # „als zahnmedizinische\nFachangestellte" enthält die Position, nur nicht
    # als zusammenhängende Zeichenfolge. Im ersten Lauf an echtem Text war das
    # die Ursache aller vier F-04-Meldungen.
    pruefbar = {
        n: LEER.sub(" ", t) for n, t in ausgaben.items() if n in AUSGABEN_MIT_KOPFDATEN
    }
    for feld, wert in kopfdaten.items():
        if not pruefbar:
            continue
        gesucht = LEER.sub(" ", wert)

        if feld in KOPFDATEN_ATOMAR:
            fehlt = [n for n, t in pruefbar.items() if gesucht not in t]
            streng = True
        else:
            # Freitextfeld: es genügt, dass die Kernwörter vorkommen. Gesucht
            # wird nach Inhalt, nicht nach Satzbau.
            kerne = KERNWORT.findall(gesucht)
            fehlt = [
                n for n, t in pruefbar.items()
                if kerne and not all(k in t for k in kerne)
            ]
            streng = False

        if not fehlt:
            continue
        zusatz = "" if streng else " (Kernwörter, nicht wörtlich)"
        if len(fehlt) == len(pruefbar):
            b.add(
                "F-04", fall, feld,
                f"`{wert}` steht in keiner nach außen gehenden Ausgabe{zusatz}",
            )
        else:
            b.add(
                "F-04", fall, feld,
                f"`{wert}` fehlt in {', '.join(sorted(fehlt))} — "
                f"Ausgaben weichen voneinander ab{zusatz}",
            )

    # F-05
    if ziel == "korrektur":
        for n in ("mandant", "gegenseite"):
            if n not in ausgaben:
                b.add("F-05", fall, f"{n}.md", f"fehlt, obwohl das Ziel `korrektur` ist")
    if ziel == "erstellen" and "zeugnis" not in ausgaben:
        b.add("F-05", fall, "zeugnis.md", "fehlt, obwohl das Ziel `erstellen` ist")

    # F-06
    art = kopf.get("zeugnisart")
    status = kopf.get("rechtsstatus_person")
    if art and art not in g.ZEUGNISART:
        b.add("F-06", fall, "fall.json", f"zeugnisart ist `{art}` — erlaubt sind {', '.join(g.ZEUGNISART)}")
    if (status, art) in STATUS_UNVEREINBAR:
        b.add(
            "F-06", fall, "fall.json",
            f"Status `{status}` und Zeugnisart `{art}` passen nicht zusammen — "
            "Anspruchsnorm, Rechtsweg und Kosten hängen daran",
        )
    norm = NORM_ERWARTET.get(art or "")
    if norm and kopf.get("anspruchsnorm") and norm.split()[1] not in str(kopf["anspruchsnorm"]):
        b.add(
            "F-06", fall, "fall.json",
            f"anspruchsnorm `{kopf['anspruchsnorm']}` passt nicht zur Zeugnisart `{art}` (erwartet: {norm})",
        )

    # F-07
    geprueft = {
        str(e.get("norm", "")).strip()
        for e in befunde
        if e.get("frische") == "geprueft" and e.get("norm")
    }
    for name, text in ausgaben.items():
        if name == "zeugnis":
            continue
        # Ein dokumentweiter Vorbehalt deckt das ganze Dokument, auch wenn er
        # am Fuß steht. Die Fenstersuche allein reichte nicht: im zweiten Lauf
        # stand die Fundstelle in Zeile 18 und die Entwurfsnotiz „sämtliche
        # Fundstellen ungeprüft" in Zeile 142 — vierhundert Zeichen Abstand
        # sind für so einen Satz die falsche Maßeinheit.
        global_markiert = any(
            MARKER_UNGEPRUEFT.search(satz) and GLOBAL_BEZUG.search(satz)
            for satz in re.split(r"(?<=[.!?])\s+", text)
        )
        for m in FUNDSTELLE.finditer(text):
            stelle = m.group(0).strip()
            if any(stelle in gp or gp in stelle for gp in geprueft):
                continue
            if global_markiert:
                continue
            absatz = text[max(0, m.start() - 400):m.end() + 400]
            if MARKER_UNGEPRUEFT.search(absatz):
                continue
            b.add(
                "F-07", fall, f"{name}.md",
                f"Fundstelle „{stelle}“ ohne Frische-Nachweis und ohne Kennzeichnung als ungeprüft",
            )

    # F-08
    if kopf and not kopf.get("abdeckung"):
        b.add(
            "F-08", fall, "fall.json",
            "kein Feld `abdeckung` — ob alle Seiten und alle notenrelevanten Sätze erfasst sind, "
            "steht nirgends. Unvollständigkeit liest sich sonst wie Vollständigkeit",
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fall", nargs="*", help="Fall-IDs (Default: alle)")
    p.add_argument("--ziel", help="Ziel überschreiben, statt es aus fall.json zu lesen")
    a = p.parse_args()

    w = g.wurzel()
    ziel = a.fall or g.faelle(w)
    if not ziel:
        g.fehler(f"Keine Fälle unter {w / 'faelle'}")

    b = g.Befunde()
    for fall in ziel:
        pruefen(b, w, fall, a.ziel)

    alle = g.faelle(w)
    zeilen = [
        "# Fertig-Definition",
        "",
        f"Stand: {g.heute()}",
        "",
    ] + g.umfang(w, ziel) + [
        f"- Offene Punkte: {len(b)}",
        "",
        "Der maschinelle Teil der Fertig-Definition. Was hier ohne Befund",
        "durchläuft, ist **nicht** geprüft — nur formal abgeschlossen. Ob der",
        "Zieltext wahr ist und ob er trägt, entscheidet der Belegketten-Durchgang.",
    ]
    if b:
        zeilen += b.zeilen()
    else:
        zeilen += [
            "",
            "---",
            "",
            f"Alle maschinell prüfbaren Bedingungen erfüllt — für die oben genannten "
            f"{len(ziel)} von {len(alle)} Fällen.",
        ]
    zeilen += g.nicht_geprueft_block([
        "**ob ein Zieltext wahr ist** — kein Skript sieht das",
        "**ob ein Befund taktisch trägt** — das entscheidet der Belegketten-Durchgang",
        "**die Schreiben selbst** — Tonlage und Stufenmischung prüft `anspruchsgate.py`",
    ])

    pfad = g.bericht_schreiben(w, "fertig.md", zeilen)
    for regel, gruppe in b.nach_regel().items():
        print(f"  {regel}: {len(gruppe)}")
    if b:
        print(f"NICHT FERTIG → {pfad}")
    else:
        print(f"FORMAL FERTIG für {len(ziel)} von {len(alle)} Fällen → {pfad}")
        print("  Formal heißt: Pflichtfelder und Zuordnungen stimmen. Nicht geprüft:")
        print("  ob ein Zieltext wahr ist und ob er trägt.")
    return 1 if b else 0


if __name__ == "__main__":
    raise SystemExit(main())
