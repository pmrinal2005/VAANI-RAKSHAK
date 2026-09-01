import { asc } from "drizzle-orm";
import { db } from "@/db";
import { ledgerBlocks } from "@/db/schema";

export const dynamic = "force-dynamic";

export async function GET() {
  // On-device / client-storage mode: the tamper-evident ledger lives in the browser.
  if (!db) return Response.json({ blocks: [] });
  const rows = await db.select().from(ledgerBlocks).orderBy(asc(ledgerBlocks.blockIndex));
  return Response.json({ blocks: rows });
}

export async function POST(request: Request) {
  const body = (await request.json()) as {
    index?: number;
    timestamp?: number;
    type?: string;
    payloadHash?: string;
    summary?: string;
    riskScore?: number;
    actor?: string;
    prevHash?: string;
    hash?: string;
    nonce?: number;
  };

  if (
    typeof body.index !== "number" ||
    !body.type ||
    !body.hash ||
    !body.prevHash ||
    !body.payloadHash
  ) {
    return Response.json({ error: "Invalid ledger block" }, { status: 400 });
  }

  // On-device / client-storage mode: acknowledge without persisting server-side.
  if (!db) return Response.json({ block: null, persisted: false }, { status: 202 });

  const [row] = await db
    .insert(ledgerBlocks)
    .values({
      blockIndex: body.index,
      ts: body.timestamp ?? Date.now(),
      type: body.type,
      payloadHash: body.payloadHash,
      summary: body.summary ?? "",
      riskScore: typeof body.riskScore === "number" ? Math.round(body.riskScore) : null,
      actor: body.actor ?? "detection-node",
      prevHash: body.prevHash,
      hash: body.hash,
      nonce: body.nonce ?? 0,
    })
    .returning();

  return Response.json({ block: row }, { status: 201 });
}
