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
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="theme-color" content="#0b1020">
        <title>FitSense AI</title>
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                min-height: 100vh;
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: #f7f8ff;
                background:
                    radial-gradient(circle at 15% 15%, rgba(99,102,241,.28), transparent 30%),
                    radial-gradient(circle at 85% 10%, rgba(45,212,191,.20), transparent 28%),
                    radial-gradient(circle at 70% 85%, rgba(168,85,247,.18), transparent 30%),
                    #080b14;
                overflow-x: hidden;
            }
            .shell {
                width: min(1120px, calc(100% - 40px));
                margin: 0 auto;
                padding: 28px 0 50px;
            }
            nav {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 72px;
            }
            .brand {
                display: flex;
                align-items: center;
                gap: 11px;
                font-weight: 750;
                letter-spacing: -.02em;
                font-size: 1.05rem;
            }
            .logo {
                width: 36px;
                height: 36px;
                display: grid;
                place-items: center;
                border-radius: 12px;
                background: linear-gradient(135deg, #7c3aed, #14b8a6);
                box-shadow: 0 8px 30px rgba(124,58,237,.28);
            }
            .docs {
                color: #c8cce0;
                text-decoration: none;
                font-size: .9rem;
                padding: 9px 14px;
                border: 1px solid rgba(255,255,255,.10);
                border-radius: 999px;
                background: rgba(255,255,255,.04);
                backdrop-filter: blur(14px);
            }
            .docs:hover { background: rgba(255,255,255,.08); }
            .hero { max-width: 790px; }
            .eyebrow {
                display: inline-flex;
                padding: 7px 11px;
                border: 1px solid rgba(255,255,255,.10);
                border-radius: 999px;
                background: rgba(255,255,255,.045);
                color: #b8c0d9;
                font-size: .78rem;
                margin-bottom: 20px;
                backdrop-filter: blur(14px);
            }
            h1 {
                font-size: clamp(3rem, 7vw, 5.9rem);
                line-height: .96;
                letter-spacing: -.065em;
                margin: 0 0 24px;
                font-weight: 800;
            }
            h1 span {
                background: linear-gradient(110deg, #fff 15%, #b9b7ff 52%, #72e8d6);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
            }
            .hero p {
                margin: 0;
                max-width: 680px;
                color: #aab1c8;
                font-size: 1.08rem;
                line-height: 1.7;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 16px;
                margin-top: 52px;
            }
            .card {
                position: relative;
                display: flex;
                flex-direction: column;
                min-height: 210px;
                padding: 25px;
                text-decoration: none;
                color: inherit;
                border: 1px solid rgba(255,255,255,.10);
                border-radius: 24px;
                background: rgba(255,255,255,.055);
                backdrop-filter: blur(22px);
                -webkit-backdrop-filter: blur(22px);
                box-shadow: 0 20px 70px rgba(0,0,0,.20);
                transition: transform .2s ease, border-color .2s ease, background .2s ease;
            }
            .card:hover {
                transform: translateY(-4px);
                border-color: rgba(255,255,255,.22);
                background: rgba(255,255,255,.08);
            }
            .icon {
                width: 44px;
                height: 44px;
                display: grid;
                place-items: center;
                border-radius: 14px;
                background: rgba(255,255,255,.075);
                border: 1px solid rgba(255,255,255,.08);
                font-size: 1.25rem;
                margin-bottom: 26px;
            }
            .card h2 {
                margin: 0 0 9px;
                font-size: 1.15rem;
                letter-spacing: -.025em;
            }
            .card p {
                margin: 0;
                color: #9da6bf;
                line-height: 1.55;
                font-size: .91rem;
                max-width: 420px;
            }
            .arrow {
                position: absolute;
                right: 23px;
                bottom: 22px;
                color: #b9c0d6;
                font-size: 1.1rem;
            }
            .footer {
                display: flex;
                justify-content: space-between;
                gap: 20px;
                margin-top: 48px;
                color: #6f7891;
                font-size: .78rem;
            }
            .footer a { color: #929bb4; text-decoration: none; }
            @media (max-width: 700px) {
                .shell { width: min(100% - 28px, 1120px); }
                nav { margin-bottom: 52px; }
                .grid { grid-template-columns: 1fr; }
                h1 { font-size: 3.4rem; }
                .footer { flex-direction: column; }
            }
        </style>
    </head>
    <body>
        <main class="shell">
            <nav>
                <div class="brand">
                    <div class="logo">✦</div>
                    <span>FitSense AI</span>
                </div>
                <a class="docs" href="/docs">API Docs ↗</a>
            </nav>

            <section class="hero">
                <div class="eyebrow">AI-powered nutrition companion</div>
                <h1>Eat smarter.<br><span>Feel better.</span></h1>
                <p>
                    Explore the FitSense AI API — upload meals for food detection,
                    chat with your meal coach, generate nutrition reports, and get
                    personalized daily health tips.
                </p>
            </section>

            <section class="grid" aria-label="Available FitSense AI features">
                <a class="card" href="/docs#/default/upload_image_upload_post">
                    <div class="icon">◉</div>
                    <h2>Meal Analysis</h2>
                    <p>Upload a meal image and let AI identify food items and process nutrition data.</p>
                    <div class="arrow">↗</div>
                </a>

                <a class="card" href="/docs#/default/chat_meal_coach_chat_meal_coach__post">
                    <div class="icon">⌁</div>
                    <h2>AI Meal Coach</h2>
                    <p>Chat with your personalized meal coach using your logged meal context.</p>
                    <div class="arrow">↗</div>
                </a>

                <a class="card" href="/docs#/default/generate_weekly_report_generate_daily_report__user_id__get">
                    <div class="icon">◫</div>
                    <h2>Nutrition Report</h2>
                    <p>Generate a nutrition summary from your meal history and see your tracked metrics.</p>
                    <div class="arrow">↗</div>
                </a>

                <a class="card" href="/docs#/default/get_daily_health_tip_daily_tip__user_id__get">
                    <div class="icon">✦</div>
                    <h2>Daily Health Tip</h2>
                    <p>Get a daily AI-generated health tip based on your FitSense data.</p>
                    <div class="arrow">↗</div>
                </a>
            </section>

            <footer class="footer">
                <span>FitSense AI · Personalized Meal Assistant</span>
                <a href="/redoc">ReDoc</a>
            </footer>
        </main>
    </body>
    </html>
    """
