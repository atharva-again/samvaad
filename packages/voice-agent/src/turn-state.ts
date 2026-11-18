export interface RetrievalState {
  retrievalAttempted: boolean;
}

/**
 * Associates LiveKit speech generations with the finalized user turn that created them.
 * A turn may be interrupted without producing a ConversationItemAdded event, so responses
 * cannot safely be paired by shifting a FIFO queue.
 */
export class VoiceTurnRegistry<T extends RetrievalState> {
  private currentTurn: T | undefined;
  private readonly userTurns = new Map<string, T>();
  private readonly speechTurns = new Map<
    string,
    { turn: T; containsChatItem: (itemId: string) => boolean }
  >();

  get current(): T | undefined {
    return this.currentTurn;
  }

  setCurrent(turn: T, userMessageId: string): void {
    this.currentTurn = turn;
    this.userTurns.set(userMessageId, turn);
  }

  getForUserMessage(userMessageId: string): T | undefined {
    return this.userTurns.get(userMessageId);
  }

  bindSpeech(
    speechId: string,
    turn: T = this.currentTurn as T,
    containsChatItem: (itemId: string) => boolean = () => false,
  ): void {
    if (!turn) throw new Error("Cannot bind a LiveKit speech without a current turn");
    this.speechTurns.set(speechId, { turn, containsChatItem });
  }

  getForSpeech(speechId: string): T | undefined {
    return this.speechTurns.get(speechId)?.turn;
  }

  getForAssistantItem(itemId: string): T | undefined {
    for (const binding of this.speechTurns.values()) {
      if (binding.containsChatItem(itemId)) return binding.turn;
    }
    return undefined;
  }

  clearSpeech(speechId: string): void {
    const turn = this.speechTurns.get(speechId)?.turn;
    this.speechTurns.delete(speechId);
    if (!turn) return;
    for (const [userMessageId, candidate] of this.userTurns) {
      if (candidate === turn) this.userTurns.delete(userMessageId);
    }
    if (this.currentTurn === turn) this.currentTurn = undefined;
  }
}

export function shouldRequireContextRetrieval(
  strictMode: boolean,
  turn: RetrievalState | undefined,
  toolChoice: unknown,
): boolean {
  if (!strictMode || !turn || turn.retrievalAttempted || toolChoice === "none") return false;
  turn.retrievalAttempted = true;
  return true;
}
