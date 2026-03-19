import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

export async function POST(req: NextRequest) {
  const { system, user, search } = await req.json() as {
    system: string;
    user: string;
    search?: boolean;
  };

  // Build params — include web search tool when requested
  const params = {
    model: "claude-opus-4-6" as const,
    max_tokens: 1500,
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
