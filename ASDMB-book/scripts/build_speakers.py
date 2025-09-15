#!/usr/bin/env python3
from __future__ import annotations
import pathlib, yaml, re
from datetime import datetime, date

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "content" / "data" / "schedule.yaml"
SPEAKERS = ROOT / "content" / "data" / "speakers.yaml"
OUT = ROOT / "content" / "speakers.md"

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def parse_ymd(s: str) -> date | None:
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception: return None

def load_schedule():
    raw = yaml.safe_load(SCHEDULE.read_text(encoding="utf-8")) or {}
    items = []
    for kind_key, kind in (("talks","Talk"),("tutorials","Tutorial")):
        for it in raw.get(kind_key, []) or []:
            if not it: continue
            d = str(it.get("date","")).strip()
            t = str(it.get("time","")).strip()
            title = str(it.get("title","")).strip()
            spk = str(it.get("speaker", it.get("author",""))).strip()
            if not (d and t and title): continue
            items.append({
                "id": it.get("id") or slugify(title) or f"{kind.lower()}",
                "date": d, "time": t, "title": title,
                "speaker": spk, "kind": kind
            })
    # sort by date/time
    def sortkey(x):
        dt = parse_ymd(x["date"]) or date(2100,1,1)
        return (dt.isoformat(), x["time"])
    items.sort(key=sortkey)
    return items

def split_names(s: str) -> list[str]:
    if not s: return []
    # split on commas and &/and
    parts = re.split(r"\s*(?:,| & | and )\s*", s)
    return [p for p in (p.strip() for p in parts) if p]

def load_speakers_registry():
    data = yaml.safe_load(SPEAKERS.read_text(encoding="utf-8")) if SPEAKERS.exists() else {}
    listed = {}
    by_alias = {}
    for sp in (data.get("speakers") or []):
        sp = dict(sp)
        sp_id = sp.get("id") or slugify(sp.get("name",""))
        sp["id"] = sp_id
        listed[sp_id] = sp
        names = [sp.get("name","")] + list(sp.get("aliases") or [])
        for n in names:
            key = slugify(n)
            if key: by_alias[key] = sp_id
    return listed, by_alias

def ensure_dir(p: pathlib.Path): p.parent.mkdir(parents=True, exist_ok=True)

def main():
    items = load_schedule()
    listed, by_alias = load_speakers_registry()

    # sessions per speaker_id
    sessions = {}
    # auto-create minimal speaker entries if not in registry
    autos = {}

    for it in items:
        for name in split_names(it["speaker"]):
            key = slugify(name)
            sp_id = by_alias.get(key)
            if not sp_id:
                sp_id = f"speaker-{key}"
                if sp_id not in autos:
                    autos[sp_id] = {"id": sp_id, "name": name, "affiliation": "", "photo": "", "bio": ""}
            sessions.setdefault(sp_id, []).append(it)

    # Merge defined + auto
    def all_speakers():
        # prefer defined ordering (by name), then autos (alpha)
        defined = sorted(listed.values(), key=lambda s: s.get("name","").lower())
        missing = [autos[k] for k in sorted(autos)]
        return defined + missing

    lines = []
    lines += ["# Speakers", ""]
    lines += ["Below are speakers in alphabetical order. Click a title to jump to the talk in the [Schedule](../schedule.md).", ""]

    # Nice grid of cards
    lines += ['<div class="speakers-grid">', ""]

    for sp in all_speakers():
        sp_id = sp["id"]
        name = sp.get("name","")
        aff  = sp.get("affiliation","")
        web  = sp.get("website","")
        photo= sp.get("photo","")
        bio  = sp.get("bio","")

        anchor = f"(speaker-{slugify(name)})="
        # anchor line
        lines += [anchor, ""]
        lines += [f'### {name}']
        # card
        lines += ['<div class="speaker-card">']
        if photo:
            lines += [f'  <img class="speaker-photo" src="{photo}" alt="{name}"/>']
        else:
            initials = "".join([w[0].upper() for w in name.split()[:2] if w])
            lines += [f'  <div class="speaker-photo placeholder">{initials or "?"}</div>']
        if aff:
            lines += [f'  <div class="speaker-aff">{aff}</div>']
        if bio:
            lines += [f'  <p class="speaker-bio">{bio}</p>']
        if web:
            lines += [f'  <div class="speaker-web"><a href="{web}">{web}</a></div>']

        # sessions list
        sess = sessions.get(sp_id, [])
        if not sess:
            # try name-key fallback (for defined speakers whose aliases didn't match exactly)
            sess = sessions.get(f"speaker-{slugify(name)}", [])
        if sess:
            lines += ['  <ul class="speaker-sessions">']
            for si in sess:
                date_txt = si["date"]
                label = f'{si["title"]} ({si["kind"]}, {si["time"]})'
                lines += [f'    <li><a href="schedule.html#{si["id"]}">{label}</a></li>']
            lines += ['  </ul>']
        lines += ['</div>', ""]  # end card
        lines += ["<hr>", ""]

    lines += ["</div>", ""]  # end grid

    ensure_dir(OUT)
    OUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
