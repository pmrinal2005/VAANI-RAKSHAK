import {
  integer,
  jsonb,
  pgTable,
  serial,
  text,
  timestamp,
} from "drizzle-orm/pg-core";

export const detections = pgTable("detections", {
  id: serial("id").primaryKey(),
  verdict: text("verdict").notNull(),
  band: text("band").notNull(),
  riskScore: integer("risk_score").notNull(),
  language: text("language").notNull(),
  explanation: text("explanation").notNull(),
  featureHash: text("feature_hash").notNull(),
  latencyMs: integer("latency_ms").notNull(),
  requiresOutOfBand: integer("requires_out_of_band").notNull().default(0),
  payload: jsonb("payload").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const ledgerBlocks = pgTable("ledger_blocks", {
  id: serial("id").primaryKey(),
  blockIndex: integer("block_index").notNull(),
  ts: integer("ts").notNull(),
  type: text("type").notNull(),
  payloadHash: text("payload_hash").notNull(),
  summary: text("summary").notNull(),
  riskScore: integer("risk_score"),
  actor: text("actor").notNull(),
  prevHash: text("prev_hash").notNull(),
  hash: text("hash").notNull(),
  nonce: integer("nonce").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
