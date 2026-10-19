#!/usr/bin/env python3
"""
Superbike Showroom - an immersive localhost site.

Run:   python app.py
Open:  http://localhost:8000      (set PORT=9000 to change the port)

Only the Python standard library is used - nothing to install.
Test-ride bookings are saved to bookings.json next to this file.
"""

import json
import os
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
BOOKINGS_FILE = os.path.join(HERE, "bookings.json")
LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Bike data. Figures are approximate, based on recent model years - always
# confirm against the manufacturer's official spec sheet before buying.
# sound = [base pitch Hz, pitch range Hz] used by the in-browser engine synth.
# ---------------------------------------------------------------------------
BIKES = [
    {
        "id": "zx10r", "name": "Ninja ZX-10R", "maker": "Kawasaki", "color": "#3ddc3c",
        "engine": "Inline-4", "cc": 998, "hp": 203, "torque": 115, "weight": 207,
        "top": 299, "redline": 14500, "sound": [58, 300],
        "tagline": "World Superbike pedigree, road-legal.",
        "desc": "Kawasaki's flagship litre bike and a multiple World Superbike champion's "
                "road-going sibling. Smooth, high-revving inline-four power with a "
                "sharp-handling chassis and an electronics suite built for the track.",
        "features": ["Bosch 6-axis IMU electronics", "Launch control & cornering management",
                     "Showa balance-free fork", "Quickshifter (up & down)",
                     "Titanium finger-follower valve train"],
    },
    {
        "id": "r1", "name": "YZF-R1", "maker": "Yamaha", "color": "#2f6bff",
        "engine": "Crossplane inline-4", "cc": 998, "hp": 200, "torque": 113, "weight": 201,
        "top": 299, "redline": 14500, "sound": [50, 280],
        "tagline": "MotoGP-derived crossplane character.",
        "desc": "The crossplane crankshaft gives the R1 its uneven firing order, a V4-like "
                "growl and strong traction out of corners. Light, compact and "
                "relentlessly technical.",
        "features": ["Crossplane crankshaft", "6-axis IMU with slide control",
                     "Magnesium sub-frame parts", "Wheelie & launch control",
                     "Race-derived aero winglets"],
    },
    {
        "id": "panigale", "name": "Panigale V4", "maker": "Ducati", "color": "#e3120b",
        "engine": "Desmosedici Stradale V4", "cc": 1103, "hp": 215, "torque": 126, "weight": 198,
        "top": 300, "redline": 14000, "sound": [64, 330],
        "tagline": "A MotoGP engine with number plates.",
        "desc": "Italian MotoGP technology on the road: a front-facing V4, a lightweight "
                "aluminium monocoque and aerodynamic winglets. Savage on a track, "
                "surprisingly usable on a road.",
        "features": ["Aluminium front frame", "Brembo Stylema brakes",
                     "Ducati Traction Control EVO 3", "Aero winglets",
                     "Öhlins Smart EC semi-active suspension"],
    },
    {
        "id": "s1000rr", "name": "S 1000 RR", "maker": "BMW Motorrad", "color": "#f0f0f0",
        "engine": "Inline-4 with ShiftCam", "cc": 999, "hp": 210, "torque": 113, "weight": 197,
        "top": 303, "redline": 14600, "sound": [60, 310],
        "tagline": "Precision engineering, brutal pace.",
        "desc": "BMW's ShiftCam variable valve timing delivers strong mid-range and a "
                "screaming top end. Famous for razor-sharp electronics and a stable, "
                "confidence-inspiring chassis.",
        "features": ["ShiftCam variable valve timing", "Dynamic Damping Control",
                     "Riding Modes Pro", "Shift assistant Pro",
                     "Optional M Package with carbon wheels"],
    },
    {
        "id": "fireblade", "name": "CBR1000RR-R Fireblade SP", "maker": "Honda", "color": "#d6001c",
        "engine": "Inline-4", "cc": 999, "hp": 214, "torque": 113, "weight": 201,
        "top": 299, "redline": 15000, "sound": [62, 320],
        "tagline": "Born from the RC213V.",
        "desc": "Honda's most extreme road bike, developed straight from its MotoGP program. "
                "A short-stroke engine that loves to scream past 14,000 rpm, with "
                "winglets, Brembo Stylema calipers and Öhlins electronic suspension.",
        "features": ["MotoGP-derived aero package", "Öhlins semi-active suspension",
                     "Brembo Stylema calipers", "Titanium con-rods",
                     "Cornering ABS & wheelie control"],
    },
    {
        "id": "hayabusa", "name": "Hayabusa", "maker": "Suzuki", "color": "#ffb000",
        "engine": "Inline-4", "cc": 1340, "hp": 190, "torque": 150, "weight": 264,
        "top": 299, "redline": 11500, "sound": [48, 230],
        "tagline": "The legend of straight-line speed.",
        "desc": "The icon that started the 300 km/h debate. Less a track weapon, more a "
                "grand-touring rocket with enormous torque, wind-cheating bodywork and "
                "a modern electronics package.",
        "features": ["1340 cc torque monster", "Six-axis IMU electronics",
                     "Launch control", "Active speed limiter at ~299 km/h",
                     "Comfortable long-distance ergonomics"],
    },
    {
        "id": "rsv4", "name": "RSV4 1100 Factory", "maker": "Aprilia", "color": "#b000ff",
        "engine": "65° V4", "cc": 1099, "hp": 217, "torque": 125, "weight": 202,
        "top": 300, "redline": 13500, "sound": [66, 335],
        "tagline": "Multiple-champion V4 with racing DNA.",
        "desc": "A compact 65-degree V4, an electronics package that set the standard for "
                "the class, and Aprilia's World Superbike heritage. A scalpel of a "
                "motorcycle.",
        "features": ["Aprilia Performance Ride Control", "Öhlins NIX fork & TTX shock",
                     "Forged aluminium wheels", "Race-derived aerodynamics",
                     "Compact V4 for mass centralisation"],
    },
]

# ---------------------------------------------------------------------------
# Front-end (single page, no external assets, works offline)
# ---------------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Apex Superbike Showroom</title>
<style>
:root{
  --accent:#3ddc3c;
  --asphalt:#14171b;
  --tarmac:#20252b;
  --kerb:#353c45;
  --chalk:#ece8df;
  --dust:#9aa3ad;
  --head:"Bahnschrift","Arial Narrow","Roboto Condensed","Helvetica Neue",Impact,sans-serif;
  --body:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--asphalt);color:var(--chalk);font-family:var(--body);line-height:1.6;overflow-x:hidden;transition:background .6s}
a{color:inherit}
canvas#lines{position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
main,header.top,footer{position:relative;z-index:1}

header.top{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px clamp(16px,4vw,48px);
  position:sticky;top:0;background:rgba(20,23,27,.82);backdrop-filter:blur(10px);z-index:20;border-bottom:1px solid var(--kerb)}
.logo{font-family:var(--head);font-size:1.5rem;font-weight:700;letter-spacing:.04em;font-style:italic;text-decoration:none}
.logo b{color:var(--accent);transition:color .4s}
nav{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
nav a{text-decoration:none;color:var(--dust);font-size:.95rem}
nav a:hover,nav a:focus-visible{color:var(--chalk)}
button,select,input{font:inherit;color:inherit}
.btn{background:var(--accent);color:#0b0d0f;border:0;padding:12px 22px;font-family:var(--head);font-size:1.05rem;font-weight:700;
  letter-spacing:.03em;cursor:pointer;clip-path:polygon(10px 0,100% 0,calc(100% - 10px) 100%,0 100%);transition:filter .2s,transform .2s}
.btn:hover{filter:brightness(1.12);transform:translateY(-1px)}
.btn.ghost{background:transparent;color:var(--chalk);box-shadow:inset 0 0 0 2px var(--kerb);clip-path:none}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px}

/* ---------- hero ---------- */
.hero{min-height:calc(100vh - 70px);display:grid;grid-template-rows:auto 1fr auto;padding:28px clamp(16px,4vw,48px) 24px}
.tabs{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;scrollbar-width:thin}
.tab{flex:0 0 auto;background:var(--tarmac);border:1px solid var(--kerb);padding:8px 16px;cursor:pointer;color:var(--dust);transition:.25s}
.tab[aria-selected="true"]{background:var(--accent);color:#0b0d0f;border-color:var(--accent);font-weight:600}
.tab:hover:not([aria-selected="true"]){color:var(--chalk);border-color:var(--dust)}
.stage{position:relative;display:grid;align-items:center;justify-items:center;min-height:420px}
.bigname{position:absolute;left:0;top:50%;transform:translateY(-58%);font-family:var(--head);font-weight:700;font-style:italic;
  font-size:clamp(3.5rem,13vw,12rem);line-height:.85;letter-spacing:-.02em;color:transparent;-webkit-text-stroke:2px var(--kerb);
  user-select:none;pointer-events:none;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:clip}
#bike{position:relative;width:min(900px,100%);height:auto;filter:drop-shadow(0 30px 40px rgba(0,0,0,.5));will-change:transform}
.ground{position:absolute;bottom:10%;width:70%;height:6px;background:linear-gradient(90deg,transparent,var(--accent),transparent);opacity:.5;filter:blur(3px)}
.hud{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-end;justify-content:space-between}
.hud .info{max-width:520px}
.hud h1{font-family:var(--head);font-size:clamp(1.8rem,4vw,3rem);line-height:1.05}
.hud .maker{color:var(--accent);font-weight:600}
.hud p.tag{color:var(--dust);margin-top:6px}
.gaugebox{display:flex;align-items:flex-end;gap:20px}
.readout{text-align:right;font-family:var(--head)}
.readout .speed{font-size:3.4rem;line-height:1;font-weight:700}
.readout small{color:var(--dust);font-size:1rem;margin-left:4px}
.throttle{display:flex;flex-direction:column;gap:10px;align-items:stretch}
#rev{touch-action:none;user-select:none;-webkit-user-select:none;padding:16px 28px;font-size:1.2rem}
#rev.on{filter:brightness(1.3);transform:scale(.97)}
.hint{color:var(--dust);font-size:.85rem;text-align:center}

/* ---------- sections ---------- */
section{padding:clamp(48px,8vw,110px) clamp(16px,4vw,48px)}
.wrap{max-width:1180px;margin:0 auto}
h2{font-family:var(--head);font-size:clamp(2rem,5vw,3.6rem);line-height:1;margin-bottom:12px;font-style:italic}
.lead{color:var(--dust);max-width:62ch;margin-bottom:36px}
.specgrid{display:grid;grid-template-columns:1.1fr 1fr;gap:clamp(24px,5vw,64px);align-items:start}
.bar{margin-bottom:20px}
.bar .row{display:flex;justify-content:space-between;margin-bottom:6px}
.bar .row span:last-child{font-family:var(--head);font-size:1.15rem}
.track{height:10px;background:var(--tarmac);position:relative;overflow:hidden}
.fill{position:absolute;inset:0 auto 0 0;width:0;background:var(--accent);transition:width 1.1s cubic-bezier(.2,.8,.2,1)}
ul.feat{list-style:none;margin-top:18px}
ul.feat li{padding:12px 0 12px 22px;border-bottom:1px solid var(--kerb);position:relative}
ul.feat li::before{content:"";position:absolute;left:0;top:50%;width:10px;height:10px;background:var(--accent);transform:translateY(-50%) skewX(-20deg)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:26px}
.stat{background:var(--tarmac);padding:14px 16px;border-left:4px solid var(--accent)}
.stat b{display:block;font-family:var(--head);font-size:1.5rem}
.stat span{color:var(--dust);font-size:.9rem}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:20px;perspective:1000px}
.card{position:relative;background:var(--tarmac);border:1px solid var(--kerb);padding:22px;cursor:pointer;transform-style:preserve-3d;
  transition:transform .15s ease-out,border-color .3s;overflow:hidden;text-align:left;width:100%}
.card::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at var(--mx,50%) var(--my,0%),var(--c),transparent 55%);opacity:0;transition:opacity .3s;mix-blend-mode:screen}
.card:hover{border-color:var(--c)}
.card:hover::before{opacity:.28}
.card .mk{color:var(--c);font-weight:600;font-size:.9rem}
.card h3{font-family:var(--head);font-size:1.7rem;line-height:1.05;margin:4px 0 14px;transform:translateZ(40px)}
.card .mini{display:flex;gap:16px;color:var(--dust);font-size:.92rem;transform:translateZ(20px)}
.card .mini b{color:var(--chalk);font-family:var(--head);font-size:1.2rem}

.cmp{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:26px}
select,input{background:var(--tarmac);border:1px solid var(--kerb);padding:12px 14px;width:100%}
select:focus,input:focus{border-color:var(--accent);outline:none}
.cmprow{display:grid;grid-template-columns:1fr 110px 1fr;gap:14px;align-items:center;margin-bottom:16px}
.cmprow .lbl{text-align:center;color:var(--dust);font-size:.9rem}
.cmprow .side{display:flex;align-items:center;gap:10px}
.cmprow .side.l{flex-direction:row-reverse}
.cmprow .t{flex:1;height:12px;background:var(--tarmac);display:flex}
.cmprow .t.l{justify-content:flex-end}
.cmprow .f{height:100%;width:0;transition:width .9s cubic-bezier(.2,.8,.2,1)}
.cmprow .v{font-family:var(--head);min-width:56px;font-size:1.1rem}
.cmprow .side.l .v{text-align:right}
.win{color:var(--accent)}

form{display:grid;gap:16px;max-width:560px}
label{display:grid;gap:6px;color:var(--dust);font-size:.92rem}
#msg{min-height:1.6em}
#msg.ok{color:var(--accent)} #msg.err{color:#ff6b5e}
footer{padding:30px clamp(16px,4vw,48px);border-top:1px solid var(--kerb);color:var(--dust);font-size:.88rem}

.dot{position:fixed;width:22px;height:22px;border:2px solid var(--accent);border-radius:50%;pointer-events:none;z-index:50;
  transform:translate(-50%,-50%);transition:width .2s,height .2s,background .2s;mix-blend-mode:difference}
.dot.big{width:54px;height:54px;background:rgba(255,255,255,.12)}
.reveal{opacity:0;transform:translateY(24px);transition:opacity .7s,transform .7s}
.reveal.in{opacity:1;transform:none}

@media (max-width:820px){
  .specgrid{grid-template-columns:1fr}
  .cmp{grid-template-columns:1fr}
  .hud{flex-direction:column;align-items:stretch}
  .gaugebox{justify-content:space-between}
  .dot{display:none}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important}
  html{scroll-behavior:auto}
  .reveal{opacity:1;transform:none}
}
</style>
</head>
<body>
<canvas id="lines"></canvas>
<div class="dot" id="dot"></div>

<header class="top">
  <a class="logo" href="#top">APEX<b>.</b>MOTO</a>
  <nav>
    <a href="#specs">Specs</a>
    <a href="#showroom">Showroom</a>
    <a href="#compare">Compare</a>
    <a href="#ride">Book a test ride</a>
    <button class="btn ghost" id="sndBtn" aria-pressed="true">Sound on</button>
  </nav>
</header>

<main id="top">
  <div class="hero">
    <div class="tabs" id="tabs" role="tablist" aria-label="Choose a superbike"></div>

    <div class="stage" id="stage">
      <div class="bigname" id="bigname" aria-hidden="true"></div>
      <div class="ground"></div>
      <svg id="bike" viewBox="0 0 640 320" role="img" aria-label="Side view of the selected motorcycle">
        <g id="bikeBody">
          <!-- swingarm & exhaust -->
          <path d="M150 218 L282 196" stroke="#4a525c" stroke-width="9" stroke-linecap="round"/>
          <path d="M215 205 Q150 215 105 190 L112 180 Q160 200 222 190 Z" fill="#7b838d"/>
          <!-- engine block -->
          <path d="M255 168 L370 168 L388 214 L270 222 Z" fill="#262b31" stroke="#3b424a" stroke-width="3"/>
          <rect x="285" y="176" width="70" height="10" fill="#3b424a"/>
          <rect x="285" y="192" width="70" height="10" fill="#3b424a"/>
          <!-- fork -->
          <path d="M432 138 L486 220" stroke="#aeb6bf" stroke-width="9" stroke-linecap="round"/>
          <path d="M440 148 L492 224" stroke="#6d757e" stroke-width="5" stroke-linecap="round"/>
          <!-- tail + seat -->
          <path id="tail" d="M108 150 Q150 128 214 150 L232 178 L132 182 Z" fill="var(--accent)"/>
          <path d="M165 150 Q205 138 262 150 L262 162 L170 164 Z" fill="#111417"/>
          <!-- fairing / tank -->
          <path id="fairing" d="M205 168 Q250 112 335 116 L405 138 L452 152 L392 186 L242 190 Z" fill="var(--accent)"/>
          <path d="M262 150 Q300 128 350 134 L392 148 L330 160 Z" fill="rgba(0,0,0,.28)"/>
          <path d="M235 184 L400 182 L380 196 L246 198 Z" fill="rgba(0,0,0,.35)"/>
          <!-- screen + headlight -->
          <path d="M404 138 L430 102 L452 140 Z" fill="rgba(210,235,255,.55)"/>
          <path d="M440 140 L470 154 L462 168 L436 158 Z" fill="#fff6c9"/>
          <!-- bars -->
          <path d="M424 110 L398 96" stroke="#aeb6bf" stroke-width="6" stroke-linecap="round"/>
        </g>
        <!-- wheels -->
        <g id="wheelR"><circle cx="150" cy="222" r="70" fill="#0d0f11" stroke="#2c323a" stroke-width="10"/>
          <g id="spokesR" stroke="#9aa3ad" stroke-width="4"></g><circle cx="150" cy="222" r="11" fill="var(--accent)"/></g>
        <g id="wheelF"><circle cx="490" cy="222" r="70" fill="#0d0f11" stroke="#2c323a" stroke-width="10"/>
          <g id="spokesF" stroke="#9aa3ad" stroke-width="4"></g><circle cx="490" cy="222" r="11" fill="var(--accent)"/></g>
        <circle cx="490" cy="222" r="46" fill="none" stroke="#c7ced6" stroke-width="2" opacity=".6"/>
      </svg>
    </div>

    <div class="hud">
      <div class="info">
        <div class="maker" id="hMaker"></div>
        <h1 id="hName"></h1>
        <p class="tag" id="hTag"></p>
      </div>
      <div class="gaugebox">
        <svg id="gauge" width="230" height="130" viewBox="0 0 230 130" aria-hidden="true"></svg>
        <div class="readout"><div class="speed" id="speed">0</div><small>km/h</small>
          <div><span id="rpmTxt">1,200</span><small>rpm</small></div></div>
        <div class="throttle">
          <button class="btn" id="rev">Hold to rev</button>
          <div class="hint">or hold Space</div>
        </div>
      </div>
    </div>
  </div>

  <section id="specs"><div class="wrap specgrid">
    <div class="reveal">
      <h2 id="sName"></h2>
      <p class="lead" id="sDesc"></p>
      <div class="stats" id="stats"></div>
      <ul class="feat" id="feat"></ul>
    </div>
    <div class="reveal" id="bars"></div>
  </div></section>

  <section id="showroom"><div class="wrap">
    <h2 class="reveal">On the showroom floor</h2>
    <p class="lead reveal">Pick any bike to bring it up on the stage above. Move your mouse over a card and it tilts to follow you.</p>
    <div class="grid" id="grid"></div>
  </div></section>

  <section id="compare"><div class="wrap">
    <h2 class="reveal">Head to head</h2>
    <p class="lead reveal">Choose two bikes. The winner of each category is highlighted.</p>
    <div class="cmp"><select id="cA" aria-label="First bike"></select><select id="cB" aria-label="Second bike"></select></div>
    <div id="cmpOut"></div>
  </div></section>

  <section id="ride"><div class="wrap">
    <h2 class="reveal">Book a test ride</h2>
    <p class="lead reveal">Leave your details and we will call you to confirm a slot. Bookings are stored locally in bookings.json.</p>
    <form id="form" class="reveal">
      <label>Your name<input name="name" required maxlength="80" autocomplete="name"></label>
      <label>Phone number<input name="phone" required maxlength="20" inputmode="tel" autocomplete="tel" placeholder="e.g. 98765 43210"></label>
      <label>Bike<select name="bike" id="bBike"></select></label>
      <label>Preferred date<input type="date" name="date" id="bDate" required></label>
      <button class="btn" type="submit">Book my ride</button>
      <div id="msg" role="status"></div>
    </form>
  </div></section>
</main>

<footer>Specs are approximate and vary by model year and market. Check the manufacturer's official figures before you buy. Ride safe and wear your gear.</footer>

<script>
const $=s=>document.querySelector(s);
const S={bikes:[],cur:0,rpm:1200,throttle:0,angle:0,audio:null,sound:true,shake:0};
const MAXES={hp:230,torque:160,top:320};
const fmt=n=>n.toLocaleString('en-IN');

fetch('/api/bikes').then(r=>r.json()).then(b=>{S.bikes=b;init();});

function init(){
  buildSpokes();
  const tabs=$('#tabs');
  S.bikes.forEach((b,i)=>{
    const t=document.createElement('button');t.className='tab';t.role='tab';t.textContent=b.name;
    t.onclick=()=>select(i);tabs.appendChild(t);
  });
  const grid=$('#grid');
  S.bikes.forEach((b,i)=>{
    const c=document.createElement('button');c.className='card reveal';c.style.setProperty('--c',b.color);
    c.innerHTML=`<div class="mk">${b.maker}</div><h3>${b.name}</h3>
      <div class="mini"><span><b>${b.hp}</b> hp</span><span><b>${b.weight}</b> kg</span><span><b>${fmt(b.cc)}</b> cc</span></div>`;
    c.onclick=()=>{select(i);window.scrollTo({top:0,behavior:'smooth'});};
    c.addEventListener('mousemove',e=>{
      const r=c.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;
      c.style.transform=`rotateY(${(x-.5)*14}deg) rotateX(${(.5-y)*14}deg)`;
      c.style.setProperty('--mx',x*100+'%');c.style.setProperty('--my',y*100+'%');
    });
    c.addEventListener('mouseleave',()=>{c.style.transform='';});
    grid.appendChild(c);
  });
  ['#cA','#cB','#bBike'].forEach(sel=>S.bikes.forEach((b,i)=>{
    const o=document.createElement('option');o.value=sel==='#bBike'?b.name:i;o.textContent=`${b.maker} ${b.name}`;$(sel).appendChild(o);}));
  $('#cB').selectedIndex=1;
  $('#cA').onchange=$('#cB').onchange=compare;
  const today=new Date().toISOString().split('T')[0];$('#bDate').min=today;$('#bDate').value=today;
  select(0);compare();observe();
  requestAnimationFrame(loop);
}

function buildSpokes(){
  ['R','F'].forEach(w=>{
    const g=$('#spokes'+w),cx=w==='R'?150:490;let h='';
    for(let i=0;i<10;i++){const a=i*36*Math.PI/180;
      h+=`<line x1="${cx}" y1="222" x2="${cx+58*Math.cos(a)}" y2="${222+58*Math.sin(a)}"/>`;}
    g.innerHTML=h;
  });
}

const cur=()=>S.bikes[S.cur];

function select(i){
  S.cur=i;const b=cur();
  document.documentElement.style.setProperty('--accent',b.color);
  document.querySelectorAll('.tab').forEach((t,k)=>t.setAttribute('aria-selected',k===i));
  $('#bigname').textContent=b.maker.split(' ')[0];
  $('#hMaker').textContent=b.maker;$('#hName').textContent=b.name;$('#hTag').textContent=b.tagline;
  $('#sName').textContent=b.name;$('#sDesc').textContent=b.desc;
  $('#stats').innerHTML=`<div class="stat"><b>${fmt(b.cc)}</b><span>cc</span></div>
    <div class="stat"><b>${b.engine.split(' ')[0]}</b><span>${b.engine}</span></div>
    <div class="stat"><b>${fmt(b.redline)}</b><span>rpm redline</span></div>`;
  $('#feat').innerHTML=b.features.map(f=>`<li>${f}</li>`).join('');
  const rows=[['Power',b.hp,b.hp/MAXES.hp,' hp'],['Torque',b.torque,b.torque/MAXES.torque,' Nm'],
    ['Top speed',b.top,b.top/MAXES.top,' km/h'],['Lightness',b.weight,(300-b.weight)/140,' kg wet']];
  $('#bars').innerHTML=rows.map(r=>`<div class="bar"><div class="row"><span>${r[0]}</span><span>${r[1]}${r[3]}</span></div>
    <div class="track"><div class="fill" data-w="${Math.max(4,Math.min(100,r[2]*100))}"></div></div></div>`).join('');
  setTimeout(()=>document.querySelectorAll('.fill').forEach(f=>f.style.width=f.dataset.w+'%'),60);
  S.rpm=1200;drawGauge();
  const bk=$('#bike');bk.animate([{transform:'translateX(-80px)',opacity:.2},{transform:'none',opacity:1}],{duration:500,easing:'cubic-bezier(.2,.8,.2,1)'});
}

/* ---------- tachometer ---------- */
const GC={x:115,y:112};
const pol=(r,deg)=>{const a=deg*Math.PI/180;return [GC.x+r*Math.cos(a),GC.y+r*Math.sin(a)];};
let gMax=16000;
function drawGauge(){
  const b=cur();gMax=Math.ceil(b.redline/1000)*1000+1000;
  const ang=v=>180+180*v/gMax;
  let h=`<path d="M${pol(98,180)} A98 98 0 0 1 ${pol(98,360)}" fill="none" stroke="#2a3038" stroke-width="3"/>`;
  const [x1,y1]=pol(98,ang(b.redline)),[x2,y2]=pol(98,360);
  h+=`<path d="M${x1} ${y1} A98 98 0 0 1 ${x2} ${y2}" fill="none" stroke="#ff3b30" stroke-width="6"/>`;
  for(let v=0;v<=gMax;v+=1000){
    const [a,b2]=pol(98,ang(v)),[c,d]=pol(86,ang(v)),[e,f]=pol(72,ang(v));
    h+=`<line x1="${a}" y1="${b2}" x2="${c}" y2="${d}" stroke="#9aa3ad" stroke-width="2"/>`;
    if(v%2000===0)h+=`<text x="${e}" y="${f+4}" fill="#9aa3ad" font-size="11" text-anchor="middle">${v/1000}</text>`;
  }
  h+=`<g id="needle"><line x1="${GC.x-14}" y1="${GC.y}" x2="${GC.x-92}" y2="${GC.y}" stroke="var(--accent)" stroke-width="3" stroke-linecap="round"/></g>
      <circle cx="${GC.x}" cy="${GC.y}" r="8" fill="#ece8df"/>`;
  $('#gauge').innerHTML=h;
}

/* ---------- engine sound (synthesised in the browser) ---------- */
function startAudio(){
  if(S.audio)return;
  const C=new (window.AudioContext||window.webkitAudioContext)();
  const o1=C.createOscillator(),o2=C.createOscillator(),o3=C.createOscillator();
  o1.type='sawtooth';o2.type='square';o3.type='triangle';
  const lp=C.createBiquadFilter();lp.type='lowpass';lp.Q.value=4;
  const g=C.createGain();g.gain.value=0;
  const lfo=C.createOscillator(),lg=C.createGain();lfo.frequency.value=38;lg.gain.value=.03;
  lfo.connect(lg);lg.connect(g.gain);
  [o1,o2,o3].forEach(o=>{o.connect(lp);o.start();});lfo.start();
  lp.connect(g);g.connect(C.destination);
  S.audio={C,o1,o2,o3,lp,g,lfo};
}
function updateAudio(){
  const A=S.audio;if(!A)return;
  const b=cur(),k=Math.max(0,(S.rpm-1000)/(b.redline-1000)),t=A.C.currentTime;
  const f=b.sound[0]+k*b.sound[1];
  A.o1.frequency.setTargetAtTime(f,t,.03);A.o2.frequency.setTargetAtTime(f*.5,t,.03);A.o3.frequency.setTargetAtTime(f*1.5,t,.03);
  A.lp.frequency.setTargetAtTime(350+k*3200,t,.05);
  A.lfo.frequency.setTargetAtTime(30+k*60,t,.05);
  const vol=S.sound?(.05+.11*k+(S.throttle?.03:0)):0;
  A.g.gain.setTargetAtTime(vol,t,.05);
}

/* ---------- main animation loop ---------- */
let last=performance.now();
function loop(now){
  const dt=Math.min(.05,(now-last)/1000);last=now;
  const b=cur();
  let target=S.throttle?b.redline:1200;
  if(S.throttle&&S.rpm>b.redline-250)target=b.redline-120+Math.sin(now*.06)*140; // rev limiter bounce
  S.rpm+=(target-S.rpm)*(1-Math.exp(-dt*(S.throttle?1.3:1.9)));
  const k=Math.max(0,(S.rpm-1200)/(b.redline-1200)),speed=Math.round(k*b.top);
  S.angle+=(speed*1.6+30)*dt;
  $('#wheelR').setAttribute('transform',`rotate(${S.angle} 150 222)`);
  $('#wheelF').setAttribute('transform',`rotate(${S.angle} 490 222)`);
  const n=$('#needle');if(n)n.setAttribute('transform',`rotate(${180*S.rpm/gMax} ${GC.x} ${GC.y})`);
  $('#speed').textContent=speed;$('#rpmTxt').textContent=fmt(Math.round(S.rpm/10)*10);
  // chassis shake + squat
  const sh=k*(S.throttle?2.2:.6);
  $('#bikeBody').setAttribute('transform',`translate(${(Math.random()-.5)*sh},${(Math.random()-.5)*sh-k*2}) rotate(${-k*1.2} 150 222)`);
  $('#bigname').style.transform=`translate(${-k*60}px,-58%)`;
  updateAudio();drawLines(dt,k);
  requestAnimationFrame(loop);
}

/* ---------- speed lines background ---------- */
const cv=$('#lines'),cx=cv.getContext('2d');let LN=[];
function resize(){cv.width=innerWidth;cv.height=innerHeight;LN=Array.from({length:70},()=>mk(true));}
function mk(rand){return{x:rand?Math.random()*cv.width:cv.width+50,y:Math.random()*cv.height,l:40+Math.random()*180,s:.4+Math.random()*1.2,a:.05+Math.random()*.2};}
function drawLines(dt,k){
  cx.clearRect(0,0,cv.width,cv.height);
  const col=getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()||'#3ddc3c';
  cx.strokeStyle=col;cx.lineWidth=1.5;
  for(const p of LN){
    const v=(120+k*2600)*p.s;p.x-=v*dt;
    cx.globalAlpha=p.a*(.4+k*1.2);
    cx.beginPath();cx.moveTo(p.x,p.y);cx.lineTo(p.x+p.l*(.4+k*2.4),p.y);cx.stroke();
    if(p.x+p.l*3<0)Object.assign(p,mk(false));
  }
  cx.globalAlpha=1;
}
addEventListener('resize',resize);resize();

/* ---------- throttle controls ---------- */
function throttle(on){
  S.throttle=on?1:0;$('#rev').classList.toggle('on',on);
  if(on){startAudio();if(S.audio&&S.audio.C.state==='suspended')S.audio.C.resume();}
}
const rev=$('#rev');
rev.addEventListener('pointerdown',e=>{e.preventDefault();rev.setPointerCapture(e.pointerId);throttle(true);});
['pointerup','pointercancel','lostpointercapture'].forEach(ev=>rev.addEventListener(ev,()=>throttle(false)));
addEventListener('keydown',e=>{if(e.code==='Space'&&!e.repeat&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)){e.preventDefault();throttle(true);}
  if(e.code==='ArrowRight'&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))select((S.cur+1)%S.bikes.length);
  if(e.code==='ArrowLeft'&&!/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))select((S.cur-1+S.bikes.length)%S.bikes.length);});
addEventListener('keyup',e=>{if(e.code==='Space')throttle(false);});
$('#sndBtn').onclick=e=>{S.sound=!S.sound;e.target.textContent=S.sound?'Sound on':'Sound off';e.target.setAttribute('aria-pressed',S.sound);};

/* ---------- comparison ---------- */
function compare(){
  const A=S.bikes[$('#cA').value],B=S.bikes[$('#cB').value];
  const rows=[['Power','hp',' hp',1],['Torque','torque',' Nm',1],['Top speed','top',' km/h',1],['Weight','weight',' kg',-1],['Capacity','cc',' cc',1]];
  let h=`<div class="cmprow"><div class="side l" style="justify-content:flex-start"><b style="font-family:var(--head);font-size:1.5rem;color:${A.color}">${A.name}</b></div><div></div>
    <div class="side"><b style="font-family:var(--head);font-size:1.5rem;color:${B.color}">${B.name}</b></div></div>`;
  rows.forEach(([lbl,key,u,dir])=>{
    const a=A[key],b=B[key],mx=Math.max(a,b),aw=dir>0?a>=b:a<=b,bw=dir>0?b>=a:b<=a;
    const pa=dir>0?a/mx*100:Math.min(100,mx/a*100),pb=dir>0?b/mx*100:Math.min(100,mx/b*100);
    h+=`<div class="cmprow"><div class="side l"><span class="v ${aw&&a!==b?'win':''}">${fmt(a)}${u}</span><div class="t l"><div class="f" data-w="${pa}" style="background:${A.color}"></div></div></div>
      <div class="lbl">${lbl}</div>
      <div class="side"><span class="v ${bw&&a!==b?'win':''}">${fmt(b)}${u}</span><div class="t"><div class="f" data-w="${pb}" style="background:${B.color}"></div></div></div></div>`;
  });
  $('#cmpOut').innerHTML=h;
  setTimeout(()=>document.querySelectorAll('#cmpOut .f').forEach(f=>f.style.width=f.dataset.w+'%'),40);
}

/* ---------- booking ---------- */
$('#form').addEventListener('submit',async e=>{
  e.preventDefault();const m=$('#msg');m.className='';m.textContent='Sending...';
  const data=Object.fromEntries(new FormData(e.target));
  try{
    const r=await fetch('/api/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const j=await r.json();
    if(r.ok){m.className='ok';m.textContent=`Booked. We will call ${j.name} to confirm the ${data.bike} test ride.`;e.target.reset();$('#bDate').value=new Date().toISOString().split('T')[0];}
    else{m.className='err';m.textContent=j.error||'Could not book. Check your details and try again.';}
  }catch(err){m.className='err';m.textContent='The server is not reachable. Make sure app.py is still running.';}
});

/* ---------- cursor + reveal ---------- */
const dot=$('#dot');
addEventListener('mousemove',e=>{dot.style.left=e.clientX+'px';dot.style.top=e.clientY+'px';
  dot.classList.toggle('big',!!e.target.closest('button,a,select,.card'));});
function observe(){
  const io=new IntersectionObserver(es=>es.forEach(en=>{if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}}),{threshold:.12});
  document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "ApexShowroom/1.0"

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/bikes":
            self._send(200, json.dumps(BIKES))
        elif path.startswith("/api/bikes/"):
            bike = next((b for b in BIKES if b["id"] == path.rsplit("/", 1)[1]), None)
            if bike:
                self._send(200, json.dumps(bike))
            else:
                self._send(404, json.dumps({"error": "Bike not found"}))
        else:
            self._send(404, json.dumps({"error": "Not found"}))

    def do_POST(self):
        if self.path != "/api/book":
            return self._send(404, json.dumps({"error": "Not found"}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 10_000:
                raise ValueError("Request size is invalid.")
            data = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return self._send(400, json.dumps({"error": "Invalid request."}))

        name = str(data.get("name", "")).strip()[:80]
        phone = str(data.get("phone", "")).strip()[:20]
        bike = str(data.get("bike", "")).strip()[:60]
        date = str(data.get("date", "")).strip()[:10]

        if not name:
            return self._send(400, json.dumps({"error": "Please enter your name."}))
        if not re.fullmatch(r"[+\d][\d\s\-]{6,18}", phone):
            return self._send(400, json.dumps({"error": "Please enter a valid phone number."}))
        if bike not in {b["name"] for b in BIKES}:
            return self._send(400, json.dumps({"error": "Please choose a bike from the list."}))
        try:
            if datetime.strptime(date, "%Y-%m-%d").date() < datetime.now().date():
                return self._send(400, json.dumps({"error": "Please choose today or a later date."}))
        except ValueError:
            return self._send(400, json.dumps({"error": "Please choose a valid date."}))

        entry = {"name": name, "phone": phone, "bike": bike, "date": date,
                 "created": datetime.now().isoformat(timespec="seconds")}
        with LOCK:
            try:
                with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                items = []
            items.append(entry)
            with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        self._send(201, json.dumps({"ok": True, "name": name}))

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    port = int(os.environ.get("PORT", 8000))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"\n  Apex Superbike Showroom running at  http://localhost:{port}\n  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Showroom closed.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
