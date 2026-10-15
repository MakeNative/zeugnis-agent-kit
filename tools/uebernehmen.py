#!/usr/bin/env python3
"""Übernimmt einen Agentenbericht wortgleich in die Fallakte.

    uebernehmen.py <fall-id> <bericht.md> [--trocken]

Die Agenten dieses Kits haben keine Schreibrechte (P-03): sie lesen fremden
Text und geben einen Bericht zurück. Bisher musste die Skill daraus die
JSONL-Dateien von Hand aufbauen — bei einem Zeugnis rund hundert Zeilen.

Das war zweifach schlecht. Erstens unbenutzbar: wer einen echten Fall
bearbeitet, tippt keine hundert Karten ab. Zweitens die Stelle, an der
Orchestrator-Wissen in die Daten sickert — wer eine Note beim Übertragen in
der Hand hält, kann sie anfassen.

Dieses Skript trennt beides. Die Skill kopiert den Bericht **unverändert**
nach `faelle/<fall>/berichte/<agent>.md`; das ist eine Kopie, keine
Umformung. Die Umformung macht dann dieses Skript, und es kann nicht urteilen.

Erkannt wird am Inhalt, nicht an einer Angabe:
  Objekte mit `satz_id`   → `register.jsonl`
  Objekte mit `befund_id` → `befunde.jsonl`
  `GESAMTNOTE:` / `ABDECKUNG:` / `GETRAGEN VON:` → `fall.json`

Bestehende Einträge werden ergänzt, nicht ersetzt: der `noten-bewerter`
liefert zu einer Karte des `satz-leser` nur die Bewertungsfelder. Ändert ein
späterer Bericht einen schon erfassten `wortlaut`, ist das ein **Konflikt**
und wird gemeldet statt still übernommen (Z-02) — zwei Agenten, die denselben
Satz verschieden zitieren, sind ein Befund, keine Formalie.

Exit 0 wenn übernommen, 1 bei Konflikten, 2 bei Abbruch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gemeinsam as g  # noqa: E402

# Eine JSON-Zeile kann eingerückt sein, in einem Codefence stehen oder hinter
# einem Listenstrich. Alles andere als der Objektrumpf wird verworfen.
JSON_ZEILE = re.compile(r"^\s*(?:[-*]\s*)?(\{.*\})\s*,?\s*$")
KOPFFELD = re.compile(
    r"^\s*(GESAMTNOTE|ABDECKUNG|GETRAGEN VON|ZEUGNISART|QUELLE|LESBAR)\s*:\s*(.+?)\s*$",
    re.M | re.I,
)
# Felder, die nur die Skill setzt. Ein Agent, der sie mitschickt, wird
# übergangen — sonst bestimmt ein Subagent die Fallsteuerung (P-02).
NUR_SKILL = {"fall_id", "ziel", "rechtsstatus_person", "anspruchsnorm", "kopfdaten"}


def json_objekte(text: str) -> list[dict]:
    """Zieht alle JSON-Objekte zeilenweise aus dem Bericht.

    Zeilenweise und nicht über einen Parser, weil der Bericht Prosa, Tabellen
    und Codefences mischt. Eine kaputte Zeile wird gemeldet und übersprungen;
    sie darf den Rest nicht verhindern.
    """
    objekte, kaputt, abgeschnitten = [], [], []
    for nr, zeile in enumerate(text.splitlines(), 1):
        m = JSON_ZEILE.match(zeile)
        if not m:
            # Eine Zeile, die mit `{` beginnt und nicht als Objekt endet, ist
            # fast immer ein abgebrochener Bericht — der Agent ist mitten in
            # der Ausgabe gestorben. Das darf nicht wie Prosa durchlaufen
            # (P-07): ein Teilergebnis ist kein Ergebnis.
            if re.match(r"^\s*(?:[-*]\s*)?\{", zeile):
                abgeschnitten.append(nr)
            continue
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            kaputt.append((nr, e.msg))
            continue
        if isinstance(d, dict) and ("satz_id" in d or "befund_id" in d):
            objekte.append(d)

    for nr, msg in kaputt:
        g.warnung(f"Bericht Zeile {nr}: kein gültiges JSON ({msg}) — übersprungen")
    if abgeschnitten:
        g.warnung(
            f"Bericht Zeile(n) {', '.join(map(str, abgeschnitten))}: beginnt mit `{{`, "
            "endet aber nicht als Objekt — vermutlich abgebrochener Bericht. "
            "Nach P-07 zählt das nicht als „nichts gefunden“: Agenten einmal neu "
            "starten und erst beim zweiten Fehlschlag als unerledigt melden."
        )
    return objekte


def zusammenfuehren(
    vorhanden: list[dict], neu: list[dict], schluessel: str
) -> tuple[list[dict], int, int, list[str]]:
    """Ergänzt bestehende Einträge und hängt neue an.

    Gibt (ergebnis, ergaenzt, angehaengt, konflikte) zurück. Die Reihenfolge
    der vorhandenen Einträge bleibt erhalten — Satz-IDs sind stabil und sollen
    in der Datei auch stabil stehen.
    """
    karte = {d[schluessel]: dict(d) for d in vorhanden if schluessel in d}
    reihenfolge = [d[schluessel] for d in vorhanden if schluessel in d]
    ergaenzt = angehaengt = 0
    konflikte: list[str] = []

    for d in neu:
        sid = d.get(schluessel)
        if not sid:
            continue
        if sid not in karte:
            karte[sid] = {k: v for k, v in d.items() if k not in NUR_SKILL}
            reihenfolge.append(sid)
            angehaengt += 1
            continue

        alt = karte[sid]

        # Z-02: weicht der Originalwortlaut ab, wird die Karte **ganz**
        # verworfen, nicht nur das Wortlautfeld. Wer „Sie war bemüht" statt
        # „Sie war stets bemüht" zitiert, hat auch die Note auf dem falschen
        # Satz gebildet — zwischen den beiden liegen Notenstufen. Die übrigen
        # Felder mitzunehmen würde den Fehler in die Bewertung tragen und
        # dort unsichtbar machen.
        neuer_wortlaut = d.get("wortlaut")
        if neuer_wortlaut and alt.get("wortlaut") and alt["wortlaut"] != neuer_wortlaut:
            konflikte.append(
                f"{sid}: wortlaut weicht ab — Karte verworfen\n"
                f"      in der Akte: {alt['wortlaut'][:90]}\n"
                f"      im Bericht:  {str(neuer_wortlaut)[:90]}"
            )
            continue

        geaendert = False
        for feld, wert in d.items():
            if feld in NUR_SKILL or alt.get(feld) == wert:
                continue
            alt[feld] = wert
            geaendert = True
        if geaendert:
            ergaenzt += 1

    return [karte[s] for s in reihenfolge], ergaenzt, angehaengt, konflikte


def schreiben(datei: Path, zeilen: list[dict]):
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in zeilen) + "\n",
        encoding="utf-8",
    )


def kopffelder(text: str, fall_datei: Path, trocken: bool) -> list[str]:
    """Übernimmt Gesamtnote und Abdeckung in `fall.json`.

    `ABDECKUNG` ist Pflicht nach P-06 und steht im Bericht des `satz-leser`;
    sie dort zu lassen, wäre genau das stille Kürzen, das die Regel verbietet.
    """
    treffer = {m.group(1).upper(): m.group(2).strip() for m in KOPFFELD.finditer(text)}
    uebernahme = {}
    if "GESAMTNOTE" in treffer:
        uebernahme["gesamtnote"] = treffer["GESAMTNOTE"]
    if "ABDECKUNG" in treffer:
        uebernahme["abdeckung"] = treffer["ABDECKUNG"]
    if "GETRAGEN VON" in treffer:
        uebernahme["gesamtnote_getragen_von"] = treffer["GETRAGEN VON"]
    if not uebernahme:
        return []

    if not trocken:
        d = json.loads(fall_datei.read_text(encoding="utf-8")) if fall_datei.is_file() else {}
        d.update(uebernahme)
        fall_datei.write_text(
            json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return [f"{k} = {v[:70]}" for k, v in uebernahme.items()]


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("fall", help="Fall-ID, z. B. blind-05")
    p.add_argument("bericht", type=Path, help="Datei mit dem wortgleichen Agentenbericht")
    p.add_argument("--trocken", action="store_true", help="nur zeigen, nichts schreiben")
    a = p.parse_args()

    w = g.wurzel()
    ordner = g.fall_pfad(w, a.fall)
    if not a.bericht.is_file():
        g.fehler(f"`{a.bericht}` nicht gefunden")

    text = a.bericht.read_text(encoding="utf-8")
    objekte = json_objekte(text)
    saetze = [d for d in objekte if "satz_id" in d]
    befunde = [d for d in objekte if "befund_id" in d and "satz_id" not in d]

    print(f"Fall:    {a.fall}")
    print(f"Bericht: {a.bericht.name}  ({len(text.splitlines())} Zeilen)")
    print(f"Gefunden: {len(saetze)} Satzkarten, {len(befunde)} Befunde")
    if not saetze and not befunde:
        g.fehler(
            "Keine JSON-Objekte mit `satz_id` oder `befund_id` im Bericht. "
            "Entweder ist es der falsche Bericht, oder der Agent hat sein "
            "Ergebnisformat nicht eingehalten — dann ist der Lauf unvollständig "
            "und zählt nicht als „nichts gefunden\" (P-07)."
        )

    konflikte: list[str] = []
    for liste, name, schluessel in (
        (saetze, "register.jsonl", "satz_id"),
        (befunde, "befunde.jsonl", "befund_id"),
    ):
        if not liste:
            continue
        datei = ordner / name
        ergebnis, ergaenzt, angehaengt, konf = zusammenfuehren(
            g.jsonl_lesen(datei), liste, schluessel
        )
        konflikte += konf
        print(f"  {name:16} {angehaengt} neu, {ergaenzt} ergänzt, {len(ergebnis)} gesamt")
        if not a.trocken:
            schreiben(datei, ergebnis)

    for zeile in kopffelder(text, ordner / "fall.json", a.trocken):
        print(f"  fall.json        {zeile}")

    if konflikte:
        print(f"\nKONFLIKTE: {len(konflikte)}", file=sys.stderr)
        for k in konflikte:
            print(f"  {k}", file=sys.stderr)
        print(
            "\nDer Originalwortlaut wurde NICHT überschrieben (Z-02). Zwei Agenten,\n"
            "die denselben Satz verschieden zitieren, sind ein Befund: einer hat\n"
            "abgetippt statt kopiert, oder die Satz-IDs sind verschoben. Kläre das\n"
            "am Dokument, bevor der Fall weiterläuft.",
            file=sys.stderr,
        )
        return 1

    if a.trocken:
        print("\nTrockenlauf — nichts geschrieben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
