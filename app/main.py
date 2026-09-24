# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api import router as api_router

app = FastAPI(title="FitSense AI - Personalized Meal Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#080b14"><title>FitSense AI</title>
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-height:100vh;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#f8f9ff;background:radial-gradient(circle at 12% 8%,rgba(99,102,241,.24),transparent 28%),radial-gradient(circle at 88% 16%,rgba(20,184,166,.18),transparent 25%),#080b14}.shell{width:min(1120px,calc(100% - 36px));margin:auto;padding:26px 0 55px}nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:65px}.brand{display:flex;align-items:center;gap:11px;font-weight:760}.logo{width:37px;height:37px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(135deg,#7c3aed,#14b8a6)}.pill,.btn{border:1px solid rgba(255,255,255,.11);border-radius:999px;background:rgba(255,255,255,.055);color:#d9dcef;text-decoration:none;padding:10px 15px;backdrop-filter:blur(18px)}.hero{max-width:800px;margin-bottom:48px}.eyebrow{display:inline-block;color:#b9c0d7;font-size:.78rem;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);padding:7px 11px;border-radius:999px;margin-bottom:20px}h1{font-size:clamp(3.2rem,7vw,6rem);line-height:.95;letter-spacing:-.065em;margin:0 0 24px}h1 span{background:linear-gradient(110deg,#fff,#b9b7ff,#72e8d6);background-clip:text;-webkit-background-clip:text;color:transparent}.hero p{color:#a9b0c6;font-size:1.05rem;line-height:1.7;max-width:680px}.tabs{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:18px}.tab{cursor:pointer;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:#aeb5ca;padding:10px 14px;border-radius:999px}.tab.active{background:#f4f3ff;color:#111325}.panel{display:none;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.055);backdrop-filter:blur(22px);border-radius:25px;padding:28px;box-shadow:0 22px 80px rgba(0,0,0,.2)}.panel.active{display:block}.panel h2{margin:0 0 7px;font-size:1.45rem}.sub{margin:0 0 25px;color:#949db7;line-height:1.55}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.full{grid-column:1/-1}label{display:block;font-size:.8rem;color:#b8bfd2;margin:0 0 7px}input,textarea{width:100%;border:1px solid rgba(255,255,255,.11);border-radius:14px;background:rgba(4,7,15,.5);color:#fff;padding:13px 14px;outline:none;font:inherit}input:focus,textarea:focus{border-color:#8b86ff;box-shadow:0 0 0 3px rgba(124,58,237,.12)}textarea{min-height:115px;resize:vertical}.file{padding:11px}.primary{cursor:pointer;border:0;border-radius:14px;padding:13px 18px;background:linear-gradient(135deg,#8178ff,#36cdb8);color:#07100f;font-weight:760;font-size:.92rem}.primary:disabled{opacity:.55;cursor:wait}.result{display:none;margin-top:20px;padding:18px;border:1px solid rgba(255,255,255,.09);border-radius:17px;background:rgba(3,6,13,.46);color:#dce0ef;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}.result.show{display:block}.result.error{border-color:rgba(248,113,113,.35);color:#fecaca}.loader{display:none;margin-left:10px;color:#9da6bf;font-size:.85rem}.loader.show{display:inline}.note{color:#727c97;font-size:.78rem;margin-top:13px}.footer{margin-top:42px;display:flex;justify-content:space-between;color:#68728c;font-size:.78rem}.footer a{color:#8e97b0;text-decoration:none}@media(max-width:700px){nav{margin-bottom:45px}.formgrid{grid-template-columns:1fr}.full{grid-column:auto}.panel{padding:21px}h1{font-size:3.45rem}.footer{flex-direction:column;gap:10px}}
</style>
</head>
<body><main class="shell">
<nav><div class="brand"><div class="logo">✦</div>FitSense AI</div><a class="pill" href="/docs">Developer API ↗</a></nav>
<section class="hero"><div class="eyebrow">AI-powered nutrition companion</div><h1>Eat smarter.<br><span>Feel better.</span></h1><p>Analyze a meal, talk to your AI meal coach, view your nutrition report, or get a personalized daily health tip — directly from this page.</p></section>

<div class="tabs">
<button class="tab active" data-tab="meal">Meal Analysis</button><button class="tab" data-tab="coach">AI Meal Coach</button><button class="tab" data-tab="report">Nutrition Report</button><button class="tab" data-tab="tip">Daily Health Tip</button>
</div>

<section id="meal" class="panel active"><h2>Analyze your meal</h2><p class="sub">Upload a food photo. This also creates your FitSense profile if the User ID is new.</p>
<form id="mealForm" class="formgrid"><div><label>User ID</label><input name="user_id" placeholder="e.g. vikas01" required></div><div><label>Meal photo</label><input class="file" name="image" type="file" accept="image/*" required></div><div><label>Height (cm)</label><input name="height" type="number" step="0.1" placeholder="178"></div><div><label>Weight (kg)</label><input name="weight" type="number" step="0.1" placeholder="75"></div><div class="full"><button class="primary" type="submit">Analyze meal</button><span class="loader">Analyzing with AI…</span></div></form><div id="mealResult" class="result"></div></section>

<section id="coach" class="panel"><h2>Chat with your meal coach</h2><p class="sub">Ask questions using the context of meals already logged under your User ID.</p>
<form id="coachForm" class="formgrid"><div class="full"><label>User ID</label><input name="user_id" placeholder="Your existing User ID" required></div><div class="full"><label>Your question</label><textarea name="message" placeholder="How balanced were my meals today?" required></textarea></div><div class="full"><button class="primary" type="submit">Ask FitSense</button><span class="loader">Thinking…</span></div></form><div id="coachResult" class="result"></div></section>

<section id="report" class="panel"><h2>Nutrition report</h2><p class="sub">Generate your nutrition summary from your logged meal history.</p>
<form id="reportForm" class="formgrid"><div class="full"><label>User ID</label><input name="user_id" placeholder="Your existing User ID" required></div><div class="full"><button class="primary" type="submit">Generate report</button><span class="loader">Building report…</span></div></form><div id="reportResult" class="result"></div></section>

<section id="tip" class="panel"><h2>Daily health tip</h2><p class="sub">Get a personalized AI-generated tip using your FitSense data.</p>
<form id="tipForm" class="formgrid"><div class="full"><label>User ID</label><input name="user_id" placeholder="Your existing User ID" required></div><div class="full"><button class="primary" type="submit">Get today's tip</button><span class="loader">Generating tip…</span></div></form><div id="tipResult" class="result"></div></section>

<div class="note">Tip: use the same User ID across features so FitSense can retrieve the profile and meals you created through Meal Analysis.</div>
<footer class="footer"><span>FitSense AI · Personalized Meal Assistant</span><span><a href="/docs">Swagger API</a> · <a href="/redoc">ReDoc</a></span></footer>
</main>
<script>
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab,.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active')});
function state(form,on){form.querySelector('button').disabled=on;form.querySelector('.loader').classList.toggle('show',on)}
function show(id,data,ok=true){const el=document.getElementById(id);el.className='result show'+(ok?'':' error');if(typeof data==='string')el.textContent=data;else el.textContent=JSON.stringify(data,null,2)}
async function parse(r){let d;try{d=await r.json()}catch{d=await r.text()}if(!r.ok)throw new Error(typeof d==='object'?(d.detail||JSON.stringify(d)):d);return d}
mealForm.onsubmit=async e=>{e.preventDefault();state(mealForm,true);try{const d=await parse(await fetch('/upload',{method:'POST',body:new FormData(mealForm)}));show('mealResult',d)}catch(x){show('mealResult',x.message,false)}finally{state(mealForm,false)}};
coachForm.onsubmit=async e=>{e.preventDefault();state(coachForm,true);try{const d=await parse(await fetch('/chat-meal-coach/',{method:'POST',body:new FormData(coachForm)}));show('coachResult',d.reply||d)}catch(x){show('coachResult',x.message,false)}finally{state(coachForm,false)}};
reportForm.onsubmit=async e=>{e.preventDefault();state(reportForm,true);try{const id=encodeURIComponent(new FormData(reportForm).get('user_id'));const d=await parse(await fetch('/generate-daily-report/'+id));show('reportResult',d)}catch(x){show('reportResult',x.message,false)}finally{state(reportForm,false)}};
tipForm.onsubmit=async e=>{e.preventDefault();state(tipForm,true);try{const id=encodeURIComponent(new FormData(tipForm).get('user_id'));const d=await parse(await fetch('/daily-tip/'+id));show('tipResult',d.daily_tip||d)}catch(x){show('tipResult',x.message,false)}finally{state(tipForm,false)}};
</script></body></html>
    """
