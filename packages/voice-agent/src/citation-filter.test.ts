import { describe, expect, it } from "vite-plus/test";
import { filterCitationMarkers } from "./citation-filter.js";

async function* chunks(values: string[]): AsyncIterable<string> {
  yield* values;
}

async function collect(values: string[]): Promise<string> {
  const result: string[] = [];
  for await (const chunk of filterCitationMarkers(chunks(values))) {
    result.push(chunk);
  }
  return result.join("");
}

describe("citation speech filtering", () => {
  it("removes citations split across streaming chunk boundaries", async () => {
    expect(await collect(["Learning about ", "[", "1", "]", " now."])).toBe("Learning about now.");
  });

  it("removes citation markers before punctuation without altering raw input", async () => {
    const raw = "Answer [1], with evidence [2].";
    expect(await collect([raw])).toBe("Answer, with evidence.");
    expect(raw).toBe("Answer [1], with evidence [2].");
  });

  it("does not speak an incomplete citation marker at end of stream", async () => {
    expect(await collect(["See ", "[", "2"])).toBe("See");
  });
});
