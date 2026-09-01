import { drizzle, type NodePgDatabase } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import * as schema from "./schema";

type Db = NodePgDatabase<typeof schema>;

const globalForDb = globalThis as typeof globalThis & {
  __arenaNextJsPostgresqlPool?: Pool;
  __arenaNextJsPostgresqlDb?: Db;
};

/**
 * VAANI-RAKSHAK runs fully on-device: the detection cascade, ONNX inference and
 * the append-only ledger all work with browser (client) storage and never
 * require a server database. A Postgres backend is OPTIONAL — provisioned only
 * when DATABASE_URL is set (e.g. a managed Postgres on Vercel).
 *
 * Design goals:
 *   1. Never throw at module-import time — Next.js imports route modules while
 *      "collecting page data" during `next build`, so a missing DATABASE_URL
 *      must not fail the build.
 *   2. Never throw at request time when DATABASE_URL is absent — API routes
 *      detect `db === null` and fall back to client-storage semantics
 *      (empty result sets), so the deployed site works with zero backend config.
 */
const hasDatabase = Boolean(process.env.DATABASE_URL);

function getPool(): Pool {
  if (globalForDb.__arenaNextJsPostgresqlPool) {
    return globalForDb.__arenaNextJsPostgresqlPool;
  }

  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required");
  }

  const pool = new Pool({ connectionString: databaseUrl });
  globalForDb.__arenaNextJsPostgresqlPool = pool;
  return pool;
}

function getDb(): Db {
  if (globalForDb.__arenaNextJsPostgresqlDb) {
    return globalForDb.__arenaNextJsPostgresqlDb;
  }
  const db = drizzle(getPool(), { schema });
  globalForDb.__arenaNextJsPostgresqlDb = db;
  return db;
}

/**
 * Lazy proxy — resolves the real drizzle instance on first property access.
 * When DATABASE_URL is not configured this is `null`, and callers MUST guard
 * with `if (!db)` to keep the app working in the database-less (edge/on-device)
 * default mode.
 */
export const db: Db | null = hasDatabase
  ? new Proxy({} as Db, {
      get(_target, prop, receiver) {
        const real = getDb() as unknown as Record<string | symbol, unknown>;
        const value = Reflect.get(real, prop, receiver);
        return typeof value === "function"
          ? (value as (...a: unknown[]) => unknown).bind(real)
          : value;
      },
    })
  : null;

/** Lazy proxy for the underlying pg Pool (kept for API compatibility). */
export const pool: Pool | null = hasDatabase
  ? new Proxy({} as Pool, {
      get(_target, prop, receiver) {
        const real = getPool() as unknown as Record<string | symbol, unknown>;
        const value = Reflect.get(real, prop, receiver);
        return typeof value === "function"
          ? (value as (...a: unknown[]) => unknown).bind(real)
          : value;
      },
    })
  : null;
