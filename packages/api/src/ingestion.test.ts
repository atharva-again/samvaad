import { describe, expect, it } from "vite-plus/test";
import { structuralChunk } from "./ingestion.js";

describe("structural document chunking", () => {
  it("returns no chunks for empty parser output", () => {
    expect(structuralChunk([])).toEqual([]);
  });

  it("preserves page metadata, heading hierarchy, and tables", () => {
    const chunks = structuralChunk([
      {
        page_number: 2,
        items: [
          { type: "heading", level: 1, value: "Main title", md: "# Main title" },
          { type: "text", value: "Intro", md: "Intro" },
          { type: "heading", level: 2, value: "Section", md: "## Section" },
          { type: "text", value: "Details", md: "Details" },
          { type: "table", md: "|A|B|\n|-|-|\n|1|2|" },
        ],
      },
    ]);

    expect(chunks.map((chunk) => chunk.content)).toContain("# Main title\n\nIntro");
    expect(chunks.map((chunk) => chunk.content)).toContain("## Section\n\nDetails");
    expect(chunks.at(-1)?.metadata).toEqual({
      page_number: 2,
      heading: "Section",
      breadcrumbs: ["Main title", "Section"],
      content_type: "table",
    });
  });

  it("splits long blocks without losing the text or exceeding the limit", () => {
    const text = "Every sentence should be retained. ".repeat(150);
    const chunks = structuralChunk([{ page: 1, items: [{ type: "text", md: text }] }], {
      limit: 300,
      overlap: 30,
    });
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((chunk) => chunk.content.length <= 300)).toBe(true);
    expect(chunks.map((chunk) => chunk.content).join(" ")).toContain(
      "Every sentence should be retained.",
    );
  });
});
