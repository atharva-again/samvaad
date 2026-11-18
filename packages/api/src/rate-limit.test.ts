import { describe, expect, it } from "vite-plus/test";
import { createFixedWindowRateLimiter } from "./rate-limit.js";

describe("fixed-window rate limiter", () => {
  it("allows the configured limit and rejects additional requests in the window", () => {
    const limit = createFixedWindowRateLimiter({
      limit: 2,
      windowMs: 60_000,
      maxBuckets: 10,
    });

    expect(limit("user-1", 0)).toBe(true);
    expect(limit("user-1", 1)).toBe(true);
    expect(limit("user-1", 2)).toBe(false);
  });

  it("starts a fresh window after expiration", () => {
    const limit = createFixedWindowRateLimiter({
      limit: 1,
      windowMs: 60_000,
      maxBuckets: 10,
    });

    expect(limit("user-1", 0)).toBe(true);
    expect(limit("user-1", 59_999)).toBe(false);
    expect(limit("user-1", 60_000)).toBe(true);
  });

  it("keeps separate identities in separate buckets", () => {
    const limit = createFixedWindowRateLimiter({
      limit: 1,
      windowMs: 60_000,
      maxBuckets: 10,
    });

    expect(limit("user-1", 0)).toBe(true);
    expect(limit("user-2", 0)).toBe(true);
  });

  it("bounds the bucket map and reclaims expired entries when at capacity", () => {
    const limit = createFixedWindowRateLimiter({
      limit: 1,
      windowMs: 60_000,
      maxBuckets: 1,
      cleanupEvery: 100,
    });

    expect(limit("user-1", 0)).toBe(true);
    expect(limit("user-2", 1)).toBe(false);
    expect(limit("user-2", 60_000)).toBe(true);
  });
});
