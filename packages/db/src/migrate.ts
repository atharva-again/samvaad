import "dotenv/config";
import { fileURLToPath } from "node:url";
import { migrate as runMigrations } from "drizzle-orm/node-postgres/migrator";
import { assertDatabaseUrl, closePool, db } from "./client.js";

async function migrate(): Promise<void> {
  assertDatabaseUrl();
  const migrationsFolder = fileURLToPath(new URL("../drizzle/", import.meta.url));
  await runMigrations(db, { migrationsFolder });
  console.info("[db] Drizzle migrations applied");
}

migrate()
  .catch((error: unknown) => {
    console.error("[db] Migration failed", error);
    process.exitCode = 1;
  })
  .finally(closePool);
