import pg, { type PoolClient, type QueryResult, type QueryResultRow } from "pg";
import { drizzle } from "drizzle-orm/node-postgres";
import * as schema from "./schema.js";

const { Pool } = pg;

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: Number(process.env.DB_POOL_MAX ?? 10),
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 30_000,
});

pool.on("error", (error: Error) => {
  console.error("[db] Unexpected idle client error", error);
});

export const db = drizzle(pool, { schema });

export function assertDatabaseUrl(): void {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is required");
  }
}

export function getPool() {
  assertDatabaseUrl();
  return pool;
}

export function query<T extends QueryResultRow = QueryResultRow>(
  text: string,
  values: unknown[] = [],
): Promise<QueryResult<T>> {
  assertDatabaseUrl();
  return pool.query<T>(text, values);
}

export async function withTransaction<T>(work: (client: PoolClient) => Promise<T>): Promise<T> {
  assertDatabaseUrl();
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await work(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function closePool(): Promise<void> {
  await pool.end();
}
