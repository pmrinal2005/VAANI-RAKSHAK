import { db } from "@/db";
import { sql } from "drizzle-orm";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    if (!db) {
      // No DATABASE_URL configured — app runs in on-device / client-storage mode.
      return Response.json({ ok: true, db: "client-storage" });
    }
    await db.execute(sql`select 1`);
    return Response.json({ ok: true, db: "connected" });
  } catch {
    return Response.json({ ok: false }, { status: 500 });
  }
}
