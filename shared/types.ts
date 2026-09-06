export interface KnowledgeDocument { id: string; name: string; category: string; size: string; updated: string; status: 'Ready' | 'Uploading' | 'Processing' | 'Failed' | 'Pending AWS'; excerpt: string }
export interface Citation { documentId: string; title: string; excerpt: string }
export interface Answer { id: string; text: string; citations: Citation[]; latencyMs: number; costUsd: number | null }
export interface Message { id: string; role: 'user' | 'assistant'; text: string; citations?: Citation[]; feedback?: 'up' | 'down'; latencyMs?: number }
export interface Conversation { id: string; title: string; messages: Message[] }
export interface WorkspaceMetrics { questionsAnswered: number; conversationCount: number; averageLatencyMs: number; helpful: number; ratings: number; blocked: number }
