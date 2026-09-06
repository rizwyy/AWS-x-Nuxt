import type { Answer, Conversation, KnowledgeDocument, Message, WorkspaceMetrics } from '../../shared/types'

export const sampleDocuments: KnowledgeDocument[] = [
  { id: 'leave', name: 'leave-policy.pdf', category: 'People & culture', size: '124 KB', updated: 'Sep 6, 2026', status: 'Ready', excerpt: 'Full-time employees receive 25 days of paid annual leave. Request leave through the People portal at least two weeks ahead. Your manager approves requests. Up to 5 unused days can carry over until March 31 of the following year.' },
  { id: 'remote', name: 'Remote work policy.pdf', category: 'People & culture', size: '840 KB', updated: 'Sep 3, 2026', status: 'Ready', excerpt: 'Employees can work remotely up to three days per week. Coordinate office days with your team. Work outside your country of employment requires prior written approval from People Operations. Each employee has a $500 annual home office equipment allowance.' },
  { id: 'onboarding', name: 'onboarding-guide.pdf', category: 'Engineering', size: '96 KB', updated: 'Sep 6, 2026', status: 'Ready', excerpt: 'During your first week, activate SSO and MFA, request GitHub access through IT, set up the development environment, and meet your onboarding buddy.' }
]

export function useKnowledge() {
  const config = useRuntimeConfig()
  const auth = useCognitoAuth()
  const live = computed(() => Boolean(config.public.apiBase))
  function headers() {
    const token = auth.tokens.value?.access_token
    if (!token) throw new Error('AUTH_REQUIRED')
    return { Authorization: `Bearer ${token}` }
  }
  async function ask(question: string, documentIds: string[], conversationId: string): Promise<Answer> {
    if (live.value) {
      return await $fetch<Answer>(`${config.public.apiBase}/chat`, { method: 'POST', headers: headers(), body: { question, documentIds, conversationId } })
    }
    const start = performance.now()
    await new Promise(resolve => setTimeout(resolve, 650))
    const q = question.toLowerCase()
    const keywords: Record<string, RegExp> = { leave: /leave|holiday|vacation|paid|carry/, remote: /remote|home|office|equipment/, onboarding: /onboard|first week|github|development/ }
    const hits = sampleDocuments.filter(d => (!documentIds.length || documentIds.includes(d.id)) && keywords[d.id]?.test(q))
    return { id: crypto.randomUUID(), text: hits.length ? hits.map(d => d.excerpt).join('\n\n') : 'I couldn’t find an answer in the selected demo documents. Try asking about annual leave, remote work, onboarding, security, or expenses. Uploaded files become searchable after your AWS ingestion service is connected.', citations: hits.map(d => ({ documentId: d.id, title: d.name, excerpt: d.excerpt })), latencyMs: Math.round(performance.now() - start), costUsd: null }
  }
  async function loadDocuments() { return await $fetch<KnowledgeDocument[]>(`${config.public.apiBase}/documents`, { headers: headers() }) }
  async function loadConversations() { return await $fetch<Conversation[]>(`${config.public.apiBase}/conversations`, { headers: headers() }) }
  async function loadMetrics() { return await $fetch<WorkspaceMetrics>(`${config.public.apiBase}/metrics`, { headers: headers() }) }
  async function saveFeedback(message: Message, rating: 'up' | 'down') { await $fetch(`${config.public.apiBase}/feedback`, { method: 'POST', headers: headers(), body: { messageId: message.id, rating } }) }
  async function uploadDocument(file: File) {
    const contentType = file.type || (file.name.endsWith('.md') ? 'text/markdown' : 'text/plain')
    const ticket = await $fetch<{ documentId: string, uploadUrl: string, headers: Record<string, string> }>(`${config.public.apiBase}/documents/upload-url`, { method: 'POST', headers: headers(), body: { filename: file.name, contentType, size: file.size } })
    await $fetch(ticket.uploadUrl, { method: 'PUT', headers: ticket.headers, body: file })
    await $fetch(`${config.public.apiBase}/documents/${ticket.documentId}/ingest`, { method: 'POST', headers: headers() })
    return ticket.documentId
  }
  return { live, ask, loadDocuments, loadConversations, loadMetrics, saveFeedback, uploadDocument }
}
