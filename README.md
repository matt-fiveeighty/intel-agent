# Brand Ad Intelligence Agent

Agency Five Eighty internal tool. Scrapes brand ad copy across Meta Ad Library, social, ecom, and digital channels — then synthesizes brand voice, generates on-brand PDP copy, and exports a formatted PDF report.

## Stack

- **Next.js 15** (App Router, TypeScript)
- **Anthropic Claude** (Opus 4.6 with web search)
- **ReportLab** (Python PDF generation)

## Setup

```bash
# 1. Install JS dependencies
npm install

# 2. Install Python PDF dependencies
pip3 install reportlab

# 3. Add your API key
cp .env.local.example .env.local
# Edit .env.local and add your ANTHROPIC_API_KEY

# 4. Run locally
npm run dev
```

Open http://localhost:3000, enter a brand name, and hit Run Agent.

## How It Works

1. Meta Ad Library — Claude web-searches for recent paid ad copy
2. Social / Organic — Instagram, TikTok, Twitter copy
3. Ecom / PDP Channels — Amazon listings, retail promotional copy
4. Digital Ads — Google search ads, display, landing pages
5. PDP Scrape — Top 5 product pages scraped for copy
6. Visuals — Ad image URLs collected and organized by channel
7. Brand Voice Synthesis — Tone words, themes, patterns, avoids
8. Copy Generation — 12 headlines + 5 ultra-short hooks in brand voice
9. PDF Export — 5-section branded report via ReportLab

## Architecture

All Claude API calls are server-side (/api/claude). The API key never touches the browser. PDF generation runs Python via Node child_process and streams the file back as a download.
