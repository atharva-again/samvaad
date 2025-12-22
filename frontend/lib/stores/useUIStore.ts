import { create } from 'zustand'

export interface SourceItem {
  id: number | string
  name: string
  type: string
  size: string
  uploadedAt: string
  status: 'uploading' | 'synced' | 'error'
  contentHash?: string // For content-based deduplication
}

export interface DuplicateItem {
  file: File
  match: {
    name: string
    id: string | number
  }
}

// Citation item from RAG pipeline
export interface CitationItem {
  filename: string
  content_preview: string
  rerank_score?: number
  chunk_id?: string
}

interface UIState {
  mode: 'text' | 'voice'
  isSidebarOpen: boolean
  hasInteracted: boolean
  setMode: (mode: 'text' | 'voice') => void
  setHasInteracted: (hasInteracted: boolean) => void
  toggleSidebar: () => void

  // Universal Search Modal
  isSearchOpen: boolean
  toggleSearch: () => void
  setSearchOpen: (isOpen: boolean) => void

  // Sources Panel
  isSourcesPanelOpen: boolean
  toggleSourcesPanel: () => void
  setSourcesPanelOpen: (isOpen: boolean) => void
  sourcesSearchQuery: string
  setSourcesSearchQuery: (query: string) => void

  // Sources Panel Tab (Knowledge Base vs Citations)
  sourcesPanelTab: 'knowledge-base' | 'citations'
  setSourcesPanelTab: (tab: 'knowledge-base' | 'citations') => void

  // Citations State
  currentCitations: CitationItem[]
  citationsMessageId: string | null
  hoveredCitationIndex: number | null
  hoveredCitationMessageId: string | null
  citedIndices: number[] | null
  hoverSource: 'bubble' | 'panel' | null
  setCitations: (messageId: string, citations: CitationItem[], citedIndices?: number[]) => void
  clearCitations: () => void
  setHoveredCitationIndex: (index: number | null, messageId?: string | null, source?: 'bubble' | 'panel' | null) => void
  openCitations: (messageId: string, citations: CitationItem[], citedIndices?: number[]) => void

  // Sources Data
  sources: SourceItem[]
  setSources: (sources: SourceItem[]) => void
  addSource: (source: SourceItem) => void
  removeSource: (id: number | string) => void
  removeSources: (ids: (number | string)[]) => void
  updateSourceStatus: (id: number | string, status: 'uploading' | 'synced' | 'error') => void
  updateSource: (id: number | string, updates: Partial<SourceItem>) => void

  // Selection Mode (for batch delete)
  isSelectionMode: boolean
  selectedSourceIds: Set<string>
  toggleSelectionMode: () => void
  toggleSourceSelection: (id: string) => void
  selectAllSources: () => void
  clearSourceSelection: () => void

  // RAG Source Whitelist (null = all sources allowed)
  allowedSourceIds: Set<string> | null
  setAllowedSourceIds: (ids: Set<string> | null) => void
  toggleAllowedSource: (id: string) => void
  enableSources: (ids: string[]) => void
  disableSources: (ids: string[]) => void
  allowAllSources: () => void

  // Fetch State
  hasFetchedSources: boolean
  setHasFetchedSources: (hasFetched: boolean) => void

  // Duplicate Management
  pendingDuplicates: DuplicateItem[]
  showDuplicateModal: boolean
  setPendingDuplicates: (files: DuplicateItem[]) => void
  setShowDuplicateModal: (show: boolean) => void
}


export const useUIStore = create<UIState>((set, get) => ({
  mode: 'text',
  isSidebarOpen: false,
  hasInteracted: false,
  setMode: (mode) => set({ mode }),
  setHasInteracted: (hasInteracted) => set({ hasInteracted }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  // Universal Search Modal
  isSearchOpen: false,
  toggleSearch: () => set((state) => ({ isSearchOpen: !state.isSearchOpen })),
  setSearchOpen: (isOpen) => set({ isSearchOpen: isOpen }),

  // Sources Panel
  isSourcesPanelOpen: false,
  toggleSourcesPanel: () => set((state) => ({ isSourcesPanelOpen: !state.isSourcesPanelOpen })),
  setSourcesPanelOpen: (isOpen) => set({ isSourcesPanelOpen: isOpen }),
  sourcesSearchQuery: '',
  setSourcesSearchQuery: (query) => set({ sourcesSearchQuery: query }),

  // Sources Panel Tab
  sourcesPanelTab: 'knowledge-base',
  setSourcesPanelTab: (tab) => set({ sourcesPanelTab: tab }),

  // Citations State
  currentCitations: [],
  citationsMessageId: null,
  hoveredCitationIndex: null,
  hoveredCitationMessageId: null,
  hoverSource: null,
  citedIndices: null,
  setCitations: (messageId, citations, citedIndices) => set({ citationsMessageId: messageId, currentCitations: citations, citedIndices: citedIndices || null }),
  clearCitations: () => set({ citationsMessageId: null, currentCitations: [], hoveredCitationIndex: null, hoveredCitationMessageId: null, hoverSource: null, citedIndices: null }),
  setHoveredCitationIndex: (index, messageId, source = null) => set({ hoveredCitationIndex: index, hoveredCitationMessageId: messageId ?? null, hoverSource: source }),
  openCitations: (messageId, citations, citedIndices) => set({
    isSourcesPanelOpen: true,
    sourcesPanelTab: 'citations',
    citationsMessageId: messageId,
    currentCitations: citations,
    citedIndices: citedIndices || null,
    hoveredCitationIndex: null
  }),

  // Sources Data
  sources: [],
  setSources: (sources) => set({ sources }),
  addSource: (source) => set((state) => ({ sources: [source, ...state.sources] })),
  removeSource: (id) => set((state) => ({ sources: state.sources.filter((s) => s.id !== id) })),
  removeSources: (ids) => set((state) => ({
    sources: state.sources.filter((s) => !ids.includes(s.id)),
    selectedSourceIds: new Set() // Clear selection after batch delete
  })),
  updateSourceStatus: (id, status) => set((state) => ({
    sources: state.sources.map((s) => s.id === id ? { ...s, status } : s)
  })),
  updateSource: (id, updates) => set((state) => ({
    sources: state.sources.map((s) => s.id === id ? { ...s, ...updates } : s)
  })),

  // Selection Mode (for batch delete)
  isSelectionMode: false,
  selectedSourceIds: new Set(),
  toggleSelectionMode: () => set((state) => ({
    isSelectionMode: !state.isSelectionMode,
    selectedSourceIds: new Set() // Clear selection when toggling mode
  })),
  toggleSourceSelection: (id) => set((state) => {
    const newSet = new Set(state.selectedSourceIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    return { selectedSourceIds: newSet }
  }),
  selectAllSources: () => set((state) => ({
    selectedSourceIds: new Set(state.sources.map(s => String(s.id)))
  })),
  clearSourceSelection: () => set({ selectedSourceIds: new Set() }),

  // RAG Source Whitelist (null = all sources allowed, default)
  allowedSourceIds: null,
  setAllowedSourceIds: (ids) => set({ allowedSourceIds: ids }),
  toggleAllowedSource: (id) => set((state) => {
    const { sources, allowedSourceIds } = state
    // If currently null (all allowed), create set with all EXCEPT this id
    if (allowedSourceIds === null) {
      const newSet = new Set(sources.map(s => String(s.id)))
      newSet.delete(id)
      return { allowedSourceIds: newSet }
    }
    // If set exists, toggle this id
    const newSet = new Set(allowedSourceIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    // If all sources are now allowed, set to null
    if (newSet.size === sources.length) {
      return { allowedSourceIds: null }
    }
    return { allowedSourceIds: newSet }
  }),
  enableSources: (ids) => set((state) => {
    const { sources, allowedSourceIds } = state
    if (allowedSourceIds === null) return {} // Already all enabled

    const newSet = new Set(allowedSourceIds)
    ids.forEach(id => newSet.add(id))

    if (newSet.size === sources.length) {
      return { allowedSourceIds: null }
    }
    return { allowedSourceIds: newSet }
  }),
  disableSources: (ids) => set((state) => {
    const { sources, allowedSourceIds } = state
    // If currently null (all allowed), create set with all EXCEPT these ids
    if (allowedSourceIds === null) {
      const newSet = new Set(sources.map(s => String(s.id)))
      ids.forEach(id => newSet.delete(id))
      return { allowedSourceIds: newSet }
    }
    // If set exists, remove these ids
    const newSet = new Set(allowedSourceIds)
    ids.forEach(id => newSet.delete(id))
    return { allowedSourceIds: newSet }
  }),
  allowAllSources: () => set({ allowedSourceIds: null }),

  // Fetch State
  hasFetchedSources: false,
  setHasFetchedSources: (hasFetched) => set({ hasFetchedSources: hasFetched }),

  // Duplicate Management
  pendingDuplicates: [],
  showDuplicateModal: false,
  setPendingDuplicates: (files) => set({ pendingDuplicates: files }),
  setShowDuplicateModal: (show) => set({ showDuplicateModal: show }),
}))

