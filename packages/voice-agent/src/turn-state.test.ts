import { describe, expect, it } from "vite-plus/test";
import { shouldRequireContextRetrieval, VoiceTurnRegistry } from "./turn-state.js";

describe("voice turn state", () => {
  it("keeps an interrupted speech associated with its original turn", () => {
    const turns = new VoiceTurnRegistry<{ retrievalAttempted: boolean; id: string }>();
    const interrupted = { id: "first", retrievalAttempted: false };
    const next = { id: "second", retrievalAttempted: false };

    turns.setCurrent(interrupted, "user-first");
    turns.bindSpeech("speech-first", interrupted, (itemId) => itemId === "item-first");
    turns.setCurrent(next, "user-second");
    turns.bindSpeech("speech-second", next, (itemId) => itemId === "item-second");

    expect(turns.getForUserMessage("user-first")).toBe(interrupted);
    expect(turns.getForUserMessage("user-second")).toBe(next);
    expect(turns.getForSpeech("speech-first")).toBe(interrupted);
    expect(turns.getForSpeech("speech-second")).toBe(next);
    expect(turns.getForAssistantItem("item-first")).toBe(interrupted);
    expect(turns.getForAssistantItem("item-second")).toBe(next);

    turns.clearSpeech("speech-first");
    expect(turns.getForSpeech("speech-first")).toBeUndefined();
    expect(turns.getForUserMessage("user-first")).toBeUndefined();
    expect(turns.current).toBe(next);
  });

  it("forces strict retrieval only once and respects the SDK stop-tool choice", () => {
    const turn = { retrievalAttempted: false };

    expect(shouldRequireContextRetrieval(true, turn, undefined)).toBe(true);
    expect(shouldRequireContextRetrieval(true, turn, undefined)).toBe(false);

    const nextTurn = { retrievalAttempted: false };
    expect(shouldRequireContextRetrieval(true, nextTurn, "none")).toBe(false);
    expect(nextTurn.retrievalAttempted).toBe(false);
  });
});
