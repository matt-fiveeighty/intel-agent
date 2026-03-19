"use client";

import { useState } from "react";

const STAGES = [
  { id: "meta", label: "Meta Ad Library", icon: "📣" },
  { id: "social", label: "Social / Organic", icon: "📱" },
  { id: "ecom", label: "Ecom / PDP Channels", icon: "🛒" },
  { id: "digital", label: "Digital Ads & Web", icon: "💻" },
  { id: "pdp", label: "Scraping 5 PDP Pages", icon: "🔍" },
  { id: "images", label: "Collecting Visuals", icon: "🖼" },
  { id: "synthesize", label: "Synthesizing Brand Voice", icon: "🧠" },
  { id: "headlines", label: "Generating Copy", icon: "✍️" },
  { id: "pdf", label: "Building PDF Report", icon: "📄" },
];

async function callClaude(system: string, user: string, search = false): Promise<string> {
  const res = await fetch("/api/claude", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ system, user, search }),
  });
  const d = await res.json();
  if (!res.ok) throw new Error((d as { error?: string }).error ?? "Claude API error");
  return (d as { text: string }).text;
}

function parseArr(raw: string): string[] {
  try {
    const c = raw.replace(/```json|```/g, "").trim();
    const s = c.indexOf("["), e = c.lastIndexOf("]");
    if (s !== -1 && e !== -1) return JSON.parse(c.slice(s, e + 1)) as string[];
  } catch {}
  return [];
}

function parseObj(raw: string): Record<string, unknown> {
  try {
    const c = raw.replace(/```json|```/g, "").trim();
    const s = c.indexOf("{"), e = c.lastIndexOf("}");
    if (s !== -1 && e !== -1) return JSON.parse(c.slice(s, e + 1)) as Record<string, unknown>;
  } catch {}
  return {};
}

async function searchChannel(brand: string, desc: string): Promise<string[]> {
  const r = await callClaude(
    `Brand intelligence researcher. Extract real advertising copy. Return ONLY a JSON array of strings. No markdown.`,
    `Find recent (6 months) ad copy from "${brand}" on: ${desc}. Short phrases under 120 chars only.`,
    true
  );
  return parseArr(r);
}

interface PdpPage { name: string; url: string; copy: string[]; }
interface ImageItem { url: string; label: string; channel: string; }
interface VoiceData { toneWords?: string[]; themes?: string[]; patterns?: string[]; avoid?: string[]; summary?: string; }
interface CopyData { headlines?: string[]; ultraShort?: string[]; }
interface ReportData { brand: string; voice: VoiceData; copy: CopyData; rawCopy: string[]; pdpPages: PdpPage[]; images: ImageItem[]; channelCopy: Record<string, string[]>; }

async function scrapePDPs(brand: string): Promise<PdpPage[]> {
  const urlRaw = await callClaude(
    `Product research agent. Find PDP page URLs. Return ONLY JSON array: [{"name":"...","url":"..."}]. Max 5. No markdown.`,
    `Find top 5 product detail pages for "${brand}" across: official brand website, Amazon.com, Total Wine or major retailer, Drizly or delivery platform, and one more major retailer. Return actual URLs.`,
    true
  );
  const urls = parseArr(urlRaw) as unknown as Array<{ name?: string; url?: string }>;
  const pages: PdpPage[] = [];
  for (const p of urls.slice(0, 5)) {
    const copyRaw = await callClaude(
      `Copy scraper. Extract product copy. Return ONLY a JSON array of strings. No markdown.`,
      `Fetch and extract all copy from: ${p.url ?? ""}. Include: headline, sub-headline, bullets, callouts, CTAs, badges, promo text. JSON array only.`,
      true
    );
    pages.push({ name: p.name ?? "Retailer", url: p.url ?? "", copy: parseArr(copyRaw) });
  }
  return pages;
}

async function collectImages(brand: string): Promise<ImageItem[]> {
  const r = await callClaude(
    `Visual research agent. Find ad image URLs. Return ONLY JSON array: [{"url":"...","label":"...","channel":"..."}]. Direct image URLs only. Max 12. No markdown.`,
    `Find actual ad image URLs for "${brand}" from Meta Ad Library, Instagram/social posts, official website, and Google Images for "${brand} advertisement". Format: [{"url":"https://...","label":"description","channel":"Meta Ads|Social|Brand Site|Digital"}]`,
    true
  );
  return parseArr(r) as unknown as ImageItem[];
}

async function synthesize(brand: string, allCopy: string[]): Promise<VoiceData> {
  const r = await callClaude(
    `Senior creative strategist. Analyze copy, return brand voice JSON. Pure JSON object, no markdown.`,
    `Brand: ${brand}\n\nCopy samples:\n${allCopy.slice(0, 40).map((c, i) => `${i + 1}. "${c}"`).join("\n")}\n\nReturn ONLY:\n{"toneWords":["4-5 adjectives"],"themes":["4-5 themes"],"patterns":["2-3 patterns"],"avoid":["2-3 avoids"],"summary":"2-3 sentence voice summary"}`
  );
  return parseObj(r) as VoiceData;
}

async function genCopy(brand: string, voice: VoiceData, allCopy: string[]): Promise<CopyData> {
  const r = await callClaude(
    `Expert PDP copywriter. Write in established brand voice. Pure JSON, no markdown.`,
    `Brand: ${brand}\nVoice: ${voice.summary ?? ""}\nTone: ${(voice.toneWords ?? []).join(", ")}\nThemes: ${(voice.themes ?? []).join(", ")}\n\nSample brand copy:\n${allCopy.slice(0, 20).map(c => `"${c}"`).join("\n")}\n\nReturn ONLY:\n{"headlines":["12 headlines 8 words or fewer"],"ultraShort":["5 hooks 3 words or fewer"]}`
  );
  return parseObj(r) as CopyData;
}

function Progress({ stage, done }: { stage: string | null; done: boolean }) {
  const idx = STAGES.findIndex(s => s.id === stage);
  return (
    <div className="my-4">
      {STAGES.map((s, i) => {
        const active = s.id === stage && !done;
        const complete = done || i < idx;
        return (
          <div key={s.id} className="flex items-center gap-3 py-1" style={{ opacity: i > idx && !done ? 0.25 : 1 }}>
            <span className="text-sm w-5">{s.icon}</span>
            <div className="flex-1 h-1 rounded-full bg-gray-200 relative overflow-hidden">
              {complete && <div className="absolute inset-0 bg-blue-600" />}
              {active && <div className="absolute inset-0 bg-blue-300 animate-pulse" />}
            </div>
            <span className={`text-xs w-48 ${complete ? "text-blue-700 font-semibold" : active ? "text-blue-900 font-semibold" : "text-gray-400"}`}>
              {s.label}{active ? "…" : complete ? " ✓" : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function Home() {
  const [brand, setBrand] = useState("");
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [result, setResult] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  async function run() {
    if (!brand.trim()) return;
    setRunning(true); setDone(false); setResult(null); setError(null);
    const allCopy: string[] = [], channelCopy: Record<string, string[]> = {};
    try {
      setStage("meta");
      const mc = await searchChannel(brand, "Meta Ad Library (facebook.com/ads/library), Facebook and Instagram paid ads");
      channelCopy["Meta Ads"] = mc; allCopy.push(...mc);

      setStage("social");
      const sc = await searchChannel(brand, "Instagram organic posts, Twitter/X, TikTok captions, hashtag campaigns");
      channelCopy["Social"] = sc; allCopy.push(...sc);

      setStage("ecom");
      const ec = await searchChannel(brand, "Amazon listings, brand ecom pages, promotional banners, product headlines on retail sites");
      channelCopy["Ecom"] = ec; allCopy.push(...ec);

      setStage("digital");
      const dc = await searchChannel(brand, "Digital display ads, Google search ads, YouTube pre-roll copy, landing page heroes");
      channelCopy["Digital"] = dc; allCopy.push(...dc);

      setStage("pdp");
      const pdpPages = await scrapePDPs(brand);
      for (const p of pdpPages) allCopy.push(...(p.copy ?? []));

      setStage("images");
      const images = await collectImages(brand);

      const uniqueCopy = [...new Set(allCopy.filter(c => c && c.length > 2 && c.length < 200))];

      setStage("synthesize");
      const voice = await synthesize(brand, uniqueCopy);

      setStage("headlines");
      const copy = await genCopy(brand, voice, uniqueCopy);

      setStage("pdf");
      setResult({ brand, voice, copy, rawCopy: uniqueCopy, pdpPages, images, channelCopy });
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setRunning(false);
    }
  }

  async function downloadPdf() {
    if (!result) return;
    setDownloading(true);
    try {
      const res = await fetch("/api/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (!res.ok) {
        const d = await res.json() as { error?: string };
        throw new Error(d.error ?? "PDF generation failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${result.brand.replace(/[^a-z0-9]/gi, "-").toLowerCase()}-ad-intelligence.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF download failed.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8 font-sans text-gray-900 bg-white min-h-screen">
      <div className="mb-6">
        <p className="text-xs font-bold tracking-widest text-gray-400 uppercase mb-1">Agency Five Eighty · PDP Copy Intelligence</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#0F1E3C] mb-1">Brand Ad Intelligence Agent</h1>
        <p className="text-xs text-gray-500 leading-relaxed">
          Scrapes Meta Ad Library · social · ecom · digital · 5 PDP pages · collects visuals · generates on-brand copy · exports PDF
        </p>
      </div>

      <div className="flex gap-2 mb-6">
        <input
          value={brand}
          onChange={e => setBrand(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !running && run()}
          disabled={running}
          placeholder="Enter brand name  (e.g. Pendleton Whiskey)"
          className="flex-1 px-4 py-3 rounded-lg border-2 border-gray-200 bg-white text-gray-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
        />
        <button
          onClick={run}
          disabled={running || !brand.trim()}
          className="px-5 py-3 bg-[#2563EB] text-white rounded-lg font-bold text-sm disabled:opacity-40 hover:bg-blue-700 transition-colors"
        >
          {running ? "Running…" : "▶ Run Agent"}
        </button>
      </div>

      {(running || done) && <Progress stage={stage} done={done} />}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-xs mt-3">⚠️ {error}</div>
      )}

      {result && done && (
        <div className="mt-5 space-y-4">
          <div className="bg-blue-50 border-l-4 border-blue-600 rounded-lg p-4">
            <p className="text-xs font-bold text-blue-600 tracking-widest uppercase mb-2">Brand Voice</p>
            <p className="text-sm text-[#1e3a5f] leading-relaxed mb-3">{result.voice.summary}</p>
            <div className="flex flex-wrap gap-1">
              {result.voice.toneWords?.map(t => (
                <span key={t} className="bg-blue-200 text-blue-800 px-3 py-0.5 rounded-full text-xs font-bold">{t}</span>
              ))}
            </div>
          </div>

          <div className="bg-green-50 border-l-4 border-green-600 rounded-lg p-4">
            <p className="text-xs font-bold text-green-700 tracking-widest uppercase mb-2">PDP Pages Scraped ({result.pdpPages?.length ?? 0})</p>
            {result.pdpPages?.map((p, i) => (
              <div key={i} className="flex gap-2 items-baseline text-xs mb-1">
                <b className="text-green-800 min-w-[80px]">{p.name}</b>
                <span className="text-gray-500 flex-1 truncate">{p.url?.slice(0, 60)}</span>
                <span className="text-green-600 whitespace-nowrap">{p.copy?.length ?? 0} strings</span>
              </div>
            ))}
          </div>

          {result.images?.length > 0 && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-xs font-bold text-gray-500 tracking-widest uppercase mb-2">Visual Assets Found ({result.images.length})</p>
              <div className="flex flex-wrap gap-1">
                {result.images.slice(0, 8).map((img, i) => (
                  <span key={i} className="text-xs bg-gray-200 rounded px-2 py-0.5 text-gray-700">{img.channel} · {(img.label ?? "").slice(0, 28)}</span>
                ))}
                {result.images.length > 8 && <span className="text-xs text-gray-400">+{result.images.length - 8} more in PDF</span>}
              </div>
            </div>
          )}

          <div>
            <p className="text-xs font-bold text-gray-700 tracking-widest uppercase mb-2">Headlines <span className="text-gray-400 font-normal">· 8 words or fewer</span></p>
            <div className="grid grid-cols-2 gap-1.5">
              {result.copy.headlines?.map((h, i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs font-semibold flex gap-2 items-start">
                  <span className="text-gray-300 text-[9px] font-bold mt-0.5 min-w-[18px]">{String(i + 1).padStart(2, "0")}</span>{h}
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-bold text-gray-700 tracking-widest uppercase mb-2">Ultra-Short <span className="text-gray-400 font-normal">· 3 words or fewer</span></p>
            <div className="flex flex-wrap gap-2">
              {result.copy.ultraShort?.map((h, i) => (
                <div key={i} className="bg-[#0F1E3C] text-white rounded-lg px-4 py-2 text-sm font-extrabold">{h}</div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            {([["📋", result.rawCopy.length, "Copy Samples"], ["🔍", result.pdpPages?.length ?? 0, "PDP Pages"], ["🖼", result.images?.length ?? 0, "Visuals"], ["✍️", result.copy.headlines?.length ?? 0, "Headlines"]] as const).map(([icon, n, label]) => (
              <div key={label} className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                <div className="text-base">{icon}</div>
                <div className="text-xl font-extrabold text-[#0F1E3C]">{n}</div>
                <div className="text-[9px] text-gray-500 uppercase tracking-wide">{label}</div>
              </div>
            ))}
          </div>

          <div className="bg-[#0F1E3C] rounded-xl p-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-[#93c5fd] text-[10px] font-bold tracking-widest uppercase mb-0.5">Report Ready</p>
              <p className="text-white text-sm font-bold">{result.brand} · Ad Intelligence Report</p>
              <p className="text-[#475569] text-xs mt-0.5">5 sections · brand voice · PDP scrape · visuals · headlines</p>
            </div>
            <button
              onClick={downloadPdf}
              disabled={downloading}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-bold whitespace-nowrap disabled:opacity-50 transition-colors"
            >
              {downloading ? "Building…" : "⬇ Download PDF"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
