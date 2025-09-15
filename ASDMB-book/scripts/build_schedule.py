#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a single-page schedule with:
  • Week 1 timetable (Mon–Fri, day columns, 30-min rows; colored blocks span duration)
  • Week 2 timetable (Mon–Fri)
  • Details section with MyST anchors (links from grid jump here)

Also injects:
  • Coffee 17:30–18:00 on all days EXCEPT Tuesday of Week 1 and Monday of Week 2
  • Dinner 19:00–20:00 on all days

Input : ASDMB-book/content/data/schedule.yaml
Output: ASDMB-book/content/schedule.md

YAML items (talks/tutorials) may include:
  id, date (YYYY-MM-DD), time ("HH:MM–HH:MM"), title, speaker, room,
  slides_pdf, slides_pptx, slides_html, video, readings (list), abstract

Requires: PyYAML
"""

from __future__ import annotations
import itertools
import pathlib
import re
from datetime import datetime, date, timedelta
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "data" / "schedule.yaml"
OUT  = ROOT / "content" / "schedule.md"

# ---------- time helpers ----------
TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")

def parse_ymd(din) -> date | None:
    if isinstance(din, date):
        return date(din.year, din.month, din.day)
    s = str(din) if din is not None else ""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def hm_to_minutes(hm: str) -> int:
    m = TIME_RE.match(hm)
    if not m:
        raise ValueError(f"Bad time '{hm}' (expected HH:MM)")
    h, mm = int(m.group(1)), int(m.group(2))
    return h * 60 + mm

def parse_time_range(t: str | None) -> tuple[int, int]:
    """Return (start_min, end_min). If no end, assume 30 min."""
    if not t:
        return (0, 0)
    parts = re.split(r"[–-]", str(t))  # en dash or hyphen
    start = hm_to_minutes(parts[0].strip())
    if len(parts) > 1 and parts[1].strip():
        end = hm_to_minutes(parts[1].strip())
    else:
        end = start + 30
    if end < start:
        end = start + 30
    return start, end

def fmt_day(din) -> str:
    d = parse_ymd(din)
    if not d:
        return str(din)
    label = d.strftime("%a, %b %d")
    return label.replace(" 0", " ")

def md_escape(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("|", r"\|")

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ---------- load & normalize ----------
def load_items() -> list[dict]:
    raw = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    talks = raw.get("talks", []) or []
    tuts  = raw.get("tutorials", []) or []

    seen_ids, dup_count = set(), {}

    def norm(item: dict, kind: str) -> dict:
        x = dict(item)
        x["kind"] = kind  # "Talk" / "Tutorial"
        if "author" in x and "speaker" not in x:
            x["speaker"] = x.pop("author")
        d = parse_ymd(x.get("date"))
        if d:
            x["date"] = d.isoformat()
        elif x.get("date") is not None:
            x["date"] = str(x["date"])
        if x.get("time") is not None:
            x["time"] = str(x["time"])
        base = x.get("id") or slugify(x.get("title", "") or "item")
        if base in seen_ids:
            dup_count[base] = dup_count.get(base, 1) + 1
            x["id"] = f"{base}-{dup_count[base]}"
        else:
            x["id"] = base
            seen_ids.add(base)
        s, e = parse_time_range(x.get("time"))
        x["_start_min"] = s
        x["_end_min"] = e
        return x

    items = [norm(i, "Talk") for i in talks] + [norm(i, "Tutorial") for i in tuts]
    items.sort(key=lambda it: (it.get("date", ""), it.get("_start_min", 0)))
    return items

# ---------- weeks: strictly Mon–Fri ----------
def mon_fri_weeks_from(items: list[dict]):
    """Return (week1_items, week2_items, week1_days, week2_days, week1_range, week2_range)."""
    all_dates = sorted({parse_ymd(it.get("date")) for it in items if parse_ymd(it.get("date"))})
    if not all_dates:
        today = date.today()
        w1_mon = today - timedelta(days=today.weekday())
        w1_days = [w1_mon + timedelta(d) for d in range(5)]
        w2_mon = w1_mon + timedelta(days=7)
        w2_days = [w2_mon + timedelta(d) for d in range(5)]
        return items, [], w1_days, w2_days, (w1_mon, w1_mon + timedelta(days=4)), (w2_mon, w2_mon + timedelta(days=4))

    first = all_dates[0]
    w1_mon = first - timedelta(days=first.weekday())  # back to Monday
    w1_days = [w1_mon + timedelta(d) for d in range(5)]
    w2_mon = w1_mon + timedelta(days=7)
    w2_days = [w2_mon + timedelta(d) for d in range(5)]

    def in_days(it, days_list):
        d = parse_ymd(it.get("date"))
        return d in set(days_list)

    week1 = [it for it in items if in_days(it, w1_days)]
    week2 = [it for it in items if in_days(it, w2_days)]

    return week1, week2, w1_days, w2_days, (w1_mon, w1_mon + timedelta(days=4)), (w2_mon, w2_mon + timedelta(days=4))

# ---------- inject coffee + dinner ----------
def add_breaks(items: list[dict], w1_days, w2_days):
    def inject(d: date, time: str, title: str, kind: str, id_prefix: str):
        s, e = parse_time_range(time)
        items.append({
            "id": f"{id_prefix}-{d.isoformat()}",
            "date": d.isoformat(),
            "time": time,
            "title": "",
            "speaker": title,
            "kind": kind,
            "_start_min": s,
            "_end_min": e,
        })

    # Week 1: coffee every weekday EXCEPT Tuesday
    for d in w1_days:
        if d.weekday() not in [0, 1]:  # 0=Mon, 1=Tue, ...
            if d.weekday() == 2:
                inject(d, "17:30–18:00", "Coffee", "Break", "coffee")
            else:
                inject(d, "17:30–18:00", "", "Break", "coffee")

    # Week 2: coffee every weekday EXCEPT Monday
    for d in w2_days:
        if d.weekday() != 0:
            if d.weekday() == 1:
                inject(d, "17:30–18:00", "Coffee", "Break", "coffee")
            else:
                inject(d, "17:30–18:00", "", "Break", "coffee")

    # Dinner every weekday in both weeks
    for d in w1_days:
        if d.weekday() != 0:
            if d.weekday() == 1:
                inject(d, "19:00–20:00", "Dinner", "Break", "dinner")
            else:
                inject(d, "19:00–20:00", "", "Break", "dinner")
    for d in w2_days:
        if d.weekday() == 0:
            inject(d, "19:00–20:00", "Dinner", "Break", "dinner")
        else:
            inject(d, "19:00–20:00", "", "Break", "dinner")

    items.sort(key=lambda it: (it.get("date", ""), it.get("_start_min", 0)))

# ---------- 30-min slot grid ----------
def compute_time_slots(items_for_week: list[dict]) -> list[int]:
    if not items_for_week:
        return []
    min_s = min(it["_start_min"] for it in items_for_week)
    max_e = max(it["_end_min"] for it in items_for_week)
    def snap_down(m): return m - (m % 30)
    def snap_up(m):   return m if m % 30 == 0 else m + (30 - (m % 30))
    cur, end = snap_down(min_s), snap_up(max_e)
    slots = []
    while cur < end:
        slots.append(cur)
        cur += 30
    return slots

def minutes_to_hm(m: int) -> str:
    h, mm = divmod(m, 60)
    return f"{h:02d}:{mm:02d}"

def split_names(s: str) -> list[str]:
    import re
    if not s:
        return []
    parts = re.split(r"\s*(?:,| & | and )\s*", s)
    return [p for p in (p.strip() for p in parts) if p]

# ---------- table builder ----------
def build_overview_grid(items_for_week: list[dict], days_list: list[date]) -> list[str]:
    """Build an HTML timetable (Mon–Fri columns, 30-min rows) and add kind/segment classes to <td>."""
    dates = [d.isoformat() for d in days_list]
    slots = compute_time_slots(items_for_week)

    # index by (date_iso, slot_start_min) -> items overlapping
    by_d_slot = {(d, s): [] for d in dates for s in slots}
    for it in items_for_week:
        d = it["date"]
        s0, e0 = it["_start_min"], it["_end_min"]
        for s in slots:
            if s >= e0 or (s + 30) <= s0:
                continue
            if (d, s) in by_d_slot:
                by_d_slot[(d, s)].append(it)

    def kind_classes(items_here: list[dict]) -> str:
        kinds = { (it.get("kind") or "").lower() for it in items_here }
        return " ".join(sorted(f"kind-{k}" for k in kinds if k))

    def seg_class(items_here: list[dict], s: int) -> str:
        starters = [it for it in items_here if it["_start_min"] == s]
        enders   = [it for it in items_here if it["_end_min"] == s + 30]
        # single-slot if the only item here starts and ends in this slot
        if len(items_here) == 1 and starters and enders:
            return "seg-single"
        if starters and enders:
            # mixed case (overlap): mark both; CSS can handle both present
            return "seg-start seg-end"
        if starters:
            return "seg-start"
        if enders:
            return "seg-end"
        return "seg-mid"

    lines = []
    lines.append('<table class="schedule">')
    lines.append("<thead>")
    head_cells = ["<th class='time'>Time</th>"] + [f"<th>{fmt_day(d)}</th>" for d in dates]
    lines.append("<tr>" + "".join(head_cells) + "</tr>")
    lines.append("</thead>")

    lines.append("<tbody>")
    for s in slots:
        row = [f"<th class='time'>{minutes_to_hm(s)}</th>"]
        for d in dates:
            items_here = by_d_slot.get((d, s), [])
            if not items_here:
                row.append("<td class='slot'>&nbsp;</td>")
                continue

            td_classes = f"slot {kind_classes(items_here)} {seg_class(items_here, s)}"

            starters = [it for it in items_here if it["_start_min"] == s]
            if starters:
                labels = []
                for it in starters:
                    title  = md_escape(it.get("title", "").strip())
                    spk    = md_escape(it.get("speaker", "").strip())
                    kind   = (it.get("kind") or "").strip()
                    anchor = it["id"]
                    if kind.lower() == "break" or kind.lower() == "dinner":
                        label_html = spk or ""
                    else:
                        label_html = f'<a href="#{anchor}">{title}</a>' + (f" ({spk})" if spk else "")
                    labels.append(f"<div class='label'>{label_html}</div>")
                row.append(f"<td class='{td_classes}'>" + "".join(labels) + "</td>")
            else:
                row.append(f"<td class='{td_classes}'>&nbsp;</td>")
        lines.append("<tr>" + "".join(row) + "</tr>")
    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("")
    return lines


# ---------- details ----------
def build_details(items_all: list[dict]) -> list[str]:
    # group by kind (lectures then tutorials) then by date
    items_all = sorted(items_all, key=lambda it: (it.get("kind", ""), it.get("date", ""), it.get("_start_min", 0)))
    lines: list[str] = []
    for date_key, group in itertools.groupby(items_all, key=lambda x: x.get("date", "")):
        # lines += [f"### {fmt_day(date_key)}", ""]
        for it in group:
            anchor = it["id"]
            title  = md_escape(it.get("title", ""))

            spk_raw = it.get("speaker", "") or ""

            names = split_names(spk_raw)

            spk_links = " · ".join(
                f"<a href='speakers.html#speaker-{slugify(n)}'>{md_escape(spk_raw)}</a>" if n else "" for n in names
            )

            kind = it.get("kind", "")
            if kind == "Break":
                continue

             # fix: list, not tuple
            lines += [f"({anchor})=", ""]  # MyST anchor for the talk
            title_esc = md_escape(title)
            if spk_links:
                lines += [f"#### {spk_links} : {title_esc}", ""]
            else:
                # Fallback if no speaker names
                spk_esc = md_escape(spk_raw)
                lines += [f"#### {spk_esc} : {title_esc}", ""]

            slides = []
            for key, label in [("slides_pdf", "PDF"), ("slides_pptx", "PowerPoint"), ("slides_html", "HTML")]:
                if it.get(key):
                    slides.append(f"[{label}]({it[key]})")
            if slides:
                lines += ["**Slides:** " + " · ".join(slides), ""]

            if it.get("video"):
                lines += [f"**Recording:** {it['video']}", ""]

            if isinstance(it.get("readings"), list) and it["readings"]:
                lines += ["**Readings:**"]
                for r in it["readings"]:
                    lines += [f"- {r}"]
                lines += [""]

            if it.get("abstract"):
                lines += ["**Abstract:**", it["abstract"], ""]
            lines += ["<hr>", ""]
        lines += [""]
    return lines

# ---------- main ----------
def main() -> None:
    items = load_items()

    # Build week ranges (Mon–Fri) then inject breaks for those days only
    w1_items, w2_items, w1_days, w2_days, w1_range, w2_range = mon_fri_weeks_from(items)
    add_breaks(items, w1_days, w2_days)

    # Rebuild week subsets after injection
    w1_items, w2_items, w1_days, w2_days, w1_range, w2_range = mon_fri_weeks_from(items)

    lines: list[str] = []
    lines += ["# Schedule", ""]

    # Week 1 grid
    w1_mon, w1_fri = w1_range
    lines += [f"## Week 1: Basics",
              "",
              "<div class='hint-wrapper'>"
              "<div class='color-hint lectures'>Lectures</div>"
              "<div class='color-hint practical'>Practical Session</div>"
              "<div class='color-hint break'>Coffee/Dinner</div>"
              "</div>",
              ""]
    lines += build_overview_grid(w1_items, w1_days) if w1_items else ["_No sessions in Week 1._", ""]

    # Week 2 grid
    if w2_items:
        w2_mon, w2_fri = w2_range
        lines += [f"## Week 2: Model Discovery and LLMs", ""]
        lines += build_overview_grid(w2_items, w2_days)

    # Details (show everything, including any items outside the two Mon–Fri weeks)
    lines += ["---", ""]
    # Sort everything chronologically for details
    items.sort(key=lambda it: (it.get("date", ""), it.get("_start_min", 0)))
    lines += build_details(items)

    OUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
