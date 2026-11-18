import "dotenv/config";
import {
  AgentSession,
  AgentSessionEventTypes,
  ServerOptions,
  cli,
  defineAgent,
  llm,
  type JobContext,
  voice,
} from "@livekit/agents";
import * as deepgram from "@livekit/agents-plugin-deepgram";
import * as openai from "@livekit/agents-plugin-openai";
import * as silero from "@livekit/agents-plugin-silero";
import {
  LIVEKIT_VOICE_TOPIC,
  type LiveKitVoiceEvent,
  type VoiceCitation,
} from "@samvaad/voice-protocol";
import { filterCitationMarkers } from "./citation-filter.js";
import { shouldRequireContextRetrieval, VoiceTurnRegistry } from "./turn-state.js";
import { uuidv7 } from "uuidv7";
import { fileURLToPath } from "node:url";
import { z } from "zod";

interface DispatchMetadata {
  user_id: string;
  conversation_id: string;
  persona: string;
  strict_mode: boolean;
  enable_tts: boolean;
}

interface VoiceTurn {
  id: string;
  userMessageId: string;
  assistantMessageId: string;
  userMessage: string;
  sources: VoiceCitation[];
  assistantMessageReady: boolean;
  userPersisted: boolean;
  userPersistence?: Promise<void>;
  retrievalAttempted: boolean;
  retrievalPromise?: Promise<InternalRagResponse>;
}

interface InternalRagResponse {
  context: string;
  sources: VoiceCitation[];
}

const apiBaseUrl = process.env.SAMVAAD_API_URL?.replace(/\/+$/, "");
const voiceAgentSecret = process.env.VOICE_AGENT_SHARED_SECRET;

function readDispatchMetadata(raw: string): DispatchMetadata {
  const value = JSON.parse(raw) as Partial<DispatchMetadata>;
  if (
    typeof value.user_id !== "string" ||
    typeof value.conversation_id !== "string" ||
    typeof value.persona !== "string" ||
    typeof value.strict_mode !== "boolean" ||
    typeof value.enable_tts !== "boolean"
  ) {
    throw new Error("Invalid LiveKit dispatch metadata");
  }
  return value as DispatchMetadata;
}

function assertBridgeConfigured(): void {
  if (!apiBaseUrl || !voiceAgentSecret) {
    throw new Error("SAMVAAD_API_URL and VOICE_AGENT_SHARED_SECRET are required");
  }
}

async function bridgePost<TResponse>(path: string, body: unknown): Promise<TResponse> {
  assertBridgeConfigured();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${voiceAgentSecret}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15_000),
  });

  if (!response.ok) {
    throw new Error(`Samvaad voice bridge ${path} failed (${response.status})`);
  }
  return (await response.json()) as TResponse;
}

async function persistVoiceRequest<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await bridgePost<TResponse>(path, body);
    } catch (error) {
      lastError = error;
      if (attempt < 2) {
        await new Promise((resolve) => setTimeout(resolve, 250 * 2 ** attempt));
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Voice turn persistence failed");
}

async function persistUserMessage(metadata: DispatchMetadata, turn: VoiceTurn): Promise<void> {
  await persistVoiceRequest("/internal/voice/user-message", {
    user_id: metadata.user_id,
    conversation_id: metadata.conversation_id,
    user_message_id: turn.userMessageId,
    user_message: turn.userMessage,
  });
  turn.userPersisted = true;
}

async function sendVoiceEvent(room: JobContext["room"], event: LiveKitVoiceEvent): Promise<void> {
  const bytes = new TextEncoder().encode(JSON.stringify(event));
  const localParticipant = room.localParticipant;
  if (!localParticipant) throw new Error("LiveKit room has no local participant");
  await localParticipant.publishData(bytes, {
    reliable: true,
    topic: LIVEKIT_VOICE_TOPIC,
  });
}

async function handleUserTurn(
  ctx: JobContext,
  metadata: DispatchMetadata,
  newMessage: { id: string; textContent?: string },
  turns: VoiceTurnRegistry<VoiceTurn>,
): Promise<void> {
  const userMessage = newMessage.textContent?.trim() ?? "";
  if (!userMessage) return;
  const turn: VoiceTurn = {
    id: uuidv7(),
    userMessageId: uuidv7(),
    assistantMessageId: uuidv7(),
    userMessage,
    sources: [],
    assistantMessageReady: false,
    userPersisted: false,
    retrievalAttempted: false,
  };
  turns.setCurrent(turn, newMessage.id);
  turn.userPersistence = persistUserMessage(metadata, turn).catch((error) => {
    console.error("Failed to persist LiveKit voice user message", error);
  });
  try {
    await sendVoiceEvent(ctx.room, {
      type: "user_message",
      turn_id: turn.id,
      message_id: turn.userMessageId,
      text: turn.userMessage,
    });
  } catch (error) {
    console.error("Failed to publish LiveKit voice user message", error);
  }
}

export default defineAgent({
  entry: async (ctx) => {
    const metadata = readDispatchMetadata(ctx.job.metadata);
    const context = await bridgePost<{
      system_instruction: string;
      messages: Array<{ role: "user" | "assistant"; content: string }>;
    }>("/internal/voice/context", {
      user_id: metadata.user_id,
      conversation_id: metadata.conversation_id,
      persona: metadata.persona,
      strict_mode: metadata.strict_mode,
    });

    const chatCtx = new llm.ChatContext();
    for (const message of context.messages) {
      chatCtx.addMessage({ role: message.role, content: message.content });
    }

    const turns = new VoiceTurnRegistry<VoiceTurn>();

    function getTurnForChatContext(chatContext: llm.ChatContext): VoiceTurn | undefined {
      for (let index = chatContext.items.length - 1; index >= 0; index -= 1) {
        const item = chatContext.items[index];
        if (item?.type === "message" && item.role === "user") {
          return turns.getForUserMessage(item.id);
        }
      }
      return undefined;
    }

    const fetchContext = llm.tool({
      name: "fetch_context",
      description:
        "Search the user's knowledge base. Call once when a question asks about uploaded documents or needs their specific information.",
      parameters: z.object({
        query: z.string().min(1).max(500),
      }),
      execute: async ({ query }, { ctx: runContext }) => {
        const turn = turns.getForSpeech(runContext.speechHandle.id);
        const retrieve = async (): Promise<InternalRagResponse> => {
          const result = await bridgePost<InternalRagResponse>("/internal/voice/rag", {
            user_id: metadata.user_id,
            query,
          });
          if (turn) {
            turn.sources = result.sources;
            if (result.sources.length > 0) {
              await sendVoiceEvent(ctx.room, {
                type: "citations",
                turn_id: turn.id,
                sources: result.sources,
              });
            }
          }
          return result;
        };

        if (turn) turn.retrievalAttempted = true;
        if (metadata.strict_mode && turn) {
          // Strict mode requires one retrieval, not a forced search at every LLM step.
          turn.retrievalPromise ??= retrieve();
          return (await turn.retrievalPromise).context;
        }
        return (await retrieve()).context;
      },
    });

    const agent = voice.Agent.create({
      instructions: context.system_instruction,
      chatCtx,
      tools: [fetchContext],
      onUserTurnCompleted: async (_agentContext, _chatContext, newMessage) => {
        await handleUserTurn(ctx, metadata, newMessage, turns);
      },
      async llmNode(agentContext, chatContext, toolContext, modelSettings) {
        // Preemptive generation is disabled below, so this node is entered only after
        // onUserTurnCompleted has installed the finalized turn.
        const turn = getTurnForChatContext(chatContext);
        const requireContext = shouldRequireContextRetrieval(
          metadata.strict_mode,
          turn,
          modelSettings.toolChoice,
        );
        const stream = await voice.Agent.default.llmNode(
          agentContext.agent,
          chatContext,
          toolContext,
          {
            ...modelSettings,
            toolChoice: requireContext
              ? { type: "function", function: { name: "fetch_context" } }
              : modelSettings.toolChoice,
          },
        );
        if (!stream) return null;

        // Publish the completed assistant text as soon as generation finishes, while the
        // already-streaming TTS audio can still be playing. Tool-call generations are not
        // user-facing answers, so only emit text from a generation with no tool calls.
        const reader = stream.getReader();
        let answer = "";
        let hasToolCalls = false;
        let canceled = false;
        return new ReadableStream({
          async pull(controller) {
            try {
              const { done, value } = await reader.read();
              if (done) {
                if (
                  turn &&
                  !canceled &&
                  !turn.assistantMessageReady &&
                  !hasToolCalls &&
                  answer.trim()
                ) {
                  turn.assistantMessageReady = true;
                  try {
                    await sendVoiceEvent(ctx.room, {
                      type: "assistant_message_ready",
                      turn_id: turn.id,
                      message_id: turn.assistantMessageId,
                      text: answer.trim(),
                    });
                  } catch (error) {
                    console.error("Failed to publish ready LiveKit voice response", error);
                  }
                }
                reader.releaseLock();
                controller.close();
                return;
              }

              if (typeof value === "string") {
                answer += value;
              } else if (value && typeof value === "object" && "delta" in value) {
                const chunk = value as { delta?: { content?: string; toolCalls?: unknown[] } };
                if (chunk.delta?.toolCalls?.length) hasToolCalls = true;
                if (typeof chunk.delta?.content === "string") answer += chunk.delta.content;
              }
              controller.enqueue(value);
            } catch (error) {
              reader.releaseLock();
              controller.error(error);
            }
          },
          async cancel(reason) {
            canceled = true;
            try {
              await reader.cancel(reason);
            } finally {
              reader.releaseLock();
            }
          },
        });
      },
      ttsNode(ctx, text, modelSettings) {
        return voice.Agent.default.ttsNode(ctx.agent, filterCitationMarkers(text), modelSettings);
      },
    });

    const session = new AgentSession({
      stt: new deepgram.STT({
        apiKey: process.env.DEEPGRAM_API_KEY,
        model: process.env.DEEPGRAM_STT_MODEL ?? "nova-3-general",
        language: "en",
        baseUrl: process.env.DEEPGRAM_STT_BASE_URL ?? "wss://api.deepgram.com",
      }),
      llm: openai.LLM.withGroq({
        apiKey: process.env.GROQ_API_KEY,
        model: process.env.GROQ_CHAT_MODEL ?? "openai/gpt-oss-120b",
      }),
      tts: metadata.enable_tts
        ? new deepgram.TTS({
            apiKey: process.env.DEEPGRAM_API_KEY,
            model: "aura-2-asteria-en",
            baseUrl: process.env.DEEPGRAM_TTS_BASE_URL ?? "https://api.deepgram.com",
            encoding: "linear16",
          })
        : undefined,
      vad: await silero.VAD.load({
        // The stricter 0.8 threshold dropped normal speech from quieter mics,
        // leaving the session listening without recognizing a user turn.
        activationThreshold: 0.5,
        minSpeechDuration: 50,
        minSilenceDuration: 550,
      }),
      turnHandling: {
        // Turn state is attached to the finalized user turn below. Speculative generations can
        // start before onUserTurnCompleted and lose the question/citation association.
        preemptiveGeneration: { enabled: false },
        interruption: {
          enabled: true,
          mode: "vad",
          minDuration: 500,
        },
        endpointing: {
          mode: "fixed",
          minDelay: 500,
          maxDelay: 1_000,
        },
      },
      ttsTextTransforms: ["filter_markdown", "filter_emoji"],
    });

    session.on(AgentSessionEventTypes.AgentStateChanged, async (event) => {
      const state =
        event.newState === "thinking"
          ? "thinking"
          : event.newState === "speaking"
            ? "speaking"
            : event.newState === "listening"
              ? "listening"
              : "idle";
      await sendVoiceEvent(ctx.room, { type: "agent_state", state });
    });

    session.on(AgentSessionEventTypes.SpeechCreated, (event) => {
      if (event.source !== "generate_reply") return;
      const turn = turns.current;
      if (!turn) {
        console.error("LiveKit created a reply speech without an active Samvaad turn");
        return;
      }

      const speechHandle = event.speechHandle;
      turns.bindSpeech(speechHandle.id, turn, (itemId) =>
        speechHandle.chatItems.some((item) => item.id === itemId),
      );
      const clearSpeechTurn = () => turns.clearSpeech(speechHandle.id);
      void speechHandle.waitForPlayout().then(clearSpeechTurn, clearSpeechTurn);
    });

    session.on(AgentSessionEventTypes.ConversationItemAdded, async (event) => {
      const item = event.item;
      if (item.type !== "message" || item.role !== "assistant") return;
      const answer = item.textContent?.trim() ?? "";
      if (!answer) return;

      const turn = turns.getForAssistantItem(item.id);
      if (!turn) {
        console.error("Received a voice response without a matching LiveKit speech turn");
        return;
      }

      let persisted = false;
      let conversationTitle: string | undefined;
      try {
        await turn.userPersistence;
        if (!turn.userPersisted) {
          await persistUserMessage(metadata, turn);
        }
        const result = await persistVoiceRequest<{ conversation_title: string }>(
          "/internal/voice/assistant-message",
          {
            user_id: metadata.user_id,
            conversation_id: metadata.conversation_id,
            user_message_id: turn.userMessageId,
            assistant_message_id: turn.assistantMessageId,
            assistant_message: answer,
            sources: turn.sources,
          },
        );
        conversationTitle = result.conversation_title;
        persisted = true;
      } catch (error) {
        console.error("Failed to persist LiveKit voice turn", error);
      }

      await sendVoiceEvent(ctx.room, {
        type: "assistant_message",
        turn_id: turn.id,
        message_id: turn.assistantMessageId,
        text: answer,
        sources: turn.sources,
        interrupted: item.interrupted,
        persisted,
        conversation_title: conversationTitle,
      });
    });

    await session.start({
      agent,
      room: ctx.room,
      inputOptions: { deleteRoomOnClose: true },
      outputOptions: { audioEnabled: metadata.enable_tts },
    });
    await sendVoiceEvent(ctx.room, { type: "agent_ready" });

    ctx.addShutdownCallback(async () => {
      await session.close();
    });
  },
});

cli.runApp(
  new ServerOptions({
    agent: fileURLToPath(import.meta.url),
    agentName: process.env.LIVEKIT_AGENT_NAME ?? "samvaad-voice",
  }),
);
