#!/usr/bin/env python3
"""Workout Dashboard Generator v7"""

import re, json, os
from datetime import datetime
from collections import Counter

# ── Default config (used when config.json is absent) ─────────────────────────
DEFAULT_CONFIG = {
    "dashboard_title": "Workout",
    "annual_target": 250,
    "github_url": "https://github.com/wenqingchen-makes/workout-dashboard",
    "categories": {
        "Pilates & Yoga": {
            "keywords": ["pilates","reformer","yoga","moreyoga","barre","flow ldn",
                         "tempo pilates","vinyasa","hot yoga","strength pilates","chill"],
            "color": "#2D6A4F"
        },
        "Ride":    {"keywords":["ride"], "color":"#1A3A5C"},
        "Tennis":  {"keywords":["tennis","court","🎾","网球"], "color":"#B5451B"},
        "Gym":     {"keywords":["gym","bodypump","bodycombat","hyrox","strength & conditioning",
                                 "functional fitness","boxfit","power pump","studio strength",
                                 "crossfit","健身房","运动","wicked shapes","body conditioning",
                                 "circuit","fantastic physiques","blockhouse"],
                    "color":"#4A4A4A"},
        "Hiking":  {"keywords":["hiking","hike","徒步"], "color":"#1D6FA4"},
        "Dance":   {"keywords":["zumba","dance","salsa","fitbounce","step aerobics",
                                 "legs bums","legs, bums","bums and tums"],
                    "color":"#6B4FA0"},
        "Swimming":{"keywords":["swim"], "color":"#0A7E8C"},
        "Squash":  {"keywords":["squash"], "color":"#8B6914"},
        "Bouldering":{"keywords":["bouldering","boulder","climbing","抱石"], "color":"#8B4513"},
    }
}

def load_config(script_dir):
    cfg_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(cfg_path):
        print("  Note: config.json not found — using built-in defaults.")
        print("  Create config.json to customise categories and targets.\n")
        return DEFAULT_CONFIG
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg: cfg[k] = v
    print(f"  Config: {cfg_path}")
    return cfg

def classify(summary, categories):
    s = summary.lower()
    for cat, info in categories.items():
        for kw in info.get("keywords", []):
            if kw.lower() in s: return cat
    return None

def unfold(text): return re.sub(r"\r?\n[ \t]", "", text)

def parse_dt(v, _):
    v = v.strip()
    try:
        return datetime.strptime(v.rstrip("Z"), "%Y%m%dT%H%M%S") if "T" in v else datetime.strptime(v, "%Y%m%d")
    except ValueError: return None

def parse_ics(filepath):
    with open(filepath, encoding="utf-8") as f: raw = f.read()
    text = unfold(raw)
    events = []
    for block in re.split(r"BEGIN:VEVENT", text)[1:]:
        end = block.find("END:VEVENT")
        if end != -1: block = block[:end]
        def get(key):
            m = re.search(rf"^{key}(?:;[^\n:]*)?:(.+)$", block, re.MULTILINE)
            return m.group(1).strip() if m else None
        def gwp(key):
            m = re.search(rf"^({key}(?:;[^\n:]*)?):(.*?)$", block, re.MULTILINE)
            if not m: return None, None
            tzm = re.search(r"TZID=([^;:]+)", m.group(1))
            return m.group(2).strip(), (tzm.group(1) if tzm else None)
        summary = get("SUMMARY")
        if not summary: continue
        sv, _ = gwp("DTSTART"); ev, _ = gwp("DTEND")
        dtstart = parse_dt(sv, None) if sv else None
        dtend   = parse_dt(ev, None) if ev else None
        if dtstart is None: continue
        dur = None
        if dtend:
            d = int((dtend - dtstart).total_seconds() / 60)
            if d > 0: dur = d
        events.append({"summary": summary, "date": dtstart.date().isoformat(),
                        "dtstart": dtstart.isoformat(), "duration_min": dur})
    return events

def load_all_events(data_dir):
    evs = []
    for f in os.listdir(data_dir):
        if f.endswith(".ics"):
            try: evs.extend(parse_ics(os.path.join(data_dir, f)))
            except Exception as e: print(f"  Warning: {f}: {e}")
    return evs

def deduplicate(events):
    seen = {}
    for ev in events:
        k = (ev["date"], ev["summary"].strip().lower())
        if k not in seen or (seen[k]["duration_min"] is None and ev["duration_min"] is not None):
            seen[k] = ev
    return list(seen.values())

def process_events(events, categories):
    result, unmatched = [], []
    for ev in events:
        cat = classify(ev["summary"], categories)
        if cat: result.append(dict(**ev, category=cat))
        else: unmatched.append(ev["summary"])
    if unmatched:
        print("\nUnmatched (skipped) events:")
        for s, c in Counter(unmatched).most_common():
            print(f"  {c}x  {s}")
    return result

# ─────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__DASHBOARD_TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0F0F0F;--surf:#1A1A1A;--surf2:#222;--bdr:#2A2A2A;
  --text:#FFF;--muted:#9A9A9A;--faint:#1E1E1E;--accent:#E8431A;
  --r:4px;--max-w:1200px;--pad:32px;
}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",sans-serif;
     background:var(--bg);color:var(--text);font-size:15px;line-height:1.6;min-height:100vh;
     background-image:linear-gradient(rgba(42,42,42,.18) 1px,transparent 1px),
       linear-gradient(90deg,rgba(42,42,42,.18) 1px,transparent 1px);
     background-size:40px 40px}
canvas{background:#1A1A1A;border-radius:var(--r)}

/* ── Landing Page ── */
#landing{position:fixed;inset:0;z-index:9000;background:#0A0A0A;display:flex;
         flex-direction:column;align-items:center;justify-content:center;
         overflow:hidden;transition:opacity .6s ease,transform .6s ease}
#landing.out{opacity:0;transform:scale(1.02);pointer-events:none}
.land-mtn{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;
           transition:transform .1s linear}
.land-content{position:relative;z-index:1;text-align:center;padding:0 24px;max-width:720px}
.land-h1{font-size:72px;font-weight:900;color:#fff;letter-spacing:-3px;line-height:1.05;
          opacity:0;animation:landIn .7s cubic-bezier(.16,1,.3,1) forwards .2s}
.land-sub{font-size:18px;color:#6B6B6B;max-width:520px;margin:18px auto 0;
           opacity:0;animation:landIn .7s cubic-bezier(.16,1,.3,1) forwards .4s}
.land-btns{display:flex;gap:14px;justify-content:center;margin-top:36px;flex-wrap:wrap;
            opacity:0;animation:landIn .7s cubic-bezier(.16,1,.3,1) forwards .6s}
.land-btn{padding:13px 28px;background:var(--accent);border:none;border-radius:var(--r);
          font-size:15px;font-weight:600;color:#fff;cursor:pointer;transition:transform .15s,opacity .15s}
.land-btn:hover{transform:translateY(-2px);opacity:.9}
.land-btn-out{padding:13px 28px;background:none;border:1px solid rgba(255,255,255,.25);
              border-radius:var(--r);font-size:15px;font-weight:500;color:rgba(255,255,255,.7);
              cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;
              transition:border-color .15s,color .15s}
.land-btn-out:hover{border-color:rgba(255,255,255,.6);color:#fff}
.land-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:56px;
             opacity:0;animation:landIn .7s cubic-bezier(.16,1,.3,1) forwards .8s}
.land-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
            border-radius:8px;padding:22px 18px;text-align:left}
.land-card-icon{font-size:22px;margin-bottom:10px}
.land-card-title{font-size:13px;font-weight:600;color:#fff;margin-bottom:4px}
.land-card-desc{font-size:12px;color:#6B6B6B;line-height:1.5}
.land-footer{position:absolute;bottom:28px;left:0;right:0;text-align:center;
              font-size:12px;color:rgba(255,255,255,.25);z-index:1;
              opacity:0;animation:landIn .6s ease forwards 1s}
@keyframes landIn{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@media(max-width:600px){
  .land-h1{font-size:44px}
  .land-cards{grid-template-columns:1fr}
}

/* ── Layout ── */
.wrap{max-width:var(--max-w);margin:0 auto;padding:0 var(--pad)}

/* ── Hero ── */
.hero{background:#0A0A0A;border-bottom:1px solid var(--bdr)}
.hero-top{display:flex;align-items:center;justify-content:space-between;padding:22px 0 0;gap:16px}
.logo{font-size:15px;font-weight:700;color:#fff;letter-spacing:-.3px}
.hero-body{display:flex;align-items:stretch;margin:20px 0;
           border:1px solid rgba(255,255,255,.07);border-radius:var(--r);overflow:hidden}
.hero-main{display:grid;grid-template-columns:repeat(4,1fr);flex:1;
           gap:1px;background:rgba(255,255,255,.06)}
.h-card{background:#0A0A0A;padding:26px 26px 22px;opacity:0;cursor:default;
        animation:cardUp .55s cubic-bezier(.16,1,.3,1) forwards;
        transition:transform .2s ease,background .2s ease}
.h-card:hover{transform:translateY(-3px);background:#111}
.h-card:nth-child(1){animation-delay:.18s}.h-card:nth-child(2){animation-delay:.3s}
.h-card:nth-child(3){animation-delay:.42s}.h-card:nth-child(4){animation-delay:.54s}
@keyframes cardUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.h-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
         color:rgba(255,255,255,.38);margin-bottom:10px}
.h-val{font-size:60px;font-weight:700;color:#fff;letter-spacing:-3px;line-height:1;
       font-variant-numeric:tabular-nums}
.h-val.sm{font-size:22px;letter-spacing:-.5px}
.hero-30{background:#0A0A0A;border-left:1px solid rgba(255,255,255,.07);
         padding:24px 28px;min-width:190px;display:flex;flex-direction:column;
         justify-content:center;gap:14px;flex-shrink:0;
         animation:cardUp .55s cubic-bezier(.16,1,.3,1) forwards .66s;opacity:0}
.h30-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
           color:var(--accent);margin-bottom:4px}
.h30-num{font-size:28px;font-weight:700;color:#fff;letter-spacing:-1px;line-height:1}
.h30-sub{font-size:11px;color:rgba(255,255,255,.38);margin-top:2px}

/* ── Tabs ── */
.tabs-bar{background:var(--surf);border-bottom:1px solid var(--bdr);position:sticky;top:0;z-index:100}
.tabs-inner{max-width:var(--max-w);margin:0 auto;padding:0 var(--pad);display:flex;position:relative}
.tab-btn{background:none;border:none;position:relative;padding:16px 20px 15px;
         font-size:14px;font-weight:500;color:var(--muted);cursor:pointer;
         transition:color .15s;white-space:nowrap}
.tab-btn:first-child{padding-left:0}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--text)}
#tabInd{position:absolute;bottom:0;left:0;height:2px;background:var(--accent);
        border-radius:1px;transition:left .3s cubic-bezier(.4,0,.2,1),width .3s cubic-bezier(.4,0,.2,1);
        pointer-events:none}

/* ── Tab panes ── */
.tab-pane{display:none}
.tab-pane.active{display:block}

/* ── Shared ── */
.sec-row{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px}
.sec-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.range-desc{font-size:12px;color:#6B6B6B;margin-top:6px;letter-spacing:.01em}
#granToggle{display:none}
.chart-box{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
           padding:20px;margin-bottom:28px}
.toggle-grp{display:flex;gap:2px;background:var(--bg);border:1px solid var(--bdr);
            border-radius:var(--r);padding:3px}
.toggle-grp button{background:none;border:none;padding:4px 11px;font-size:12px;color:var(--muted);
                   cursor:pointer;border-radius:3px;white-space:nowrap;transition:all .15s}
.toggle-grp button.active{background:var(--surf);color:var(--text);font-weight:500}
.toggle-grp button:hover:not(.active){color:var(--text)}

/* Time range strip */
.tr-strip{display:flex;gap:2px;background:var(--bg);border:1px solid var(--bdr);
          border-radius:var(--r);padding:3px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tr-strip::-webkit-scrollbar{display:none}
.tr-strip button{background:none;border:none;padding:4px 11px;font-size:12px;color:var(--muted);
                 cursor:pointer;border-radius:3px;white-space:nowrap;transition:all .15s}
.tr-strip button.active{background:var(--surf);color:var(--text);font-weight:500}
.tr-strip button:hover:not(.active){color:var(--text)}
.custom-row{display:none;align-items:center;gap:8px;padding:10px 0;flex-wrap:wrap;
            border-top:1px solid var(--bdr);margin-top:10px}
.custom-row.show{display:flex}
.custom-row label{font-size:12px;color:var(--muted)}
.custom-row input[type="date"]{background:var(--surf2);border:1px solid var(--bdr);
  border-radius:var(--r);padding:4px 8px;font-size:12px;color:var(--text);color-scheme:dark;outline:none}
.custom-apply{padding:5px 14px;background:var(--accent);border:none;border-radius:var(--r);
              font-size:12px;color:#fff;cursor:pointer;font-weight:500}

/* Pagination */
.pag-btn{background:none;border:1px solid var(--bdr);border-radius:var(--r);
         width:32px;height:32px;display:flex;align-items:center;justify-content:center;
         cursor:pointer;color:var(--text);font-size:16px;transition:background .15s}
.pag-btn:hover:not(:disabled){background:var(--surf2)}
.pag-btn:disabled{opacity:.3;cursor:default}
.range-display{font-size:11px;font-weight:500;color:var(--muted);min-width:160px;
               text-align:center;white-space:nowrap;letter-spacing:.01em}

/* Dropdown */
.dd-wrap{position:relative}
.dd-btn{display:flex;align-items:center;gap:6px;padding:6px 12px;
        border:1px solid var(--bdr);border-radius:var(--r);background:var(--surf);
        font-size:13px;color:var(--text);cursor:pointer;transition:background .15s;white-space:nowrap}
.dd-btn:hover{background:var(--surf2)}
.dd-menu{display:none;position:absolute;top:calc(100% + 4px);left:0;background:var(--surf);
         border:1px solid var(--bdr);border-radius:var(--r);min-width:190px;z-index:60;padding:4px 0}
.dd-menu.open{display:block}
.dd-item{display:flex;align-items:center;gap:10px;padding:8px 14px;font-size:13px;cursor:pointer;transition:background .12s}
.dd-item:hover{background:var(--surf2)}
.dd-chk{width:15px;height:15px;border:1.5px solid var(--bdr);border-radius:3px;
        display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .12s}
.dd-chk.on{background:var(--accent);border-color:var(--accent)}
.dd-chk.on::after{content:'';display:block;width:8px;height:5px;
                  border-left:1.5px solid #fff;border-bottom:1.5px solid #fff;
                  transform:rotate(-45deg) translateY(-1px)}
.cat-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.filter-tags{display:flex;flex-wrap:wrap;gap:5px}
.f-tag{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;
       border:1px solid var(--bdr);border-radius:var(--r);font-size:12px;background:var(--surf)}
.f-tag-x{cursor:pointer;color:var(--muted);font-size:14px;line-height:1}
.f-tag-x:hover{color:var(--text)}

/* ── Calendar ── */
.cal-nav{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.cal-nav-btn{background:none;border:1px solid var(--bdr);border-radius:var(--r);
             padding:5px 12px;font-size:14px;cursor:pointer;color:var(--text);transition:background .15s}
.cal-nav-btn:hover{background:var(--surf2)}
.cal-month-title{font-size:16px;font-weight:600;flex:1}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;
          background:var(--bdr);border:1px solid var(--bdr);border-radius:var(--r);overflow:hidden}
.cal-head{background:var(--surf2);text-align:center;padding:8px 4px;font-size:10px;
          font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.day-cell{background:var(--surf);padding:8px 7px;min-height:80px}
.day-cell.clickable{cursor:pointer}.day-cell.clickable:hover{background:var(--surf2)}
.day-cell.out{background:var(--bg)}
.day-cell.today{outline:2px solid var(--accent);outline-offset:-2px}
.day-num{font-size:12px;font-weight:500;color:var(--text);margin-bottom:5px}
.day-cell.out .day-num{color:rgba(255,255,255,.2)}
.event-pill{display:block;font-size:10px;padding:2px 6px;border-radius:6px;margin-bottom:3px;
            color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ── By Type ── */
.bar-row{display:flex;align-items:center;gap:12px;padding:8px 0;cursor:default;
         border-radius:var(--r);transition:background .15s;position:relative}
.bar-row:hover{background:var(--surf2)}
.bar-label{width:120px;font-size:12px;font-weight:500;color:var(--text);flex-shrink:0;
           display:flex;align-items:center;gap:5px;justify-content:flex-end}
.bar-label-text{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;height:48px;background:var(--surf2);border-radius:var(--r);overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:var(--r);width:0;transition:width .6s cubic-bezier(.16,1,.3,1),filter .15s}
.bar-row:hover .bar-fill{filter:brightness(1.25)}
.bar-count{width:36px;font-size:13px;font-weight:600;color:var(--text);flex-shrink:0;text-align:left}
.bar-tip{display:none;position:fixed;z-index:999;background:#2A2A2A;
         border:1px solid #3A3A3A;border-radius:var(--r);padding:8px 12px;
         font-size:12px;color:#fff;pointer-events:none;line-height:1.7}
/* Category help tooltip */
.cat-help{display:inline-flex;align-items:center;justify-content:center;
          width:14px;height:14px;border-radius:50%;border:1px solid var(--bdr);
          font-size:9px;color:var(--muted);cursor:help;flex-shrink:0;
          position:relative;transition:border-color .15s}
.cat-help:hover{border-color:var(--muted)}
.cat-help:hover .cat-tip{display:block}
.cat-tip{display:none;position:absolute;bottom:calc(100% + 8px);right:0;
         background:#222;border:1px solid #3A3A3A;border-radius:6px;
         padding:10px 12px;font-size:11px;color:#ccc;white-space:nowrap;
         min-width:220px;z-index:200;line-height:1.8;pointer-events:none;
         box-shadow:0 4px 20px rgba(0,0,0,.4)}
/* Category guide */
.cat-guide{margin-top:20px;background:var(--surf);border:1px solid var(--bdr);border-radius:8px;overflow:hidden}
.cat-guide-toggle{width:100%;background:none;border:none;padding:14px 18px;
                  text-align:left;font-size:13px;color:var(--muted);cursor:pointer;
                  display:flex;align-items:center;justify-content:space-between;transition:color .15s}
.cat-guide-toggle:hover{color:var(--text)}
.cat-guide-body{display:none;padding:0 18px 18px}
.cat-guide-body.open{display:block}
.cg-row{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--bdr);align-items:flex-start}
.cg-row:last-of-type{border-bottom:none}
.cg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px}
.cg-name{font-size:12px;font-weight:600;color:var(--text);width:100px;flex-shrink:0}
.cg-courses{font-size:11px;color:var(--muted);line-height:1.7}
.cg-note{font-size:11px;color:rgba(255,255,255,.25);margin-top:14px;padding-top:12px;border-top:1px solid var(--bdr)}

/* Donut chart */
.donut-wrap{display:flex;align-items:center;gap:32px;flex-wrap:wrap}
.donut-svg-box{flex-shrink:0}
.donut-legend{display:flex;flex-direction:column;gap:8px}
.legend-item{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted);cursor:default}
.legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.legend-name{color:var(--text);font-weight:500}
.legend-pct{color:var(--muted)}

/* ── Progress Tab ── */
.prog-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px}
.prog-title{font-size:24px;font-weight:700;letter-spacing:-.5px}
.year-strip{display:flex;gap:2px;background:var(--bg);border:1px solid var(--bdr);
            border-radius:var(--r);padding:3px}
.year-strip button{background:none;border:none;padding:5px 14px;font-size:13px;color:var(--muted);
                   cursor:pointer;border-radius:3px;white-space:nowrap;transition:all .15s}
.year-strip button.active{background:var(--surf);color:var(--text);font-weight:500}
.year-strip button:hover:not(.active){color:var(--text)}
.level-block{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
             padding:32px 32px 28px;margin-bottom:24px;position:relative;overflow:hidden}
.mountain-svg{position:absolute;bottom:0;left:0;right:0;width:100%;height:65%;pointer-events:none}
.level-content{position:relative;z-index:1}
.level-emoji{font-size:40px;margin-bottom:10px;display:block;line-height:1}
.level-name{font-size:30px;font-weight:700;letter-spacing:-1px;margin-bottom:4px}
.level-count{font-size:13px;color:var(--muted);margin-bottom:22px}
.level-bar-section{position:relative;padding-top:34px;margin-bottom:8px}
.shoe-track{position:absolute;top:0;left:0;width:100%;height:30px;pointer-events:none}
#lvShoe{position:absolute;font-size:22px;left:0;top:0;transform:translateX(-50%);display:block;line-height:1}
@keyframes shoeBounce{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(-4px)}}
#lvShoe.bouncing{animation:shoeBounce 1.5s ease-in-out infinite}
.level-bar-track{height:5px;background:var(--bdr);border-radius:3px;overflow:hidden}
.level-bar-fill{height:100%;background:var(--accent);border-radius:3px;width:0}
.level-bar-label{font-size:12px;color:var(--muted);display:flex;justify-content:space-between;margin-top:6px}
.level-steps{display:flex;gap:12px;margin-top:18px;border-top:1px solid var(--bdr);
             padding-top:14px;flex-wrap:wrap}
.level-step{display:flex;align-items:center;gap:6px;font-size:11px;color:rgba(255,255,255,.3)}
.level-step .dot{width:6px;height:6px;border-radius:50%;background:var(--bdr);flex-shrink:0}
.level-step.done{color:rgba(255,255,255,.6)}.level-step.done .dot{background:var(--accent)}
.level-step.curr{color:var(--text);font-weight:600}
.level-step.curr .dot{background:var(--accent);width:8px;height:8px;box-shadow:0 0 0 3px rgba(232,67,26,.25)}

/* Badges */
.badges-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:24px}
.badge-card{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
            padding:18px 14px;text-align:center;position:relative;
            animation:badgePop .35s cubic-bezier(.16,1,.3,1) both;
            transition:transform .2s,border-color .2s}
.badge-card.unlocked:hover{transform:translateY(-3px);border-color:#444}
.badge-card.locked{opacity:.4;filter:grayscale(1)}
.badge-emoji-wrap{position:relative;display:inline-block;margin-bottom:8px}
.badge-emoji{font-size:28px;display:block;line-height:1}
.lock-svg{position:absolute;top:-2px;right:-6px;width:14px;height:14px;opacity:.85}
@keyframes badgePop{from{opacity:0;transform:scale(.82) translateY(10px)}to{opacity:1;transform:none}}
.badge-name{font-size:12px;font-weight:600;margin-bottom:4px;color:var(--text)}
.badge-detail{font-size:11px;color:var(--muted);line-height:1.5}
.badge-card.unlocked .badge-detail{color:#3D9B70}

/* Year in Review */
.yir-section{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
             padding:24px;margin-bottom:24px}
.yir-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
           color:var(--muted);margin-bottom:18px}
.yir-row{display:grid;grid-template-columns:60px 1fr 80px 140px 140px;
         gap:12px;align-items:center;padding:11px 0;border-bottom:1px solid var(--bdr)}
.yir-row:last-child{border-bottom:none}
.yir-year{font-size:14px;font-weight:700;color:var(--text)}
.yir-sessions{font-size:13px;color:var(--muted)}
.yir-hours{font-size:13px;color:var(--muted)}
.yir-level{font-size:12px;font-weight:500;color:var(--text)}
.yir-prog{display:flex;align-items:center;gap:8px}
.yir-check{font-size:14px;color:#3D9B70;font-weight:700}
.yir-pct{font-size:12px;color:var(--muted);min-width:34px;text-align:right}
.yir-bar-bg{flex:1;height:3px;background:var(--bdr);border-radius:2px;overflow:hidden}
.yir-bar-fill{height:100%;background:var(--accent);border-radius:2px}

/* 30-day summary */
.summary-30{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);padding:24px 28px}
.summary-30-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:16px}
.s30-item{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid var(--bdr);font-size:14px;line-height:1.55}
.s30-item:last-child{border-bottom:none}
.s30-item strong{color:var(--accent)}
.s30-arrow{color:var(--accent);flex-shrink:0;margin-top:1px}

/* Modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:500;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
       width:360px;max-width:92vw;padding:24px;max-height:80vh;overflow-y:auto;
       animation:modalIn .2s ease both}
@keyframes modalIn{from{opacity:0;transform:scale(.96) translateY(8px)}to{opacity:1;transform:none}}
.modal-date{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:16px}
.modal-ev{padding:12px 0;border-bottom:1px solid var(--bdr)}
.modal-ev:last-of-type{border-bottom:none}
.modal-ev-name{font-size:14px;font-weight:600;margin-bottom:6px}
.modal-ev-row{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--muted);align-items:center}
.cat-badge{display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;color:#fff}
.modal-close{display:block;width:100%;margin-top:18px;padding:10px;background:none;
             border:1px solid var(--bdr);border-radius:var(--r);font-size:13px;cursor:pointer;color:var(--text);transition:background .15s}
.modal-close:hover{background:var(--surf2)}
.empty{text-align:center;padding:56px 0;color:var(--muted);font-size:14px}

/* ── Mobile ── */
@media(max-width:768px){
  :root{--pad:16px}
  .hero-body{flex-direction:column}
  .hero-main{grid-template-columns:repeat(2,1fr)}
  .hero-30{border-left:none;border-top:1px solid rgba(255,255,255,.07)}
  .h-val{font-size:42px}.h-card{padding:18px 16px}
  .tab-btn{padding:14px 12px 13px;font-size:13px}
  .badges-grid{grid-template-columns:repeat(2,1fr)}
  canvas{height:200px!important}
  .day-cell{min-height:58px;padding:5px 4px}
  .event-pill{font-size:9px}
  .bar-label{width:88px}
  .yir-row{grid-template-columns:48px 1fr 60px;grid-template-rows:auto auto}
  .yir-hours,.yir-level{display:none}
}
</style>
</head>
<body>

<!-- ══ LANDING PAGE ══════════════════════════════════════════════ -->
<div id="landing">
  <svg class="land-mtn" viewBox="0 0 1440 500" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <path d="M0,500 L120,300 L220,380 L360,160 L480,280 L620,80 L740,200 L860,110 L980,180 L1100,50 L1220,140 L1340,90 L1440,160 L1440,500 Z" fill="#0D2137" opacity="0.25"/>
    <path d="M0,500 L80,400 L180,440 L300,340 L420,400 L540,260 L660,320 L780,240 L900,300 L1020,190 L1140,260 L1260,200 L1380,260 L1440,220 L1440,500 Z" fill="#081829" opacity="0.18"/>
  </svg>
  <div class="land-content">
    <h1 class="land-h1">Your training,<br>visualized.</h1>
    <p class="land-sub">Drop in your Apple Calendar .ics files and get a beautiful workout dashboard — trends, calendar, progress and more.</p>
    <div class="land-btns">
      <button class="land-btn" onclick="enterDashboard()">View Dashboard →</button>
      <a id="landGH" href="#" target="_blank" rel="noopener" class="land-btn-out">See on GitHub</a>
    </div>
    <div class="land-cards">
      <div class="land-card">
        <div class="land-card-icon">📈</div>
        <div class="land-card-title">Trend Analysis</div>
        <div class="land-card-desc">Weekly or monthly charts across all categories, with filters and date range selection.</div>
      </div>
      <div class="land-card">
        <div class="land-card-icon">📅</div>
        <div class="land-card-title">Calendar View</div>
        <div class="land-card-desc">See every session on a full calendar. Click any day to see details.</div>
      </div>
      <div class="land-card">
        <div class="land-card-icon">🏔️</div>
        <div class="land-card-title">Progress System</div>
        <div class="land-card-desc">Annual goals, level badges, and year-by-year review of your fitness journey.</div>
      </div>
    </div>
  </div>
  <div class="land-footer">Built with Claude · Open source on GitHub &nbsp;·&nbsp; Drop in your .ics files and go<br>© 2026 Wenqing Chen · MIT License</div>
</div>

<!-- ══ DASHBOARD APP ════════════════════════════════════════════ -->
<div id="app" style="display:none">
<div class="bar-tip" id="barTip"></div>

<!-- ══ HERO ══════════════════════════════════════════════════════ -->
<div class="hero">
  <div class="wrap">
    <div class="hero-top"><span class="logo" id="appLogo">Workout</span></div>
    <div class="hero-body">
      <div class="hero-main">
        <div class="h-card"><div class="h-label">Sessions</div><div class="h-val" id="vSessions">0</div></div>
        <div class="h-card"><div class="h-label">Active Days</div><div class="h-val" id="vDays">0</div></div>
        <div class="h-card"><div class="h-label">Total Hours</div><div class="h-val" id="vHours">—</div></div>
        <div class="h-card"><div class="h-label">Top Type</div><div class="h-val sm" id="vTop">—</div></div>
      </div>
      <div class="hero-30">
        <div class="h30-title">Past 30 Days</div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
          <div><div class="h30-num" id="v30s">0</div><div class="h30-sub">sessions</div></div>
          <div><div class="h30-num" id="v30h">—</div><div class="h30-sub">hours</div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ TABS ═══════════════════════════════════════════════════════ -->
<div class="tabs-bar">
  <div class="tabs-inner">
    <button class="tab-btn active" data-tab="overview">Overview</button>
    <button class="tab-btn" data-tab="calendar">Calendar</button>
    <button class="tab-btn" data-tab="bytype">By Type</button>
    <button class="tab-btn" data-tab="progress">Progress</button>
    <div id="tabInd"></div>
  </div>
</div>

<div class="wrap" style="padding-top:32px;padding-bottom:56px;">

  <!-- ── Overview ── -->
  <div class="tab-pane active" id="tab-overview">
    <div class="sec-row" style="align-items:flex-start;">
      <div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span class="sec-title">Period</span>
          <div class="tr-strip" id="timeRange">
            <button data-r="1w">1W</button><button data-r="1m">1M</button>
            <button data-r="3m" class="active">3M</button><button data-r="6m">6M</button>
            <button data-r="1y">1Y</button><button data-r="all">All</button>
            <button data-r="custom">Custom</button>
          </div>
        </div>
        <div class="range-desc" id="rangeDesc">Past 3 months · weekly view</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <div class="toggle-grp">
          <button id="mTotal" class="active" onclick="setMode('total')">Total</button>
          <button id="mByCat" onclick="setMode('bycat')">By Type</button>
        </div>
        <div class="toggle-grp" id="granToggle">
          <button id="gWeek" class="active" onclick="setGran('week')">Weekly</button>
          <button id="gMonth" onclick="setGran('month')">Monthly</button>
        </div>
        <div class="toggle-grp">
          <button id="mCount" class="active" onclick="setMetric('count')">Sessions</button>
          <button id="mHours" onclick="setMetric('hours')">Hours</button>
        </div>
        <div style="display:flex;gap:6px;align-items:center;">
          <button class="pag-btn" id="pagPrev" onclick="page(-1)">&#8592;</button>
          <span class="range-display" id="rangeDisplay"></span>
          <button class="pag-btn" id="pagNext" onclick="page(1)" disabled>&#8594;</button>
        </div>
      </div>
    </div>
    <div class="custom-row" id="customRow">
      <label>From</label><input type="date" id="cs">
      <label>to</label><input type="date" id="ce">
      <button class="custom-apply" onclick="applyCustom()">Apply</button>
    </div>
    <div id="filterRow" style="display:none;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px;">
      <div class="dd-wrap" id="ddWrap">
        <button class="dd-btn" onclick="toggleDD()">
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
            <circle cx="2.5" cy="2.5" r="2" fill="currentColor"/>
            <circle cx="9.5" cy="2.5" r="2" fill="currentColor"/>
            <circle cx="2.5" cy="9.5" r="2" fill="currentColor"/>
            <circle cx="9.5" cy="9.5" r="2" fill="currentColor"/>
          </svg>
          Filter types
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>
        <div class="dd-menu" id="ddMenu"></div>
      </div>
      <div class="filter-tags" id="filterTags"></div>
    </div>
    <div class="chart-box" style="padding:16px;" id="trendBox">
      <canvas id="trendChart" height="280"></canvas>
    </div>
  </div>

  <!-- ── Calendar ── -->
  <div class="tab-pane" id="tab-calendar">
    <div class="cal-nav">
      <button class="cal-nav-btn" onclick="navMonth(-1)">&#8592;</button>
      <span class="cal-month-title" id="calTitle"></span>
      <button class="cal-nav-btn" onclick="navMonth(1)">&#8594;</button>
    </div>
    <div id="calGrid"></div>
  </div>

  <!-- ── By Type ── -->
  <div class="tab-pane" id="tab-bytype">
    <div class="sec-row" style="margin-bottom:20px;align-items:flex-start;">
      <span class="sec-title" style="padding-top:6px;">By Type</span>
      <div style="display:flex;flex-direction:column;gap:0;align-items:flex-end;">
        <div class="tr-strip" id="btTimeRange">
          <button data-bt="1w">1W</button><button data-bt="1m">1M</button>
          <button data-bt="3m" class="active">3M</button><button data-bt="6m">6M</button>
          <button data-bt="1y">1Y</button><button data-bt="all">All</button>
          <button data-bt="custom">Custom</button>
        </div>
        <div class="custom-row" id="btCustomRow" style="justify-content:flex-end;">
          <label>From</label><input type="date" id="btCs">
          <label>to</label><input type="date" id="btCe">
          <button class="custom-apply" onclick="applyBtCustom()">Apply</button>
        </div>
      </div>
    </div>
    <div class="chart-box" id="barsBox">
      <div class="sec-title" style="margin-bottom:16px;">Sessions by Type</div>
      <div id="barsContainer"></div>
    </div>
    <div class="chart-box" id="donutBox">
      <div class="sec-title" style="margin-bottom:16px;">Distribution</div>
      <div id="donutContainer"></div>
    </div>
    <div class="cat-guide">
      <button class="cat-guide-toggle" onclick="toggleCatGuide(this)">
        How categories work
        <svg width="12" height="8" viewBox="0 0 12 8" fill="none"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </button>
      <div class="cat-guide-body" id="catGuideBody"></div>
    </div>
  </div>

  <!-- ── Progress ── -->
  <div class="tab-pane" id="tab-progress">
    <div class="prog-header">
      <div class="prog-title" id="progTitle">2026 Progress</div>
      <div class="year-strip" id="yearStrip"></div>
    </div>
    <div class="level-block">
      <svg class="mountain-svg" id="mtnSvg" viewBox="0 0 800 220" preserveAspectRatio="none" aria-hidden="true">
        <path d="M0,220 L90,130 L160,175 L240,80 L320,140 L420,35 L500,100 L580,55 L650,90 L720,20 L800,60 L800,220 Z" fill="#0D2137" opacity="0.55"/>
        <path d="M0,220 L70,170 L140,200 L200,145 L280,185 L360,110 L440,155 L520,95 L600,140 L680,85 L800,130 L800,220 Z" fill="#081829" opacity="0.4"/>
      </svg>
      <div class="level-content">
        <span class="level-emoji" id="lvEmoji"></span>
        <div class="level-name" id="lvName"></div>
        <div class="level-count" id="lvCount"></div>
        <div class="level-bar-section">
          <div class="shoe-track"><span id="lvShoe">🥾</span></div>
          <div class="level-bar-track"><div class="level-bar-fill" id="lvBar"></div></div>
        </div>
        <div class="level-bar-label" id="lvBarLabel"></div>
        <div class="level-steps" id="lvSteps"></div>
      </div>
    </div>
    <div class="sec-row" style="margin-bottom:14px;">
      <span class="sec-title">Achievements</span>
      <span style="font-size:12px;color:var(--muted);" id="badgeCount"></span>
    </div>
    <div class="badges-grid" id="badgesGrid"></div>
    <div class="yir-section">
      <div class="yir-title">Year in Review</div>
      <div id="yirBody"></div>
    </div>
    <div class="summary-30">
      <div class="summary-30-title">Past 30 Days</div>
      <div id="summary30"></div>
    </div>
  </div>

</div><!-- /wrap -->

<div class="modal-overlay" id="modalOv" onclick="handleOv(event)">
  <div class="modal">
    <div class="modal-date" id="modalDate"></div>
    <div id="modalEvs"></div>
    <button class="modal-close" onclick="closeModal()">Close</button>
  </div>
</div>
</div><!-- /app -->

<script>
// ══════════════════════════════════════════════════════════════════════════════
// DATA
// ══════════════════════════════════════════════════════════════════════════════
const ALL_EVENTS = __EVENTS_JSON__;
const CONFIG     = __CONFIG_JSON__;
const CAT_COLORS = Object.fromEntries(Object.entries(CONFIG.categories).map(([k,v])=>[k,v.color]));
const ALL_CATS   = Object.keys(CONFIG.categories);
const ANNUAL_TARGET = CONFIG.annual_target||250;
const GITHUB_URL    = CONFIG.github_url||'';
Chart.defaults.color = '#9A9A9A';

const CAT_GUIDE = {
  "Pilates & Yoga":["Reformer Pilates","MoreYoga series","Barre Fit","FLOW LDN","Tempo Pilates","Hot Yoga","Vinyasa Flow","Strength Pilates"],
  "Ride":["RIDE","RIDE - Sculpt","RIDE - Performance"],
  "Tennis":["Abbotts Park Courts","Downhills Park Courts","Lloyd Park Courts","🎾 series"],
  "Gym":["Gym Session","Bodypump","Bodycombat","Hyrox","Strength & Conditioning","Functional Fitness","Boxfit","Power Pump","Studio Strength","CrossFit"],
  "Hiking":["徒步 series","Hiking routes"],
  "Dance":["Zumba","Dance Fitness","Strictly Salsa","Fitbounce","Step Aerobics","Legs Bums and Tums"],
  "Swimming":["Casual Swim"],
  "Squash":["Squash","Squash Court"],
  "Bouldering":["Bouldering series","Climbing"],
};

const ANNUAL_LEVELS=[
  {min:0,   emoji:'🏕️',name:'Base Camp',   next:50},
  {min:50,  emoji:'🥾',name:'Trail Walker', next:100},
  {min:100, emoji:'⛰️',name:'Hill Climber', next:150},
  {min:150, emoji:'🏔️',name:'Peak Chaser',  next:200},
  {min:200, emoji:'🗻',name:'Summit Seeker',next:250},
  {min:250, emoji:'🌟',name:'Summit Master',next:null},
];

function getAnnualLevel(n){
  for(let i=ANNUAL_LEVELS.length-1;i>=0;i--) if(n>=ANNUAL_LEVELS[i].min) return ANNUAL_LEVELS[i];
  return ANNUAL_LEVELS[0];
}

// ── State ──────────────────────────────────────────────────────────────────
let range='3m', cStart=null, cEnd=null;
let btRange='3m', btCStart=null, btCEnd=null;
let customGranOverride=null;
let metric='count', trendMode='total';
let activeCats=new Set(ALL_CATS), trendOffset=0;
let trendChart=null, calMonthOff=0;
let progressYear=String(new Date().getFullYear());
const PAGE_SIZE=13;
const TAB_ORDER=['overview','calendar','bytype','progress'];
let currentTabIdx=0;

// ══════════════════════════════════════════════════════════════════════════════
// LANDING PAGE
// ══════════════════════════════════════════════════════════════════════════════
function enterDashboard(){
  const lp=document.getElementById('landing');
  lp.classList.add('out');
  setTimeout(()=>{
    lp.style.display='none';
    const app=document.getElementById('app');
    app.style.display='block';
    moveTabIndicator(document.querySelector('.tab-btn.active'));
    refresh();renderCalendar();
  },600);
}
// Parallax on landing
document.addEventListener('mousemove',e=>{
  const lp=document.getElementById('landing');
  if(!lp||lp.style.display==='none'||lp.classList.contains('out')) return;
  const mx=(e.clientX/window.innerWidth-.5)*20;
  const my=(e.clientY/window.innerHeight-.5)*10;
  const mtn=lp.querySelector('.land-mtn');
  if(mtn) mtn.style.transform=`translate(${mx}px,${my}px)`;
});

// ══════════════════════════════════════════════════════════════════════════════
// TAB SWITCHING
// ══════════════════════════════════════════════════════════════════════════════
function moveTabIndicator(btn){
  const ind=document.getElementById('tabInd');
  if(!ind||!btn) return;
  ind.style.left=btn.offsetLeft+'px';
  ind.style.width=btn.offsetWidth+'px';
}

function switchTab(id){
  const newIdx=TAB_ORDER.indexOf(id);
  const dir=newIdx>currentTabIdx?1:-1;
  const isLift=id==='progress';
  const oldPane=document.querySelector('.tab-pane.active');
  const newPane=document.getElementById('tab-'+id);
  if(!oldPane||oldPane===newPane){currentTabIdx=newIdx;return;}

  const exitX=isLift?'0px':`${-dir*30}px`;
  const exitY=isLift?'-15px':'0px';
  const enterX=isLift?'0px':`${dir*40}px`;
  const enterY=isLift?'30px':'0px';

  // Exit old
  Object.assign(oldPane.style,{
    transition:'opacity 200ms ease,transform 200ms ease',
    opacity:'0',transform:`translate(${exitX},${exitY})`
  });
  setTimeout(()=>{
    oldPane.classList.remove('active');
    oldPane.style.cssText='';
    // Enter new
    newPane.style.cssText=`opacity:0;transform:translate(${enterX},${enterY});display:block`;
    newPane.classList.add('active');
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      newPane.style.transition='opacity 350ms cubic-bezier(.4,0,.2,1),transform 350ms cubic-bezier(.4,0,.2,1)';
      newPane.style.opacity='1';
      newPane.style.transform='none';
      setTimeout(()=>{newPane.style.cssText='';},360);
    }));
  },210);
  currentTabIdx=newIdx;
}

// ══════════════════════════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════════════════════════
const parseDate=s=>new Date(s+(s.includes('T')?'':'T00:00:00'));
const toStr=d=>d.toISOString().slice(0,10);
function today(){const n=new Date();return new Date(n.getFullYear(),n.getMonth(),n.getDate())}

function getRangeStart(r){
  const t=today();
  const map={'1w':7,'1m':30,'3m':90,'6m':180,'1y':365};
  if(map[r]) return new Date(t.getTime()-map[r]*864e5);
  return new Date('2000-01-01');
}
function getFiltered(){
  const t=today();
  if(range==='custom'&&cStart&&cEnd){
    const s=parseDate(cStart),e=parseDate(cEnd);
    return ALL_EVENTS.filter(ev=>{const d=parseDate(ev.date);return d>=s&&d<=e;});
  }
  const start=getRangeStart(range);
  return ALL_EVENTS.filter(ev=>{const d=parseDate(ev.date);return d>=start&&d<=t;});
}
function getBtFiltered(){
  const t=today();
  if(btRange==='custom'&&btCStart&&btCEnd){
    const s=parseDate(btCStart),e=parseDate(btCEnd);
    return ALL_EVENTS.filter(ev=>{const d=parseDate(ev.date);return d>=s&&d<=e;});
  }
  const start=getRangeStart(btRange);
  return ALL_EVENTS.filter(ev=>{const d=parseDate(ev.date);return d>=start&&d<=t;});
}

const getDayKey=s=>s.slice(0,10);
function getWeekKey(s){
  const d=parseDate(s),dow=d.getDay();
  return toStr(new Date(d.getTime()-(dow===0?6:dow-1)*864e5));
}
const getMonthKey=s=>s.slice(0,7);

// Granularity resolution
function autoDetectCustomGran(){
  if(!cStart||!cEnd) return 'week';
  return (parseDate(cEnd)-parseDate(cStart))/(864e5)>180?'month':'week';
}
function getEffectiveGran(){
  if(range==='1w') return 'day';
  if(range==='1m'||range==='3m') return 'week';
  if(range==='6m'||range==='1y'||range==='all') return 'month';
  return customGranOverride||autoDetectCustomGran();
}
function getWindowStart(){
  if(range==='custom'&&cStart) return parseDate(cStart);
  if(range==='all'){
    if(!ALL_EVENTS.length) return today();
    return parseDate(ALL_EVENTS.reduce((a,b)=>a.date<b.date?a:b).date);
  }
  return getRangeStart(range);
}
function getWindowEnd(){return(range==='custom'&&cEnd)?parseDate(cEnd):today();}

function generateAllKeys(start,end,gran){
  const keys=[];
  if(gran==='day'){
    let cur=new Date(start);
    while(cur<=end){keys.push(toStr(cur));cur=new Date(cur.getTime()+864e5);}
  } else if(gran==='week'){
    const dow=start.getDay();
    let cur=new Date(start.getTime()-(dow===0?6:dow-1)*864e5);
    while(cur<=end){keys.push(toStr(cur));cur=new Date(cur.getTime()+7*864e5);}
  } else {
    let y=start.getFullYear(),m=start.getMonth();
    const ey=end.getFullYear(),em=end.getMonth();
    while(y<ey||(y===ey&&m<=em)){
      keys.push(y+'-'+(m+1<10?'0':'')+(m+1));
      if(++m===12){m=0;y++;}
    }
  }
  return keys;
}

// X-axis labels
function dayLabel(s){return parseDate(s).toLocaleDateString('en-GB',{weekday:'short'});}
function weekLabel(s){return parseDate(s).toLocaleDateString('en-GB',{day:'numeric',month:'short'});}
function monthLabel(mk){
  const[y,m]=mk.split('-');
  return new Date(+y,+m-1,1).toLocaleDateString('en-GB',{month:'short',year:'numeric'});
}

// Period description
const RANGE_DESC={
  '1w':'Past 7 days · daily view',
  '1m':'Past 30 days · weekly view',
  '3m':'Past 3 months · weekly view',
  '6m':'Past 6 months · monthly view',
  '1y':'Past 12 months · monthly view',
  'all':'All time · monthly view',
};
function updatePeriodUI(){
  const desc=document.getElementById('rangeDesc');
  const gt=document.getElementById('granToggle');
  const isCustom=range==='custom';
  gt.style.display=isCustom?'flex':'none';
  if(isCustom){
    const g=getEffectiveGran();
    const gn=g==='day'?'daily':g==='week'?'weekly':'monthly';
    desc.textContent='Custom range · '+gn+' view'+(customGranOverride?'':' (auto)');
    document.getElementById('gWeek').classList.toggle('active',g==='week');
    document.getElementById('gMonth').classList.toggle('active',g==='month');
  } else {
    desc.textContent=RANGE_DESC[range]||'';
  }
}

function fmtHours(min){
  if(!min) return null;
  const h=Math.floor(min/60),m=min%60;
  return h===0?m+'m':m===0?h+'h':h+'h '+m+'m';
}
const fmtDate=s=>s?parseDate(s).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'';
function fmtMonth(mk){const[y,m]=mk.split('-');return new Date(+y,+m-1,1).toLocaleDateString('en-GB',{month:'long',year:'numeric'})}
function fmtTime(iso){
  if(!iso||!iso.includes('T')) return '';
  const t=iso.split('T')[1];
  const h=parseInt(t.slice(0,2)),mi=t.slice(3,5);
  return((h%12)||12)+':'+mi+(h>=12?' PM':' AM');
}
function addMins(iso,mins){
  if(!iso||!mins) return null;
  return new Date(parseDate(iso).getTime()+mins*60000).toISOString().slice(0,19);
}

// ══════════════════════════════════════════════════════════════════════════════
// SPRING COUNT-UP
// ══════════════════════════════════════════════════════════════════════════════
function springEase(t){
  if(t>=1) return 1;
  const u=1-t;
  return 1-u*u*u+Math.sin(t*Math.PI)*0.35*u;
}
function countUp(el,target,dur,dec){
  dec=dec||0;
  const from=parseFloat(el.dataset.cur||0)||0;
  el.dataset.cur=target;
  const t0=performance.now();
  (function step(now){
    const p=Math.min((now-t0)/dur,1);
    const ease=springEase(p);
    const v=from+(target-from)*ease;
    el.textContent=dec?v.toFixed(dec):Math.round(v);
    if(p<1) requestAnimationFrame(step);
  })(t0);
}

// ══════════════════════════════════════════════════════════════════════════════
// HERO CARDS
// ══════════════════════════════════════════════════════════════════════════════
function updateCards(evs){
  const sessions=evs.length;
  const days=new Set(evs.map(e=>e.date)).size;
  const withDur=evs.filter(e=>e.duration_min);
  const totalMin=withDur.reduce((s,e)=>s+e.duration_min,0);
  const cats={};evs.forEach(e=>{cats[e.category]=(cats[e.category]||0)+1;});
  const top=Object.entries(cats).sort((a,b)=>b[1]-a[1])[0];
  countUp(document.getElementById('vSessions'),sessions,600);
  countUp(document.getElementById('vDays'),days,600);
  const hEl=document.getElementById('vHours');
  if(withDur.length) countUp(hEl,+(totalMin/60).toFixed(1),600,1);
  else{hEl.textContent='—';hEl.dataset.cur='0';}
  document.getElementById('vTop').textContent=top?top[0]:'—';
}
function update30d(){
  const cutoff=new Date(today().getTime()-30*864e5);
  const e30=ALL_EVENTS.filter(e=>parseDate(e.date)>=cutoff);
  const min30=e30.filter(e=>e.duration_min).reduce((s,e)=>s+e.duration_min,0);
  countUp(document.getElementById('v30s'),e30.length,600);
  const h=document.getElementById('v30h');
  if(min30>0) countUp(h,+(min30/60).toFixed(1),600,1);
  else h.textContent='—';
}

// ══════════════════════════════════════════════════════════════════════════════
// RANGE DISPLAY
// ══════════════════════════════════════════════════════════════════════════════
function updateRangeDisplay(keys){
  const el=document.getElementById('rangeDisplay');
  if(!el||!keys.length){if(el) el.textContent='';return;}
  const g=getEffectiveGran();
  const fmtDY=d=>d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
  const fmtMY=d=>d.toLocaleDateString('en-GB',{month:'short',year:'numeric'});
  if(g==='month'){
    const p=mk=>{const[y,m]=mk.split('-');return new Date(+y,+m-1,1);};
    const first=p(keys[0]),last=p(keys[keys.length-1]);
    el.textContent=keys.length===1
      ? first.toLocaleDateString('en-GB',{month:'long',year:'numeric'})
      : fmtMY(first)+' – '+fmtMY(last);
  } else if(g==='week'){
    const firstMon=parseDate(keys[0]);
    const lastSun=new Date(parseDate(keys[keys.length-1]).getTime()+6*864e5);
    el.textContent=fmtDY(firstMon)+' – '+fmtDY(lastSun);
  } else {
    const first=parseDate(keys[0]),last=parseDate(keys[keys.length-1]);
    el.textContent=keys.length===1?fmtDY(first):fmtDY(first)+' – '+fmtDY(last);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// TREND CHART
// ══════════════════════════════════════════════════════════════════════════════
function buildTrendData(evs){
  const g=getEffectiveGran();
  const keyFn=g==='day'?getDayKey:g==='week'?getWeekKey:getMonthKey;
  const labelFn=g==='day'?dayLabel:g==='week'?weekLabel:monthLabel;
  const catEvs=trendMode==='bycat'?evs.filter(e=>activeCats.has(e.category)):evs;
  const allKeys=generateAllKeys(getWindowStart(),getWindowEnd(),g);
  const total=allKeys.length;
  const pageEnd=Math.max(0,total-trendOffset);
  const pageStart=Math.max(0,pageEnd-PAGE_SIZE);
  const keys=allKeys.slice(pageStart,pageEnd);
  document.getElementById('pagPrev').disabled=pageStart===0;
  document.getElementById('pagNext').disabled=trendOffset===0;
  updateRangeDisplay(keys);
  const labels=keys.map(k=>labelFn(k));
  if(trendMode==='total'){
    const data=keys.map(k=>{
      const e=catEvs.filter(ev=>keyFn(ev.date)===k);
      return metric==='count'?e.length:+(e.filter(x=>x.duration_min).reduce((s,x)=>s+x.duration_min,0)/60).toFixed(1);
    });
    return{labels,datasets:[{label:'All sessions',data,
      borderColor:'#E8431A',backgroundColor:'rgba(232,67,26,0.1)',
      borderWidth:2.5,pointRadius:5,pointHoverRadius:7,pointBackgroundColor:'#E8431A',
      tension:.35,fill:true}]};
  }
  const catsActive=[...activeCats].filter(c=>catEvs.some(e=>e.category===c));
  return{labels,datasets:catsActive.map(cat=>({
    label:cat,
    data:keys.map(k=>{
      const e=catEvs.filter(ev=>keyFn(ev.date)===k&&ev.category===cat);
      return metric==='count'?e.length:+(e.filter(x=>x.duration_min).reduce((s,x)=>s+x.duration_min,0)/60).toFixed(1);
    }),
    borderColor:CAT_COLORS[cat],backgroundColor:CAT_COLORS[cat]+'22',
    borderWidth:2.5,pointRadius:5,pointHoverRadius:7,pointBackgroundColor:CAT_COLORS[cat],
    tension:.35,fill:false
  }))};
}

const darkScales={
  x:{grid:{color:'#2A2A2A'},ticks:{color:'#9A9A9A',font:{size:11},maxRotation:0,maxTicksLimit:13}},
  y:{beginAtZero:true,grid:{color:'#2A2A2A'},
     ticks:{color:'#9A9A9A',font:{size:11},callback:v=>metric==='hours'?v+'h':v}}
};
const darkTooltip={backgroundColor:'#2A2A2A',borderColor:'#3A3A3A',borderWidth:1,
  titleColor:'#fff',bodyColor:'#9A9A9A',padding:10,bodyFont:{size:12},titleFont:{size:12,weight:'500'}};

function renderTrend(evs){
  const box=document.getElementById('trendBox');
  const{labels,datasets}=buildTrendData(evs);
  if(!labels.length){
    if(trendChart){trendChart.destroy();trendChart=null;}
    box.innerHTML='<div class="empty">No sessions in this period.</div>';
    return;
  }
  if(!box.querySelector('canvas')){
    box.innerHTML='<canvas id="trendChart" height="280"></canvas>';
    trendChart=null;
  }
  const ctx=document.getElementById('trendChart').getContext('2d');
  if(trendChart){
    trendChart.data.labels=labels;
    trendChart.data.datasets=datasets;
    trendChart.options.scales=darkScales;
    trendChart.options.plugins.legend.display=trendMode==='bycat';
    trendChart.update({duration:400,easing:'easeInOutQuart'});
  } else {
    trendChart=new Chart(ctx,{
      type:'line',data:{labels,datasets},
      options:{
        responsive:true,maintainAspectRatio:false,animation:{duration:600},
        interaction:{mode:'index',intersect:false},
        plugins:{
          legend:{display:trendMode==='bycat',position:'bottom',
            labels:{font:{size:11},color:'#9A9A9A',boxWidth:8,boxHeight:8,padding:16,usePointStyle:true,pointStyle:'circle'}},
          tooltip:{...darkTooltip,callbacks:{
            label:c=>' '+c.dataset.label+': '+(metric==='hours'?c.parsed.y+'h':c.parsed.y+' sessions')
          }}
        },
        scales:darkScales
      }
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// DROPDOWN FILTER
// ══════════════════════════════════════════════════════════════════════════════
function availCats(evs){return ALL_CATS.filter(c=>evs.some(e=>e.category===c));}
function renderDD(avail){
  const menu=document.getElementById('ddMenu');menu.innerHTML='';
  avail.forEach(cat=>{
    const item=document.createElement('div');item.className='dd-item';
    const on=activeCats.has(cat);
    item.innerHTML=`<span class="dd-chk ${on?'on':''}"></span><span class="cat-dot" style="background:${CAT_COLORS[cat]}"></span>${cat}`;
    item.onclick=e=>{
      e.stopPropagation();
      if(activeCats.has(cat)){if(activeCats.size>1)activeCats.delete(cat);}
      else activeCats.add(cat);
      renderDD(avail);renderFilterTags(avail);renderTrend(getFiltered());
    };
    menu.appendChild(item);
  });
}
function renderFilterTags(avail){
  const c=document.getElementById('filterTags');c.innerHTML='';
  [...activeCats].filter(cat=>avail.includes(cat)).forEach(cat=>{
    const t=document.createElement('span');t.className='f-tag';
    t.innerHTML=`<span class="cat-dot" style="background:${CAT_COLORS[cat]}"></span>${cat}<span class="f-tag-x">&times;</span>`;
    t.querySelector('.f-tag-x').onclick=()=>{if(activeCats.size>1)activeCats.delete(cat);renderDD(avail);renderFilterTags(avail);renderTrend(getFiltered());};
    c.appendChild(t);
  });
}
function toggleDD(){document.getElementById('ddMenu').classList.toggle('open');}
document.addEventListener('click',e=>{const w=document.getElementById('ddWrap');if(w&&!w.contains(e.target))document.getElementById('ddMenu').classList.remove('open');});

// ══════════════════════════════════════════════════════════════════════════════
// CALENDAR
// ══════════════════════════════════════════════════════════════════════════════
function byDateMap(){const m={};ALL_EVENTS.forEach(e=>{if(!m[e.date])m[e.date]=[];m[e.date].push(e);});return m;}
function renderCalendar(){
  const now=new Date();
  const base=new Date(now.getFullYear(),now.getMonth()+calMonthOff,1);
  document.getElementById('calTitle').textContent=base.toLocaleDateString('en-GB',{month:'long',year:'numeric'});
  const byDate=byDateMap(),todayStr=toStr(today());
  const lastDay=new Date(base.getFullYear(),base.getMonth()+1,0).getDate();
  const firstDow=(new Date(base.getFullYear(),base.getMonth(),1).getDay()+6)%7;
  const grid=document.getElementById('calGrid');grid.innerHTML='';
  const cal=document.createElement('div');cal.className='cal-grid';
  ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].forEach(n=>{
    const h=document.createElement('div');h.className='cal-head';h.textContent=n;cal.appendChild(h);
  });
  for(let i=0;i<firstDow;i++) cal.appendChild(makeCell(new Date(base.getFullYear(),base.getMonth(),-firstDow+i+1),byDate,false,todayStr));
  for(let d=1;d<=lastDay;d++) cal.appendChild(makeCell(new Date(base.getFullYear(),base.getMonth(),d),byDate,true,todayStr));
  const total=firstDow+lastDay,trail=(7-total%7)%7;
  for(let i=1;i<=trail;i++) cal.appendChild(makeCell(new Date(base.getFullYear(),base.getMonth()+1,i),byDate,false,todayStr));
  grid.appendChild(cal);
}
function makeCell(dateObj,byDate,inMonth,todayStr){
  const dateKey=toStr(dateObj),evs=byDate[dateKey]||[],isToday=dateKey===todayStr;
  const cell=document.createElement('div');
  cell.className='day-cell'+(inMonth?'':' out')+(isToday?' today':'')+(evs.length?' clickable':'');
  const n=document.createElement('div');n.className='day-num';n.textContent=dateObj.getDate();cell.appendChild(n);
  evs.forEach(e=>{
    const p=document.createElement('span');p.className='event-pill';
    p.style.background=CAT_COLORS[e.category];p.textContent=e.summary.length>16?e.summary.slice(0,15)+'…':e.summary;
    cell.appendChild(p);
  });
  if(evs.length) cell.onclick=()=>openModal(dateKey,evs);
  return cell;
}
function navMonth(d){calMonthOff+=d;renderCalendar();}

// ══════════════════════════════════════════════════════════════════════════════
// BY TYPE — CSS bars + SVG donut + category guide
// ══════════════════════════════════════════════════════════════════════════════
const tip=document.getElementById('barTip');
function showTip(e,html){tip.innerHTML=html;tip.style.display='block';moveTip(e);}
function moveTip(e){tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY-8)+'px';}
function hideTip(){tip.style.display='none';}

function renderByType(){
  const evs=getBtFiltered();
  const catCount={},catDur={};
  evs.forEach(e=>{catCount[e.category]=(catCount[e.category]||0)+1;catDur[e.category]=(catDur[e.category]||0)+(e.duration_min||0);});
  const total=evs.length;
  const sorted=Object.entries(catCount).sort((a,b)=>b[1]-a[1]);
  if(!sorted.length){
    document.getElementById('barsContainer').innerHTML='<div class="empty">No sessions in this period.</div>';
    document.getElementById('donutContainer').innerHTML='';
    return;
  }
  const maxCount=sorted[0][1];
  const container=document.getElementById('barsContainer');
  container.innerHTML='';
  sorted.forEach(([cat,count],i)=>{
    const pct=(count/total*100).toFixed(1);
    const barPct=(count/maxCount*100).toFixed(1);
    const guide=(CAT_GUIDE[cat]||[]).join(', ');
    const row=document.createElement('div');row.className='bar-row';
    row.innerHTML=`
      <div class="bar-label">
        <span class="bar-label-text">${cat}</span>
        <span class="cat-help" tabindex="0">?<div class="cat-tip"><strong>${cat}</strong><br>${guide}</div></span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="background:${CAT_COLORS[cat]};"></div></div>
      <div class="bar-count">${count}</div>`;
    const fill=row.querySelector('.bar-fill');
    setTimeout(()=>{fill.style.width=barPct+'%';},i*60+50);
    const tipHtml=`<strong>${cat}</strong><br>${count} sessions &middot; ${pct}%${catDur[cat]?'<br>'+fmtHours(catDur[cat])+' total':''}`;
    row.addEventListener('mousemove',e=>{showTip(e,tipHtml);});
    row.addEventListener('mouseleave',hideTip);
    container.appendChild(row);
  });
  renderDonut(sorted,catDur,total);
}

function renderDonut(sorted,catDur,total){
  const SIZE=200,cx=100,cy=100,R=75,r=45;
  function p2c(angle,radius){
    const rad=(angle-90)*Math.PI/180;
    return{x:cx+radius*Math.cos(rad),y:cy+radius*Math.sin(rad)};
  }
  function sectorPath(startA,endA){
    const diff=endA-startA;
    if(diff>=359.99) return `M${cx-R},${cy} A${R},${R} 0 1 1 ${cx+R},${cy} A${R},${R} 0 1 1 ${cx-R},${cy} M${cx-r},${cy} A${r},${r} 0 1 0 ${cx+r},${cy} A${r},${r} 0 1 0 ${cx-r},${cy} Z`;
    const s=p2c(startA,R),e=p2c(endA,R),si=p2c(startA,r),ei=p2c(endA,r);
    const large=diff>180?1:0;
    return `M${s.x},${s.y} A${R},${R} 0 ${large} 1 ${e.x},${e.y} L${ei.x},${ei.y} A${r},${r} 0 ${large} 0 ${si.x},${si.y} Z`;
  }
  let startAngle=0;
  const segData=sorted.map(([cat,count])=>{
    const pct=count/total;
    const endAngle=startAngle+pct*360;
    const d=sectorPath(startAngle,endAngle);
    startAngle=endAngle;
    return{cat,count,d,color:CAT_COLORS[cat]};
  });
  const svgId='donut-'+Date.now(),ns='http://www.w3.org/2000/svg';
  const dc=document.getElementById('donutContainer');
  dc.innerHTML=`<div class="donut-wrap">
    <div class="donut-svg-box">
      <svg id="${svgId}" viewBox="0 0 ${SIZE} ${SIZE}" width="${SIZE}" height="${SIZE}" style="overflow:visible">
        <g id="${svgId}-segs">${segData.map(s=>`<path d="${s.d}" fill="${s.color}" class="donut-seg"/>`).join('')}</g>
        <text x="${cx}" y="${cy-4}" text-anchor="middle" dominant-baseline="middle" fill="#fff" font-size="20" font-weight="700">${total}</text>
        <text x="${cx}" y="${cy+14}" text-anchor="middle" fill="#9A9A9A" font-size="11">sessions</text>
      </svg>
    </div>
    <div class="donut-legend">${segData.map(s=>`<div class="legend-item"><span class="legend-dot" style="background:${s.color}"></span><span class="legend-name">${s.cat}</span><span class="legend-pct">${(s.count/total*100).toFixed(1)}%</span></div>`).join('')}</div>
  </div>`;
  const svgEl=document.getElementById(svgId);
  const segs=document.getElementById(svgId+'-segs');
  const defs=document.createElementNS(ns,'defs');
  const clipId='dc-'+svgId,clip=document.createElementNS(ns,'clipPath');
  clip.setAttribute('id',clipId);
  const revealPath=document.createElementNS(ns,'path');
  clip.appendChild(revealPath);defs.appendChild(clip);
  svgEl.insertBefore(defs,svgEl.firstChild);
  segs.setAttribute('clip-path',`url(#${clipId})`);
  const t0=performance.now(),dur=600;
  (function step(now){
    const p=Math.min((now-t0)/dur,1);
    const ease=1-Math.pow(1-p,3);
    const angle=ease*359.99;
    if(p>=1){segs.removeAttribute('clip-path');return;}
    const end=p2c(angle,R+10),start=p2c(0,R+10),large=angle>180?1:0;
    revealPath.setAttribute('d',`M${cx},${cy} L${start.x},${start.y} A${R+10},${R+10} 0 ${large} 1 ${end.x},${end.y} Z`);
    requestAnimationFrame(step);
  })(t0);
}

function renderCatGuide(){
  const body=document.getElementById('catGuideBody');
  if(!body||body._built) return;
  body._built=true;
  ALL_CATS.forEach(cat=>{
    const courses=(CAT_GUIDE[cat]||[]).join(' · ');
    const row=document.createElement('div');row.className='cg-row';
    row.innerHTML=`<span class="cg-dot" style="background:${CAT_COLORS[cat]}"></span><span class="cg-name">${cat}</span><span class="cg-courses">${courses}</span>`;
    body.appendChild(row);
  });
  const note=document.createElement('div');note.className='cg-note';
  note.textContent='Categories are auto-detected from event titles in your .ics files. Customise keywords in config.json or generate_dashboard.py';
  body.appendChild(note);
}
function toggleCatGuide(btn){
  const body=document.getElementById('catGuideBody');
  const open=body.classList.toggle('open');
  btn.querySelector('svg').style.transform=open?'rotate(180deg)':'';
  if(open) renderCatGuide();
}

// ══════════════════════════════════════════════════════════════════════════════
// PROGRESS TAB
// ══════════════════════════════════════════════════════════════════════════════
function getAvailableYears(){
  return[...new Set(ALL_EVENTS.map(e=>e.date.slice(0,4)))].sort();
}

function animateLevelBar(targetPct){
  const bar=document.getElementById('lvBar');
  const shoe=document.getElementById('lvShoe');
  shoe.classList.remove('bouncing');
  bar.style.width='0%';shoe.style.left='0%';
  const t0=performance.now(),dur=800;
  (function step(now){
    const p=Math.min((now-t0)/dur,1);
    const ease=springEase(p);
    const cur=ease*targetPct;
    bar.style.width=cur+'%';shoe.style.left=cur+'%';
    if(p<1) requestAnimationFrame(step);
    else shoe.classList.add('bouncing');
  })(t0);
}

function animateMountain(){
  const svg=document.getElementById('mtnSvg');
  if(!svg) return;
  svg.style.cssText='transform:translateY(60px);opacity:0;transition:none';
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    svg.style.cssText='transform:translateY(0);opacity:1;transition:transform 800ms cubic-bezier(.16,1,.3,1),opacity 800ms ease';
    setTimeout(()=>{svg.style.cssText='';},820);
  }));
}

function renderYearSelector(){
  const yrs=getAvailableYears();
  const strip=document.getElementById('yearStrip');
  strip.innerHTML='';
  yrs.forEach(yr=>{
    const btn=document.createElement('button');
    btn.textContent=yr;
    btn.className=yr===progressYear?'active':'';
    btn.onclick=()=>{progressYear=yr;renderProgress();};
    strip.appendChild(btn);
  });
}

function renderProgress(){
  renderYearSelector();
  document.getElementById('progTitle').textContent=progressYear+' Progress';
  const sorted=[...ALL_EVENTS].sort((a,b)=>a.date.localeCompare(b.date));
  const yrEvs=ALL_EVENTS.filter(e=>e.date.startsWith(progressYear));
  const total=yrEvs.length;
  const lv=getAnnualLevel(total);
  const pct=Math.min(100,Math.round(total/ANNUAL_TARGET*100));

  document.getElementById('lvEmoji').textContent=lv.emoji;
  document.getElementById('lvName').textContent=lv.name;
  document.getElementById('lvCount').textContent=total+' sessions in '+progressYear;

  const toTarget=ANNUAL_TARGET-total;
  document.getElementById('lvBarLabel').innerHTML=
    total>=ANNUAL_TARGET
      ?'<span>0</span><span>Summit Master achieved! 🌟</span>'
      :`<span>0</span><span>${toTarget} more to Summit Master (${ANNUAL_TARGET})</span>`;

  const steps=document.getElementById('lvSteps');steps.innerHTML='';
  ANNUAL_LEVELS.filter(l=>l.next).forEach((l,i)=>{
    const done=total>=l.next;
    const curr=!done&&total>=l.min;
    const el=document.createElement('div');
    el.className='level-step'+(done?' done':curr?' curr':'');
    el.innerHTML=`<div class="dot"></div>${l.name} <span style="opacity:.45">${l.next}</span>`;
    steps.appendChild(el);
  });

  animateLevelBar(pct);
  animateMountain();

  // Badges (all-time)
  const badges=computeBadges(sorted);
  const unlocked=badges.filter(b=>b.unlocked).length;
  document.getElementById('badgeCount').textContent=unlocked+'/'+badges.length+' unlocked';
  const grid=document.getElementById('badgesGrid');grid.innerHTML='';
  badges.forEach((b,i)=>{
    const card=document.createElement('div');
    card.className='badge-card '+(b.unlocked?'unlocked':'locked');
    card.style.animationDelay=(i*80)+'ms';
    const lockSVG=b.unlocked?'':
      `<svg class="lock-svg" viewBox="0 0 24 24" fill="rgba(255,255,255,0.8)">
        <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
      </svg>`;
    card.innerHTML=`<div class="badge-emoji-wrap"><span class="badge-emoji">${b.emoji}</span>${lockSVG}</div><div class="badge-name">${b.name}</div><div class="badge-detail">${b.unlocked?(b.detail||b.desc):b.hint}</div>`;
    grid.appendChild(card);
  });

  // Year in Review
  renderYearInReview();

  // 30-day summary
  const cutoff=new Date(today().getTime()-30*864e5);
  const last30=ALL_EVENTS.filter(e=>parseDate(e.date)>=cutoff);
  const dowCount=[0,0,0,0,0,0,0];
  last30.forEach(e=>dowCount[parseDate(e.date).getDay()]++);
  const peakDow=dowCount.indexOf(Math.max(...dowCount));
  const DAYS=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const toNext=total>=ANNUAL_TARGET?0:ANNUAL_TARGET-total;
  const items=[
    `Over the past 30 days, you completed <strong>${last30.length}</strong> workout${last30.length!==1?'s':''}.`,
    `Your most active day of the week is <strong>${DAYS[peakDow]}</strong>.`,
    total>=ANNUAL_TARGET
      ?`You've hit the annual target — <strong>Summit Master</strong>. Incredible!`
      :`Only <strong>${toNext} more session${toNext!==1?'s':''}</strong> to reach Summit Master this year.`,
  ];
  document.getElementById('summary30').innerHTML=items.map(t=>
    `<div class="s30-item"><span class="s30-arrow">→</span><span>${t}</span></div>`).join('');
}

function renderYearInReview(){
  const yrs=getAvailableYears();
  const body=document.getElementById('yirBody');
  body.innerHTML='';
  yrs.forEach(yr=>{
    const yEvs=ALL_EVENTS.filter(e=>e.date.startsWith(yr));
    const sessions=yEvs.length;
    const totalMin=yEvs.filter(e=>e.duration_min).reduce((s,e)=>s+e.duration_min,0);
    const hours=(totalMin/60).toFixed(1);
    const lv=getAnnualLevel(sessions);
    const pct=Math.min(100,Math.round(sessions/ANNUAL_TARGET*100));
    const done=sessions>=ANNUAL_TARGET;
    const row=document.createElement('div');row.className='yir-row';
    row.innerHTML=`
      <span class="yir-year">${yr}</span>
      <span class="yir-sessions">${sessions} sessions</span>
      <span class="yir-hours">${hours}h</span>
      <span class="yir-level">${lv.emoji} ${lv.name}</span>
      <div class="yir-prog">
        ${done
          ?'<span class="yir-check">✓ Target hit</span>'
          :`<span class="yir-pct">${pct}%</span><div class="yir-bar-bg"><div class="yir-bar-fill" style="width:${pct}%"></div></div>`
        }
      </div>`;
    body.appendChild(row);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// BADGES (all-time)
// ══════════════════════════════════════════════════════════════════════════════
function computeBadges(sorted){
  let maxStreak=0,streak=0,prevDate=null;
  sorted.forEach(e=>{
    const d=parseDate(e.date);
    if(prevDate){
      const diff=(d-prevDate)/(864e5);
      streak=diff===1?streak+1:1;
    } else streak=1;
    maxStreak=Math.max(maxStreak,streak);
    prevDate=d;
  });
  const catCounts={};sorted.forEach(e=>{catCounts[e.category]=(catCounts[e.category]||0)+1;});
  const byMonth={};
  sorted.forEach(e=>{const mk=e.date.slice(0,7);if(!byMonth[mk])byMonth[mk]=new Set();byMonth[mk].add(e.category);});
  const arm=Object.entries(byMonth).find(([,s])=>s.size>=5);
  const maxTypes=Math.max(0,...Object.values(byMonth).map(s=>s.size));
  const maxMonthCount=Math.max(0,...Object.entries(byMonth).map(([k])=>sorted.filter(e=>e.date.startsWith(k)).length));
  const starM=Object.keys(byMonth).find(k=>sorted.filter(e=>e.date.startsWith(k)).length>=20);
  const earlyEvs=sorted.filter(e=>{
    if(!e.dtstart||!e.dtstart.includes('T')) return false;
    const h=parseInt(e.dtstart.split('T')[1].slice(0,2));
    return h<8;
  });
  const winterEvs=sorted.filter(e=>{const m=new Date(e.date+'T00:00:00').getMonth();return m===11||m===0;});
  const byYear={};sorted.forEach(e=>{const y=e.date.slice(0,4);byYear[y]=(byYear[y]||0)+1;});
  const maxYear=Math.max(0,...Object.values(byYear));
  let summitY=null;Object.entries(byYear).sort((a,b)=>a[0].localeCompare(b[0])).forEach(([y,c])=>{if(!summitY&&c>=ANNUAL_TARGET)summitY=y;});
  const topCatE=Object.entries(catCounts).find(([,v])=>v>=100);
  return[
    {emoji:'🔥',name:'7-Day Streak',desc:'7 consecutive training days',
     unlocked:maxStreak>=7,detail:`Longest streak: ${maxStreak} days`,hint:`Longest streak: ${maxStreak}/7 days`},
    {emoji:'💪',name:'Century Club',desc:'100 total sessions',
     unlocked:sorted.length>=100,detail:sorted.length>=100?`100th session: ${fmtDate(sorted[99].date)}`:'',hint:`${sorted.length}/100 sessions`},
    {emoji:'🎾',name:'Court Regular',desc:'30 Tennis sessions',
     unlocked:(catCounts['Tennis']||0)>=30,
     detail:(catCounts['Tennis']||0)>=30?`30th: ${fmtDate(sorted.filter(e=>e.category==='Tennis')[29].date)}`:'',
     hint:`Tennis: ${catCounts['Tennis']||0}/30`},
    {emoji:'🧘',name:'Mind & Body',desc:'50 Pilates & Yoga sessions',
     unlocked:(catCounts['Pilates & Yoga']||0)>=50,
     detail:(catCounts['Pilates & Yoga']||0)>=50?`50th: ${fmtDate(sorted.filter(e=>e.category==='Pilates & Yoga')[49].date)}`:'',
     hint:`Pilates & Yoga: ${catCounts['Pilates & Yoga']||0}/50`},
    {emoji:'🌈',name:'All-Rounder',desc:'5 types in one month',
     unlocked:!!arm,detail:arm?fmtMonth(arm[0]):'',hint:`Best month: ${maxTypes}/5 types`},
    {emoji:'🌅',name:'Early Bird',desc:'Workout before 8 AM',
     unlocked:earlyEvs.length>0,detail:earlyEvs.length>0?`First: ${fmtDate(earlyEvs[0].date)}`:'',hint:'Start a session before 8:00 AM'},
    {emoji:'❄️',name:'Winter Warrior',desc:'Training in December or January',
     unlocked:winterEvs.length>0,detail:winterEvs.length>0?`First: ${fmtDate(winterEvs[0].date)}`:'',hint:'Work out in Dec or Jan'},
    {emoji:'🏆',name:'Monthly Star',desc:'20+ sessions in one month',
     unlocked:!!starM,detail:starM?fmtMonth(starM):'',hint:`Best month: ${maxMonthCount}/20`},
    {emoji:'🏔️',name:'Summit Seeker',desc:`${ANNUAL_TARGET} sessions in a single year`,
     unlocked:!!summitY,detail:summitY?`Achieved in ${summitY}`:'',hint:`Best year: ${maxYear}/${ANNUAL_TARGET}`},
    {emoji:'⚡',name:'Unstoppable',desc:'30 consecutive training days',
     unlocked:maxStreak>=30,detail:maxStreak>=30?`Streak: ${maxStreak} days`:'',hint:`Longest streak: ${maxStreak}/30 days`},
    {emoji:'🎯',name:'Type Master',desc:'100 sessions in one type',
     unlocked:!!topCatE,detail:topCatE?`${topCatE[0]}: ${topCatE[1]} sessions`:'',hint:`Best type: ${Math.max(...Object.values(catCounts),0)}/100`},
  ];
}

// ══════════════════════════════════════════════════════════════════════════════
// MODAL
// ══════════════════════════════════════════════════════════════════════════════
function openModal(dateKey,evs){
  document.getElementById('modalDate').textContent=parseDate(dateKey).toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  document.getElementById('modalEvs').innerHTML=evs.map(e=>{
    const color=CAT_COLORS[e.category],dur=fmtHours(e.duration_min);
    const startT=fmtTime(e.dtstart),endT=e.duration_min?fmtTime(addMins(e.dtstart,e.duration_min)):'';
    return`<div class="modal-ev"><div class="modal-ev-name">${e.summary}</div><div class="modal-ev-row">
      <span class="cat-badge" style="background:${color}">${e.category}</span>
      ${startT?`<span>${startT}${endT?' – '+endT:''}</span>`:''}
      ${dur?`<span>${dur}</span>`:''}
    </div></div>`;
  }).join('');
  document.getElementById('modalOv').classList.add('open');
}
function closeModal(){document.getElementById('modalOv').classList.remove('open');}
function handleOv(e){if(e.target===document.getElementById('modalOv'))closeModal();}

// ══════════════════════════════════════════════════════════════════════════════
// CONTROLS
// ══════════════════════════════════════════════════════════════════════════════
function setMode(m){
  trendMode=m;
  document.getElementById('mTotal').classList.toggle('active',m==='total');
  document.getElementById('mByCat').classList.toggle('active',m==='bycat');
  document.getElementById('filterRow').style.display=m==='bycat'?'flex':'none';
  trendOffset=0;renderTrend(getFiltered());
}
function setGran(g){
  if(range!=='custom') return;
  customGranOverride=g;updatePeriodUI();trendOffset=0;renderTrend(getFiltered());
}
function setMetric(m){
  metric=m;
  document.getElementById('mCount').classList.toggle('active',m==='count');
  document.getElementById('mHours').classList.toggle('active',m==='hours');
  renderTrend(getFiltered());
}
function page(dir){trendOffset=Math.max(0,trendOffset-dir);renderTrend(getFiltered());}
function applyCustom(){
  cStart=document.getElementById('cs').value;
  cEnd=document.getElementById('ce').value;
  if(cStart&&cEnd){updatePeriodUI();refresh();}
}
function applyBtCustom(){
  btCStart=document.getElementById('btCs').value;
  btCEnd=document.getElementById('btCe').value;
  if(btCStart&&btCEnd) renderByType();
}
function refresh(){
  trendOffset=0;
  const evs=getFiltered();
  updateCards(evs);
  const avail=availCats(evs);
  renderDD(avail);renderFilterTags(avail);renderTrend(evs);
  if(document.getElementById('tab-bytype').classList.contains('active')) renderByType();
}

// Tab buttons
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    moveTabIndicator(btn);
    const id=btn.dataset.tab;
    switchTab(id);
    setTimeout(()=>{
      if(id==='bytype') renderByType();
      if(id==='calendar') renderCalendar();
      if(id==='progress') renderProgress();
    },220);
  });
});

// Time range buttons
document.querySelectorAll('#timeRange button').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#timeRange button').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    range=btn.dataset.r;
    if(range!=='custom') customGranOverride=null;
    updatePeriodUI();
    const cr=document.getElementById('customRow');
    if(range==='custom'){cr.classList.add('show');return;}
    cr.classList.remove('show');refresh();
  });
});

// By Type time range buttons
document.querySelectorAll('#btTimeRange button').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#btTimeRange button').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');btRange=btn.dataset.bt;
    const cr=document.getElementById('btCustomRow');
    if(btRange==='custom'){cr.classList.add('show');return;}
    cr.classList.remove('show');renderByType();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════════
(function init(){
  // Set GitHub links
  document.getElementById('landGH').href=GITHUB_URL;
  document.getElementById('appLogo').textContent=CONFIG.dashboard_title||'Workout';
  document.title=CONFIG.dashboard_title||'Workout';

  // Date input defaults
  const ts=toStr(today());
  ['ce','cs','btCe','btCs'].forEach(id=>{
    const el=document.getElementById(id);
    if(el){el.max=ts;if(id==='ce'||id==='btCe') el.value=ts;}
  });

  updatePeriodUI();
  update30d();
  // Don't auto-refresh — dashboard init happens when entering from landing
})();
</script>
</body>
</html>
"""

def generate(data_dir, output_path, script_dir):
    cfg = load_config(script_dir)
    categories = cfg["categories"]
    print("Loading .ics files...")
    raw = load_all_events(data_dir)
    print(f"  Raw events: {len(raw)}")
    deduped = deduplicate(raw)
    print(f"  After dedup: {len(deduped)}")
    events = process_events(deduped, categories)
    events.sort(key=lambda e: e["date"])
    print(f"  Workout events: {len(events)}")
    cats = Counter(e["category"] for e in events)
    print("\nCategory breakdown:")
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")
    html = HTML_TEMPLATE
    html = html.replace("__EVENTS_JSON__", json.dumps(events, ensure_ascii=False))
    html = html.replace("__CONFIG_JSON__", json.dumps(cfg, ensure_ascii=False))
    html = html.replace("__DASHBOARD_TITLE__", cfg.get("dashboard_title", "Workout"))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nGenerated: {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate(
        os.path.join(script_dir, "data"),
        os.path.join(script_dir, "dashboard.html"),
        script_dir
    )
