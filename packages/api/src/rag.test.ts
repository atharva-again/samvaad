import { describe, expect, it } from "vite-plus/test";
import { formatRagContext } from "./utils.js";
import { scrubPii } from "./rag.js";

describe("RAG input safeguards", () => {
  it("redacts email, phone, SSN, and card-like strings before document embedding", () => {
    const scrubbed = scrubPii(
      "Email user@example.com, phone 123-456-7890, SSN 000-00-0000, card 1234 5678 9012 3456",
    );
    expect(scrubbed).toContain("[EMAIL_REDACTED]");
    expect(scrubbed).toContain("[PHONE_REDACTED]");
    expect(scrubbed).toContain("[SSN_REDACTED]");
    expect(scrubbed).toContain("[CARD_REDACTED]");
  });

  it("uses a stable no-results message", () => {
    expect(formatRagContext([])).toBe("No relevant information found in the knowledge base.");
  });
});
