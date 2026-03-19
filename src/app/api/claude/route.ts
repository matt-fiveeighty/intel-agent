import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// Model tiers — callers pick the right tier for the job
// haiku:  cheap, fast — structured JSON extraction / scraping
// sonnet: mid-tier   — synthesis, copy generation
const MODELS = {
  haiku:  "claude-haiku-4-5",
  sonnet: "claude-sonnet-4-5",
} as const;

type Tier = keyof typeof MODELS;

export async function POST(req: NextRequest) {
  const { system, user, search, tier, maxTokens } = await req.json() as {
    system: string;
    user: string;
    search?: boolean;
    tier?: Tier;
    maxTokens?: number;
  };

  const model = MODELS[tier ?? "haiku"];
  const max_tokens = maxTokens ?? 600;

  const params = {
    model,
    max_tokens,
    system,
    messages: [{ role: "user" as const, content: user }],
    ...(search
      ? { tools: [{ type: "web_search_20260209" as const, name: "web_search" as const }] }
      : {}),
  };

  const response = await client.messages.create(params);
  const text = response.content
    .filter((b) => b.type === "text")
    .map((b) => (b as Anthropic.TextBlock).text)
    .join("\n");

  return NextResponse.json({ text });
}
