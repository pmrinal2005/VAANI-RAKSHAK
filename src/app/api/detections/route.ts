import { desc } from "drizzle-orm";
import { db } from "@/db";
import { detections } from "@/db/schema";

export const dynamic = "force-dynamic";

export async function GET() {
  const rows = await db.select().from(detections).orderBy(desc(detections.createdAt)).limit(20);
  return Response.json({ detections: rows });
}

export async function POST(request: Request) {
  const body = (await request.json()) as {
    verdict?: string;
    band?: string;
    riskScore?: number;
    language?: string;
    explanation?: string;
    featureHash?: string;
    latencyMs?: number;
    requiresOutOfBand?: boolean;
    payload?: unknown;
  };

  if (!body.verdict || !body.band || typeof body.riskScore !== "number") {
    return Response.json({ error: "Invalid detection payload" }, { status: 400 });
  }

  const [row] = await db
    .insert(detections)
    .values({
      verdict: body.verdict,
      band: body.band,
      riskScore: Math.round(body.riskScore),
      language: body.language ?? "undetermined",
      explanation: body.explanation ?? "",
      featureHash: body.featureHash ?? "",
      latencyMs: Math.round(body.latencyMs ?? 0),
      requiresOutOfBand: body.requiresOutOfBand ? 1 : 0,
      payload: (body.payload ?? {}) as Record<string, unknown>,
    })
    .returning();

  return Response.json({ detection: row }, { status: 201 });
}
