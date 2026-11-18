import { describe, expect, it } from "vite-plus/test";
import { buildSlidingWindow, buildSystemPrompt, getModeInstruction } from "./prompts.js";
import { detectQueryComplexity } from "./memory.js";

describe("prompt and history behavior", () => {
  it("falls back to the default persona and retains tool citation rules", () => {
    const prompt = buildSystemPrompt({
      persona: "not-a-persona",
      strictMode: true,
      history: "User: hello",
    });
    expect(prompt).toContain("helpful AI assistant");
    expect(prompt).toContain("Always use `fetch_context`");
    expect(prompt).toContain("NEVER** use filenames");
    expect(prompt).toContain("User: hello");
  });

  it("keeps voice answers concise and conversational", () => {
    const prompt = buildSystemPrompt({ mode: "voice", persona: "tutor" });
    expect(prompt).toContain("Keep responses brief");
    expect(prompt).toContain("patient and knowledgeable tutor");
    expect(prompt).not.toContain("### Conversation History");
  });

  it("splits recent history from older messages", () => {
    const messages = Array.from({ length: 8 }, (_, index) => index);
    expect(buildSlidingWindow(messages, 6)).toEqual([
      [2, 3, 4, 5, 6, 7],
      [0, 1],
    ]);
  });

  it("flags history references and synthesis questions", () => {
    expect(detectQueryComplexity("Compare what we discussed earlier").recommendation).toBe(
      "likely_needs_tools",
    );
    expect(detectQueryComplexity("What is a vector?").recommendation).toBe("baseline");
    expect(getModeInstruction(false)).toContain("Hybrid Mode");
  });
});
