interface RateLimitBucket {
  count: number;
  resetAt: number;
}

interface FixedWindowRateLimiterOptions {
  limit: number;
  windowMs: number;
  maxBuckets: number;
  cleanupEvery?: number;
}

export function createFixedWindowRateLimiter({
  limit,
  windowMs,
  maxBuckets,
  cleanupEvery = 64,
}: FixedWindowRateLimiterOptions): (key: string, now?: number) => boolean {
  if (
    !Number.isInteger(limit) ||
    limit < 1 ||
    !Number.isFinite(windowMs) ||
    windowMs < 1 ||
    !Number.isInteger(maxBuckets) ||
    maxBuckets < 1 ||
    !Number.isInteger(cleanupEvery) ||
    cleanupEvery < 1
  ) {
    throw new Error("Invalid fixed-window rate limiter options");
  }

  const buckets = new Map<string, RateLimitBucket>();
  let requestCount = 0;

  function removeExpiredBuckets(now: number): void {
    for (const [key, bucket] of buckets) {
      if (bucket.resetAt <= now) buckets.delete(key);
    }
  }

  return (key, now = Date.now()) => {
    requestCount += 1;
    if (requestCount % cleanupEvery === 0) removeExpiredBuckets(now);

    let bucket = buckets.get(key);
    if (bucket && bucket.resetAt <= now) {
      buckets.delete(key);
      bucket = undefined;
    }

    if (!bucket) {
      if (buckets.size >= maxBuckets) removeExpiredBuckets(now);
      // Fail closed for new identities when the hard memory bound is reached.
      if (buckets.size >= maxBuckets) return false;
      buckets.set(key, { count: 1, resetAt: now + windowMs });
      return true;
    }

    if (bucket.count >= limit) return false;
    bucket.count += 1;
    return true;
  };
}
