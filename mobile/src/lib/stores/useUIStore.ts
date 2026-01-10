import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";

export interface SourceItem {

  id: number | string;
  name: string;
  type: string;
  size: string;
  uploadedAt: string;
  status: "uploading" | "synced" | "error";
  contentHash?: string;
}

export interface DuplicateItem {
  file: { name: string; uri: string };
  match: {
    name: string;
    id: string | number;
  };
}

export interface CitationItem {
  filename: string;
  content_preview: string;
  rerank_score?: number;
  chunk_id?: string;
  metadata?: {
    extra?: {
      page_number?: number;
      breadcrumbs?: string[];
      content_type?: string;
      heading?: string;
    };
  };
}

interface UIState {
  mode: "text" | "voice";
  isSidebarOpen: boolean;
  hasInteracted: boolean;
  strictMode: boolean;
  persona: string;
  enableTTS: boolean;
  isVoiceSessionActive: boolean;
  activeVoiceConversationId: string | null;
  setMode: (mode: "text" | "voice") => void;
  setHasInteracted: (hasInteracted: boolean) => void;
  setStrictMode: (strictMode: boolean) => void;
  setPersona: (persona: string) => void;
  setEnableTTS: (enableTTS: boolean) => void;
  setVoiceSessionActive: (
    active: boolean,
    conversationId?: string | null
  ) => void;
  toggleSidebar: () => void;

  isSearchOpen: boolean;
  toggleSearch: () => void;
  setSearchOpen: (isOpen: boolean) => void;

  isSourcesPanelOpen: boolean;
  toggleSourcesPanel: () => void;
  setSourcesPanelOpen: (isOpen: boolean) => void;
  sourcesSearchQuery: string;
  setSourcesSearchQuery: (query: string) => void;

  sourcesPanelTab: "knowledge-base" | "citations";
  setSourcesPanelTab: (tab: "knowledge-base" | "citations") => void;

  currentCitations: CitationItem[];
  citationsMessageId: string | null;
  hoveredCitationIndex: number | null;
  hoveredCitationMessageId: string | null;
  citedIndices: number[] | null;
  hoverSource: "bubble" | "panel" | null;
  setCitations: (
    messageId: string,
    citations: CitationItem[],
    citedIndices?: number[]
  ) => void;
  clearCitations: () => void;
  setHoveredCitationIndex: (
    index: number | null,
    messageId?: string | null,
    source?: "bubble" | "panel" | null
  ) => void;
  openCitations: (
    messageId: string,
    citations: CitationItem[],
    citedIndices?: number[]
  ) => void;

  sources: SourceItem[];
  setSources: (sources: SourceItem[]) => void;
  addSource: (source: SourceItem) => void;
  removeSource: (id: number | string) => void;
  removeSources: (ids: (number | string)[]) => void;
  updateSourceStatus: (
    id: number | string,
    status: "uploading" | "synced" | "error"
  ) => void;
  updateSource: (id: number | string, updates: Partial<SourceItem>) => void;

  isSelectionMode: boolean;
  selectedSourceIds: Set<string>;
  toggleSelectionMode: () => void;
  toggleSourceSelection: (id: string) => void;
  selectAllSources: () => void;
  clearSourceSelection: () => void;

  allowedSourceIds: Set<string> | null;
  setAllowedSourceIds: (ids: Set<string> | null) => void;
  toggleAllowedSource: (id: string) => void;
  enableSources: (ids: string[]) => void;
  disableSources: (ids: string[]) => void;
  allowAllSources: () => void;

  hasFetchedSources: boolean;
  setHasFetchedSources: (hasFetched: boolean) => void;

  pendingDuplicates: DuplicateItem[];
  showDuplicateModal: boolean;
  setPendingDuplicates: (files: DuplicateItem[]) => void;
  setShowDuplicateModal: (show: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      mode: "text",
      isSidebarOpen: false,
      hasInteracted: false,
      strictMode: false,
      persona: "default",
      enableTTS: true,
      isVoiceSessionActive: false,
      activeVoiceConversationId: null,
      setMode: (mode) => set({ mode }),
      setHasInteracted: (hasInteracted) => set({ hasInteracted }),
      setStrictMode: (strictMode) => set({ strictMode }),
      setPersona: (persona) => set({ persona }),
      setEnableTTS: (enableTTS) => set({ enableTTS }),
      setVoiceSessionActive: (active, conversationId) =>
        set({
          isVoiceSessionActive: active,
          activeVoiceConversationId: active ? (conversationId ?? null) : null,
        }),
      toggleSidebar: () =>
        set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

      isSearchOpen: false,
      toggleSearch: () =>
        set((state) => ({ isSearchOpen: !state.isSearchOpen })),
      setSearchOpen: (isOpen) => set({ isSearchOpen: isOpen }),

      isSourcesPanelOpen: false,
      toggleSourcesPanel: () =>
        set((state) => ({ isSourcesPanelOpen: !state.isSourcesPanelOpen })),
      setSourcesPanelOpen: (isOpen) => set({ isSourcesPanelOpen: isOpen }),
      sourcesSearchQuery: "",
      setSourcesSearchQuery: (query) => set({ sourcesSearchQuery: query }),

      sourcesPanelTab: "knowledge-base",
      setSourcesPanelTab: (tab) => set({ sourcesPanelTab: tab }),

      currentCitations: [],
      citationsMessageId: null,
      hoveredCitationIndex: null,
      hoveredCitationMessageId: null,
      hoverSource: null,
      citedIndices: null,
      setCitations: (messageId, citations, citedIndices) =>
        set({
          citationsMessageId: messageId,
          currentCitations: citations,
          citedIndices: citedIndices ?? null,
        }),
      setHoveredCitationIndex: (index, messageId, source) =>
        set({
          hoveredCitationIndex: index,
          hoveredCitationMessageId: messageId ?? null,
          hoverSource: source ?? null,
        }),
      openCitations: (messageId, citations, citedIndices) => {
        set({ isSourcesPanelOpen: true });
        set({ sourcesPanelTab: "citations" });
        set({
          citationsMessageId: messageId,
          currentCitations: citations,
          citedIndices: citedIndices ?? null,
        });
      },
      clearCitations: () =>
        set({
          currentCitations: [],
          citationsMessageId: null,
          hoveredCitationIndex: null,
          hoveredCitationMessageId: null,
          hoverSource: null,
          citedIndices: null,
        }),

      sources: [],
      setSources: (sources) => set({ sources }),
      addSource: (source) =>
        set((state) => ({ sources: [source, ...state.sources] })),
      removeSource: (id) =>
        set((state) => ({ sources: state.sources.filter((s) => s.id !== id) })),
      removeSources: (ids) =>
        set((state) => ({
          sources: state.sources.filter((s) => !ids.includes(s.id)),
          selectedSourceIds: new Set(),
        })),
      updateSourceStatus: (id, status) =>
        set((state) => ({
          sources: state.sources.map((s) =>
            s.id === id ? { ...s, status } : s
          ),
        })),
      updateSource: (id, updates) =>
        set((state) => ({
          sources: state.sources.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        })),

      isSelectionMode: false,
      selectedSourceIds: new Set(),
      toggleSelectionMode: () =>
        set((state) => ({
          isSelectionMode: !state.isSelectionMode,
          selectedSourceIds: new Set(),
        })),
      toggleSourceSelection: (id) =>
        set((state) => {
          const newSet = new Set(state.selectedSourceIds);
          if (newSet.has(id)) {
            newSet.delete(id);
          } else {
            newSet.add(id);
          }
          return { selectedSourceIds: newSet };
        }),
      selectAllSources: () =>
        set((state) => ({
          selectedSourceIds: new Set(state.sources.map((s) => String(s.id))),
        })),
      clearSourceSelection: () => set({ selectedSourceIds: new Set() }),

      allowedSourceIds: null,
      setAllowedSourceIds: (ids) => set({ allowedSourceIds: ids }),
      toggleAllowedSource: (id) =>
        set((state) => {
          const { sources, allowedSourceIds } = state;
          if (allowedSourceIds === null) {
            const newSet = new Set(sources.map((s) => String(s.id)));
            newSet.delete(id);
            return { allowedSourceIds: newSet };
          }
          const newSet = new Set(allowedSourceIds);
          if (newSet.has(id)) {
            newSet.delete(id);
          } else {
            newSet.add(id);
          }
          if (newSet.size === sources.length) {
            return { allowedSourceIds: null };
          }
          return { allowedSourceIds: newSet };
        }),
      enableSources: (ids) =>
        set((state) => {
          const { sources, allowedSourceIds } = state;
          if (allowedSourceIds === null) return {};

          const newSet = new Set(allowedSourceIds);
          for (const id of ids) newSet.add(id);

          if (newSet.size === sources.length) {
            return { allowedSourceIds: null };
          }
          return { allowedSourceIds: newSet };
        }),
      disableSources: (ids) =>
        set((state) => {
          const { sources, allowedSourceIds } = state;
          if (allowedSourceIds === null) {
            const newSet = new Set(sources.map((s) => String(s.id)));
            for (const id of ids) newSet.delete(id);
            return { allowedSourceIds: newSet };
          }
          const newSet = new Set(allowedSourceIds);
          for (const id of ids) newSet.delete(id);
          return { allowedSourceIds: newSet };
        }),
      allowAllSources: () => set({ allowedSourceIds: null }),

      hasFetchedSources: false,
      setHasFetchedSources: (hasFetched) =>
        set({ hasFetchedSources: hasFetched }),

      pendingDuplicates: [],
      showDuplicateModal: false,
      setPendingDuplicates: (files) => set({ pendingDuplicates: files }),
      setShowDuplicateModal: (show) => set({ showDuplicateModal: show }),
    }),
    {
      name: "samvaad-ui-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        strictMode: state.strictMode,
        persona: state.persona,
        enableTTS: state.enableTTS,
      }),
    }
  )
);
