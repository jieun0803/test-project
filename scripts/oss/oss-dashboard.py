#!/usr/bin/env python3
"""Build a self-contained HTML OSS dashboard from CycloneDX SBOMs.

Usage:
  python3 scripts/oss/oss-dashboard.py SBOM.json [SBOM.json ...] [-o oss-dashboard.html] [--title T]
  python3 scripts/oss/oss-dashboard.py sboms/web/              # every *.json in the folder

Release label = file name without .json (e.g. sboms/web/1.2.0.json -> 1.2.0); releases are
ordered by version. The page shows:
  1. License distribution of the latest release (policy bucket per license, oss-policy.md)
  2. SBOM change timeline across releases: component count, added / removed, risk count
     (needs 2+ SBOMs)
No network or CDN: data and rendering code are inlined. Exit code: 0 written, 3 error.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
from pathlib import Path
from oss_paths import safe_path  # CLI paths must stay inside the working directory

_here = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("sbomdiff", _here / "sbom-diff.py")
sd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sd)
audit = sd.audit


def releases(paths: list[str]) -> list[tuple[str, Path]]:
    files: list[Path] = []
    for p in map(Path, paths):
        files += sorted(p.glob("*.json")) if p.is_dir() else [p]
    return sorted(((f.stem, f) for f in files), key=lambda r: sd.version_tuple(r[0]))


def build(paths: list[str]) -> dict:
    policy, cache = audit.load_policy(), audit.load_cache()
    out = []
    prev = None
    for label, f in releases(paths):
        comps = sd.load(str(f))
        pkgs = {}
        for key, c in comps.items():
            lic = sd.comp_license(c) or (cache.get(key) or ("NOASSERTION",))[0]
            pkgs[f"{key[0]}:{key[1]}"] = {"version": c.get("version") or "", "license": lic,
                                          "policy": audit.evaluate(lic, policy)}
        rel = {"label": label, "file": str(f), "total": len(pkgs), "packages": pkgs,
               "risk": {b: sum(p["policy"] == b for p in pkgs.values()) for b in audit.RANK}}
        if prev:
            rel["added"] = sorted(pkgs.keys() - prev.keys())
            rel["removed"] = sorted(prev.keys() - pkgs.keys())
        prev = pkgs
        out.append(rel)
    return {"releases": out}


PAGE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--s1:#2a78d6;--add:#2a78d6;--rem:#e34948;
--good:#0ca30c;--warn:#fab219;--crit:#d03b3b}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--page:#0d0d0d;
--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--s1:#3987e5;--add:#3987e5;--rem:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--add:#3987e5;--rem:#e66767}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:32px 0 4px}.sub{color:var(--ink2);margin:0 0 16px;overflow-wrap:anywhere}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:16px;margin-top:12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tile .v{font-size:28px;font-weight:600}.tile .k{color:var(--ink2);display:flex;gap:6px;align-items:center}
.badge{display:inline-flex;gap:4px;align-items:center;font-size:12px;color:var(--ink2);white-space:nowrap}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:none}
.sx{overflow-x:auto;-webkit-overflow-scrolling:touch}svg{display:block;width:100%;min-width:640px;height:auto;overflow:visible}svg text{fill:var(--muted);font-size:12px}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--ink2);font-size:13px;margin-bottom:8px}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);
border-radius:8px;padding:8px 10px;font-size:13px;box-shadow:0 4px 16px rgba(0,0,0,.15);display:none;max-width:320px;z-index:9}
details{margin-top:12px}summary{cursor:pointer;color:var(--ink2)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:560px;font-size:13px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}th{color:var(--ink2);font-weight:600;white-space:nowrap}
.empty{color:var(--ink2)}
</style></head><body><main>
<h1>__TITLE__</h1><p class="sub" id="sub"></p>
<h2>라이선스 분포</h2><p class="sub" id="distSub"></p>
<div class="tiles" id="tiles"></div>
<div class="card"><div id="dist" class="sx"></div>
<details><summary>표로 보기</summary><div class="tw"><table id="distTable"></table></div></details></div>
<h2>SBOM 변경 타임라인</h2><p class="sub" id="tlSub"></p>
<div id="tl"></div>
<div id="tip" role="tooltip"></div>
</main>
<script>
const DATA = __DATA__;
const POL = {"Allowed":{c:"var(--good)",i:"✓",t:"Allowed"},"Review Required":{c:"var(--warn)",i:"!",t:"Review"},
             "Blocked":{c:"var(--crit)",i:"✕",t:"Blocked"}};
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const badge = p => `<span class="badge"><span class="dot" style="background:${POL[p].c}"></span>${POL[p].i} ${POL[p].t}</span>`;
const tip = document.getElementById("tip");
function showTip(e, h){tip.innerHTML=h;tip.style.display="block";
  const x=Math.min(e.clientX+14, innerWidth-tip.offsetWidth-8), y=Math.min(e.clientY+14, innerHeight-tip.offsetHeight-8);
  tip.style.left=x+"px";tip.style.top=y+"px";}
const hideTip = () => tip.style.display = "none";
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent){const n=document.createElementNS(NS,tag);for(const k in attrs)n.setAttribute(k,attrs[k]);
  parent&&parent.appendChild(n);return n;}
function hover(node, html){node.addEventListener("mousemove",e=>showTip(e,html));node.addEventListener("mouseleave",hideTip);}

const R = DATA.releases, last = R[R.length-1];
document.getElementById("sub").textContent =
  `릴리스 ${R.length}개 (${R.map(r=>r.label).join(" → ")}) · 정책: .cursor/oss-policy.md`;

// ---------- 1. License distribution (latest release)
document.getElementById("distSub").textContent = `${last.label} 기준 · 컴포넌트 ${last.total}개 · ${last.file}`;
document.getElementById("tiles").innerHTML =
  `<div class="card tile"><div class="k">전체 컴포넌트</div><div class="v">${last.total}</div></div>` +
  ["Allowed","Review Required","Blocked"].map(p =>
    `<div class="card tile"><div class="k">${badge(p)}</div><div class="v">${last.risk[p]}</div></div>`).join("");
const byLic = {};
for (const [name, p] of Object.entries(last.packages)) {
  const l = p.license === "NOASSERTION" ? "Unknown (NOASSERTION)" : p.license;
  (byLic[l] ||= {policy:p.policy, pkgs:[]}).pkgs.push(name);
}
let lic = Object.entries(byLic).sort((a,b)=>b[1].pkgs.length-a[1].pkgs.length || a[0].localeCompare(b[0]));
const MAXBARS = 12;
if (lic.length > MAXBARS) {   // fold the tail into "Other" (keeps worst policy of the folded group)
  const tail = lic.slice(MAXBARS-1), rank = {"Allowed":0,"Review Required":1,"Blocked":2};
  lic = lic.slice(0, MAXBARS-1).concat([[`기타 ${tail.length}종`, {policy: tail.map(t=>t[1].policy)
    .reduce((a,b)=>rank[b]>rank[a]?b:a), pkgs: tail.flatMap(t=>t[1].pkgs), other: tail.map(t=>t[0])}]]);
}
(function distChart(){
  const W=1000, LW=330, BW=W-LW-150, rowH=30, H=lic.length*rowH+8, max=Math.max(...lic.map(l=>l[1].pkgs.length));
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"라이선스별 컴포넌트 수"},document.getElementById("dist"));
  lic.forEach(([name,g],i)=>{
    const y=i*rowH+4, w=Math.max(4, g.pkgs.length/max*BW), short=name.length>44?name.slice(0,42)+"…":name;
    const t=el("text",{x:LW-10,y:y+rowH/2+4,"text-anchor":"end"},svg); t.textContent=short; t.style.fill="var(--ink2)";
    el("rect",{x:LW,y:y+5,width:w,height:rowH-12,rx:4,fill:"var(--s1)"},svg);
    const v=el("text",{x:LW+w+8,y:y+rowH/2+4},svg); v.textContent=g.pkgs.length; v.style.fill="var(--ink)";
    const pb=el("text",{x:LW+w+40,y:y+rowH/2+4},svg); pb.textContent=`${POL[g.policy].i} ${POL[g.policy].t}`;
    pb.style.fill="var(--ink2)";
    const hit=el("rect",{x:0,y,width:W,height:rowH,fill:"transparent"},svg);
    hover(hit, `<b>${esc(name)}</b><br>${g.pkgs.length}개 · ${badge(g.policy)}<br><span style="color:var(--ink2)">`+
      esc((g.other? g.other.join(", ") : g.pkgs.slice(0,8).join(", ")) + (!g.other && g.pkgs.length>8?` 외 ${g.pkgs.length-8}`:""))+"</span>");
  });
})();
document.getElementById("distTable").innerHTML = "<tr><th>패키지</th><th>버전</th><th>라이선스</th><th>정책</th></tr>" +
  Object.entries(last.packages).sort((a,b)=>({"Blocked":0,"Review Required":1,"Allowed":2}[a[1].policy]-
    {"Blocked":0,"Review Required":1,"Allowed":2}[b[1].policy]) || a[0].localeCompare(b[0]))
  .map(([n,p])=>`<tr><td>${esc(n)}</td><td>${esc(p.version)}</td><td>${esc(p.license)}</td><td>${badge(p.policy)}</td></tr>`).join("");

// ---------- 2. Timeline
const tl = document.getElementById("tl");
if (R.length < 2) {
  document.getElementById("tlSub").textContent = "SBOM이 2개 이상이어야 타임라인을 그립니다.";
} else {
  document.getElementById("tlSub").textContent = `${R[0].label} → ${last.label}`;
  const W=1000, L=48, Rm=16, step=(W-L-Rm)/R.length, xs=i=>L+step*(i+0.5);  // band layout: half-slot inset
  const ticks = (max) => { const s=Math.max(1,Math.ceil(max/4)); const t=[]; for(let v=0;v<=max+s-1;v+=s)t.push(v); return t; };

  // 2a. total components (line)
  const c1=document.createElement("div"); c1.className="card"; c1.innerHTML="<b>릴리스별 컴포넌트 수</b>"; tl.appendChild(c1);
  const H1=220, T=16, B=28, tmax=ticks(Math.max(...R.map(r=>r.total))), ymax=tmax[tmax.length-1]||1;
  const y1=v=>T+(H1-T-B)*(1-v/ymax);
  const w1=document.createElement("div"); w1.className="sx"; c1.appendChild(w1);
  const s1=el("svg",{viewBox:`0 0 ${W} ${H1}`,role:"img","aria-label":"릴리스별 컴포넌트 수 추이"},w1);
  tmax.forEach(v=>{el("line",{x1:L,x2:W-Rm,y1:y1(v),y2:y1(v),stroke:v?"var(--grid)":"var(--axis)"},s1);
    const t=el("text",{x:L-8,y:y1(v)+4,"text-anchor":"end"},s1);t.textContent=v;});
  el("polyline",{points:R.map((r,i)=>`${xs(i)},${y1(r.total)}`).join(" "),fill:"none",stroke:"var(--s1)","stroke-width":2,
    "stroke-linejoin":"round"},s1);
  R.forEach((r,i)=>{el("circle",{cx:xs(i),cy:y1(r.total),r:4,fill:"var(--s1)",stroke:"var(--surface)","stroke-width":2},s1);
    const t=el("text",{x:xs(i),y:H1-8,"text-anchor":"middle"},s1);t.textContent=r.label;});
  const v=el("text",{x:xs(R.length-1)-8,y:y1(last.total)-10,"text-anchor":"end"},s1);v.textContent=last.total;v.style.fill="var(--ink)";
  const cross=el("line",{y1:T,y2:H1-B,stroke:"var(--axis)",visibility:"hidden"},s1);
  R.forEach((r,i)=>{const h=el("rect",{x:xs(i)-step/2,y:0,width:step||W,height:H1,fill:"transparent"},s1);
    h.addEventListener("mouseenter",()=>{cross.setAttribute("x1",xs(i));cross.setAttribute("x2",xs(i));cross.setAttribute("visibility","visible");});
    h.addEventListener("mouseleave",()=>cross.setAttribute("visibility","hidden"));
    hover(h,`<b>${esc(r.label)}</b><br>컴포넌트 ${r.total}개<br>${badge("Blocked")} ${r.risk.Blocked} · ${badge("Review Required")} ${r.risk["Review Required"]}`);});

  // 2b. added / removed (diverging bars)
  const c2=document.createElement("div"); c2.className="card";
  c2.innerHTML=`<b>릴리스별 추가 / 삭제</b><div class="legend"><span><span class="dot" style="background:var(--add)"></span> 추가 (위)</span>
    <span><span class="dot" style="background:var(--rem)"></span> 삭제 (아래)</span></div>`; tl.appendChild(c2);
  const D=R.slice(1), H2=240, amax=Math.max(1,...D.map(r=>Math.max(r.added.length,r.removed.length)));
  const at=ticks(amax), am=at[at.length-1], mid=T+(H2-T-B)/2, sc=v=>v/am*((H2-T-B)/2);
  const w2=document.createElement("div"); w2.className="sx"; c2.appendChild(w2);
  const s2=el("svg",{viewBox:`0 0 ${W} ${H2}`,role:"img","aria-label":"릴리스별 추가 삭제 컴포넌트 수"},w2);
  at.forEach(t=>[1,-1].forEach(sg=>{if(!t&&sg<0)return; el("line",{x1:L,x2:W-Rm,y1:mid-sg*sc(t),y2:mid-sg*sc(t),
    stroke:t?"var(--grid)":"var(--axis)"},s2); const tx=el("text",{x:L-8,y:mid-sg*sc(t)+4,"text-anchor":"end"},s2); tx.textContent=t;}));
  const bw=Math.min(40,step*0.35);
  D.forEach((r,j)=>{const i=j+1, x=xs(i)-bw/2;
    if(r.added.length) el("path",{d:bar(x,mid-1,bw,sc(r.added.length),-1),fill:"var(--add)"},s2);
    if(r.removed.length) el("path",{d:bar(x,mid+1,bw,sc(r.removed.length),1),fill:"var(--rem)"},s2);
    const t=el("text",{x:xs(i),y:H2-6,"text-anchor":"middle"},s2);t.textContent=`${R[j].label}→${r.label}`;
    const h=el("rect",{x:xs(i)-step/2,y:0,width:step,height:H2,fill:"transparent"},s2);
    hover(h,`<b>${esc(R[j].label)} → ${esc(r.label)}</b><br>추가 ${r.added.length}: ${esc(r.added.slice(0,10).join(", ")||"-")}`+
      `<br>삭제 ${r.removed.length}: ${esc(r.removed.slice(0,10).join(", ")||"-")}`);});
  function bar(x,y0,w,h,dir){ if(h<=0) return ""; const r=Math.min(4,h,w/2), y1=y0+dir*h;
    return dir<0 ? `M${x},${y0}V${y1+r}Q${x},${y1} ${x+r},${y1}H${x+w-r}Q${x+w},${y1} ${x+w},${y1+r}V${y0}Z`
                 : `M${x},${y0}V${y1-r}Q${x},${y1} ${x+r},${y1}H${x+w-r}Q${x+w},${y1} ${x+w},${y1-r}V${y0}Z`; }

  // 2c. table
  const c3=document.createElement("div"); c3.className="card";
  c3.innerHTML="<b>릴리스별 변경 내역</b><div class='tw'><table><tr><th>릴리스</th><th>컴포넌트</th><th>추가</th><th>삭제</th><th>정책 위험</th></tr>"+
    R.map(r=>`<tr><td>${esc(r.label)}</td><td>${r.total}</td><td>${r.added?esc(r.added.join(", ")||"-"):"(기준)"}</td>`+
      `<td>${r.removed?esc(r.removed.join(", ")||"-"):"(기준)"}</td><td>${badge("Blocked")} ${r.risk.Blocked} · ${badge("Review Required")} ${r.risk["Review Required"]}</td></tr>`).join("")+
    "</table></div>"; tl.appendChild(c3);
}
</script></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sboms", nargs="+")
    ap.add_argument("-o", "--output", default="oss-dashboard.html")
    ap.add_argument("--title", default="OSS 라이선스 대시보드")
    a = ap.parse_args()
    try:
        out = safe_path(a.output, "--output")
        data = build([str(safe_path(s, "SBOM")) for s in a.sboms])
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    if not data["releases"]:
        print("error: no SBOM files found", file=sys.stderr)
        return 3
    page = PAGE.replace("__TITLE__", html.escape(a.title)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out.write_text(page, encoding="utf-8")
    last = data["releases"][-1]
    print(f"Dashboard: {a.output} — {len(data['releases'])} release(s), latest {last['label']}: "
          f"{last['total']} components, Blocked {last['risk']['Blocked']}, Review {last['risk']['Review Required']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
