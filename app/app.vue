<script setup lang="ts">
import { Layers, MessageSquare, Files, ChartNoAxesCombined, ShieldCheck, Settings2, Plus, ArrowUp, ArrowUpRight, ChevronDown, ChevronRight, Search, FileText, X, UploadCloud, ThumbsUp, ThumbsDown, Copy, Check, Clock3, PanelLeftClose, Sparkles, BookOpen, Ellipsis, LogOut } from 'lucide-vue-next'
import type { KnowledgeDocument, Conversation, Citation, Message } from '../shared/types'
import { sampleDocuments } from './composables/useKnowledge'
const { live, ask, loadDocuments, loadConversations, saveFeedback, uploadDocument } = useKnowledge()
const auth = useCognitoAuth()
const section = ref('Ask Atlas')
const nav = [{ name: 'Ask Atlas', icon: MessageSquare }, { name: 'Documents', icon: Files }, { name: 'Insights', icon: ChartNoAxesCombined }]
const docs = ref<KnowledgeDocument[]>(structuredClone(sampleDocuments))
const conversations = ref<Conversation[]>([])
const activeId = ref('')
const active = computed(() => conversations.value.find(c => c.id === activeId.value))
const question = ref('')
const busy = ref(false)
const error = ref('')
const notice = ref('')
const search = ref('')
const category = ref('All categories')
const selected = ref<string[]>([])
const scopeOpen = ref(false)
const uploadOpen = ref(false)
const source = ref<Citation | null>(null)
const mobileMenu = ref(false)
const fileInput = ref<HTMLInputElement>()
const modalElement = ref<HTMLElement>()
let previousFocus: HTMLElement | null = null
watch(() => Boolean(uploadOpen.value || source.value), async (open) => {
  if (!import.meta.client) return
  if (open) { previousFocus = document.activeElement as HTMLElement; await nextTick(); modalElement.value?.querySelector<HTMLButtonElement>('button')?.focus() }
  else previousFocus?.focus()
})
function trapFocus(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  const nodes = modalElement.value?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([hidden]), a[href], [tabindex="0"]')
  if (!nodes?.length) return
  const first = nodes[0]!, last = nodes[nodes.length - 1]!
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
const messagesEnd = ref<HTMLElement>()
const filteredDocs = computed(() => docs.value.filter(d => d.name.toLowerCase().includes(search.value.toLowerCase()) && (category.value === 'All categories' || d.category === category.value)))
const totalAnswers = computed(() => conversations.value.flatMap(c => c.messages).filter(m => m.role === 'assistant'))
const suggestions = [ { icon: BookOpen, title: 'Understand our policies', text: 'What is our annual leave policy?', label: 'People & culture' }, { icon: Layers, title: 'Get up to speed', text: 'What should I do in my first week?', label: 'Engineering' }, { icon: ShieldCheck, title: 'Work from anywhere', text: 'What is our remote work policy?', label: 'People & culture' } ]
onMounted(async () => {
  await auth.initialize()
  if (live.value && auth.isAuthenticated.value) {
    try {
      const [remoteDocs, remoteConversations] = await Promise.all([loadDocuments(), loadConversations()])
      if (remoteDocs.length) docs.value = remoteDocs
      conversations.value = remoteConversations
    } catch { notice.value = 'Chat is ready, but workspace data could not be loaded.' }
  }
  if (!live.value) { try { const saved = JSON.parse(localStorage.getItem('atlas-demo-v1') || 'null'); if (saved && Array.isArray(saved.conversations) && Array.isArray(saved.docs)) { conversations.value = saved.conversations; docs.value = saved.docs } } catch { notice.value = 'Your saved demo could not be restored.' } }
})
watch([conversations, docs], () => { if (import.meta.client && !live.value) { try { localStorage.setItem('atlas-demo-v1', JSON.stringify({ conversations: conversations.value, docs: docs.value })) } catch { notice.value = 'Browser storage is full. This session will not be saved.' } } }, { deep: true })
function newChat() { activeId.value = ''; question.value = ''; error.value = ''; section.value = 'Ask Atlas'; mobileMenu.value = false }
function navigate(name: string) { section.value = name; mobileMenu.value = false }
async function send(text = question.value) {
  if (!text.trim() || busy.value) return
  if (text.length > 4000) { error.value = 'Please keep your question under 4,000 characters.'; return }
  if (!active.value) { const c = { id: crypto.randomUUID(), title: text.trim().slice(0, 55), messages: [] }; conversations.value.unshift(c); activeId.value = c.id }
  const conversation = active.value!
  conversation.messages.push({ id: crypto.randomUUID(), role: 'user', text: text.trim() })
  question.value = ''; error.value = ''; busy.value = true; section.value = 'Ask Atlas'
  try { const result = await ask(text.trim(), selected.value, conversation.id); conversation.messages.push({ id: result.id, role: 'assistant', text: result.text, citations: result.citations, latencyMs: result.latencyMs }) }
  catch (cause) { error.value = cause instanceof Error && cause.message === 'AUTH_REQUIRED' ? 'Please sign in to ask your company knowledge base.' : 'The answer service is unavailable. Please try again.'; question.value = text }
  finally { busy.value = false; await nextTick(); messagesEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }
}
async function feedback(message: Message, value: 'up' | 'down') {
  if (live.value) { try { await saveFeedback(message, value) } catch { notice.value = 'Feedback could not be saved.'; return } }
  message.feedback = value; notice.value = live.value ? 'Thanks—your feedback was saved.' : 'Feedback saved for this session.'
}
async function copy(text: string) { try { await navigator.clipboard.writeText(text); notice.value = 'Answer copied.' } catch { notice.value = 'Clipboard unavailable. Select the answer to copy it.' } }
async function upload(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  for (const file of files) {
    if (!/\.(pdf|docx|txt|md)$/i.test(file.name) || file.size > 20 * 1024 * 1024 || file.size === 0) { notice.value = 'Choose a nonempty PDF, DOCX, TXT, or MD file under 20 MB.'; continue }
    if (live.value) {
      try {
        const id = await uploadDocument(file)
        docs.value.unshift({ id, name: file.name, category: 'Uncategorized', size: `${Math.max(1, Math.round(file.size / 1024))} KB`, updated: 'Just now', status: 'Processing', excerpt: 'Uploaded securely. Amazon Bedrock is indexing this document.' })
        notice.value = 'Document uploaded. Bedrock indexing has started.'
      } catch { notice.value = 'The document could not be uploaded. Check the AWS upload routes and S3 CORS.' }
      continue
    }
    docs.value.unshift({ id: crypto.randomUUID(), name: file.name, category: 'Uncategorized', size: `${Math.max(1, Math.round(file.size / 1024))} KB`, updated: 'Just now', status: 'Pending AWS', excerpt: 'This file is staged as metadata only. Its contents have not been uploaded or indexed. Connect the AWS upload and ingestion flow to make it searchable.' })
    notice.value = 'Document added to the demo queue. AWS ingestion is not connected.'
  }
  uploadOpen.value = false; section.value = 'Documents'
}
function resetDemo() { if (!confirm('Delete all locally saved demo conversations and staged document metadata?')) return; conversations.value = []; docs.value = structuredClone(sampleDocuments); newChat(); notice.value = 'Demo data reset.' }
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'mobile-open': mobileMenu }">
      <a class="brand" href="#" @click.prevent="newChat"><span class="brand-mark"><Layers :size="23" /></span>atlas<span class="brand-dot">.</span></a>
      <div class="workspace"><span class="workspace-avatar">A</span><div><strong>Acme workspace</strong><small>Company knowledge</small></div><ChevronDown :size="15" /></div>
      <button class="new-chat" @click="newChat"><Plus :size="18" /> New conversation <span>↗</span></button>
      <div class="nav-label">WORKSPACE</div>
      <nav><button v-for="item in nav" :key="item.name" :class="{ active: section === item.name }" @click="navigate(item.name)"><component :is="item.icon" :size="19" />{{ item.name }}<span v-if="item.name === 'Documents'" class="count">{{ docs.length }}</span></button></nav>
      <div class="history-label"><span class="nav-label">RECENT CONVERSATIONS</span><Clock3 :size="13" /></div>
      <div class="history"><button v-for="c in conversations.slice(0, 8)" :key="c.id" :class="{ selected: c.id === activeId }" @click="activeId = c.id; navigate('Ask Atlas')"><MessageSquare :size="15" /><span>{{ c.title }}</span></button><p v-if="!conversations.length">A little curiosity goes a long way.<br>Your conversations will appear here.</p></div>
      <div class="sidebar-bottom"><div class="knowledge-status"><span class="status-dot" /><strong>{{ live ? 'AWS connected' : 'Explore the demo' }}</strong><p>{{ live ? (auth.isAuthenticated.value ? 'Signed in and ready' : 'Sign in to ask questions') : 'Sample knowledge. No AWS costs.' }}</p></div><button class="settings-link" @click="navigate('Settings')"><Settings2 :size="18" />Workspace settings</button><div class="profile"><span class="avatar">{{ auth.isAuthenticated.value ? auth.initial.value : 'A' }}</span><div><strong>{{ auth.isAuthenticated.value ? auth.displayName.value : 'Atlas' }}</strong><small>{{ auth.isAuthenticated.value ? (auth.user?.email || 'Company account') : 'Company workspace' }}</small></div><button v-if="auth.isAuthenticated.value" aria-label="Sign out" title="Sign out" @click="auth.signOut"><LogOut :size="15" /></button><button v-else aria-label="Sign in" @click="auth.signIn"><ChevronRight :size="15" /></button></div></div>
    </aside>
    <div class="main-shell">
      <header class="topbar"><div class="breadcrumb"><button class="menu-toggle" aria-label="Toggle sidebar" @click="mobileMenu = !mobileMenu"><PanelLeftClose :size="19" /></button><span>Workspace</span><ChevronRight :size="14" /><strong>{{ section }}</strong></div><div class="header-right"><span class="demo-pill"><span />{{ live ? (auth.isAuthenticated.value ? 'AWS connected' : 'Sign-in required') : 'Demo workspace' }}</span><span class="avatar small">{{ auth.isAuthenticated.value ? auth.initial.value : 'A' }}</span></div></header>
      <main v-if="live && auth.loading.value" class="auth-page"><div class="welcome-symbol"><Layers :size="33" :stroke-width="1.6" /></div><h1>Opening your workspace…</h1></main>
      <main v-else-if="live && !auth.isAuthenticated.value" class="auth-page"><div class="welcome-symbol"><ShieldCheck :size="33" :stroke-width="1.6" /></div><div class="eyebrow">SECURE COMPANY KNOWLEDGE</div><h1>Sign in to Atlas.</h1><p>Use your company account to ask questions and view grounded answers from your documents.</p><p v-if="auth.authError.value" class="error" role="alert">{{ auth.authError.value }}</p><button class="primary auth-button" @click="auth.signIn"><LogOut class="login-icon" :size="18" />Sign in with Cognito</button></main>
      <main v-else-if="section === 'Ask Atlas'" class="chat-page" :class="{ 'has-messages': active?.messages.length }">
        <div class="chat-toolbar"><div><span class="tiny-logo"><Sparkles :size="15" /></span><strong>Knowledge assistant</strong><span class="version">BETA</span></div><button class="text-button" @click="navigate('Documents')"><Files :size="16" />{{ docs.filter(d => d.status === 'Ready').length }} sources<ChevronRight :size="14" /></button></div>
        <div v-if="!active?.messages.length" class="welcome">
          <div class="welcome-symbol"><Layers :size="33" :stroke-width="1.6" /><span class="spark-dot">✦</span></div>
          <div class="eyebrow">LESS SEARCHING. MORE KNOWING.</div>
          <h1>Your team’s knowledge.<br><span>One clear answer.</span></h1>
          <p>Ask a question. Connect the dots.<br>Get answers grounded in your company’s documents.</p>
          <div class="suggestion-grid"><button v-for="s in suggestions" :key="s.title" @click="send(s.text)"><component :is="s.icon" :size="20" /><h3>{{ s.title }}</h3><p>{{ s.text }}</p><div><span>{{ s.label }}</span><ArrowUpRight :size="17" /></div></button></div>
          <div class="trust-line"><ShieldCheck :size="15" /><span>Answers with sources, so you can check the details.</span></div>
        </div>
        <div v-else class="messages" aria-live="polite"><template v-for="m in active.messages" :key="m.id"><div v-if="m.role === 'user'" class="user-message"><span class="avatar small">R</span><p>{{ m.text }}</p></div><article v-else class="answer"><div class="answer-label"><span class="tiny-logo"><Layers :size="17" /></span><strong>Atlas</strong><span>{{ live ? 'Answer' : 'Demo answer' }}</span></div><p class="answer-text">{{ m.text }}</p><div v-if="m.citations?.length" class="citations"><span class="nav-label">SOURCES</span><button v-for="(citation, index) in m.citations" :key="citation.documentId" @click="source = citation"><span>{{ index + 1 }}</span><FileText :size="15" />{{ citation.title }}<ArrowUpRight :size="14" /></button></div><div class="answer-actions"><button aria-label="Helpful answer" :class="{ chosen: m.feedback === 'up' }" @click="feedback(m, 'up')"><ThumbsUp :size="15" /></button><button aria-label="Unhelpful answer" :class="{ chosen: m.feedback === 'down' }" @click="feedback(m, 'down')"><ThumbsDown :size="15" /></button><button aria-label="Copy answer" @click="copy(m.text)"><Copy :size="15" /></button><span>{{ ((m.latencyMs || 0) / 1000).toFixed(2) }}s · {{ live ? 'API response' : 'Sample documents' }}</span></div></article></template><div v-if="busy" class="thinking"><Sparkles :size="17" />Finding the relevant knowledge<span>•••</span></div><div ref="messagesEnd" /></div>
        <div class="composer-area"><div v-if="error" class="error" role="alert">{{ error }}</div><form class="composer" @submit.prevent="send()"><textarea v-model="question" aria-label="Ask a question" placeholder="What would you like to know?" rows="2" maxlength="4000" @keydown.enter.exact.prevent="send()" /><div class="composer-footer"><div class="scope-wrap"><button type="button" class="scope-button" @click="scopeOpen = !scopeOpen"><Files :size="15" />{{ selected.length ? `${selected.length} selected sources` : 'All documents' }}<ChevronDown :size="13" /></button><div v-if="scopeOpen" class="scope-menu"><strong>Search within</strong><label v-for="d in docs.filter(d => d.status === 'Ready')" :key="d.id"><input v-model="selected" type="checkbox" :value="d.id" />{{ d.name }}</label><button type="button" @click="selected = []; scopeOpen = false">Use all documents</button><button type="button" @click="scopeOpen = false">Done</button></div></div><div class="send-controls"><span>↵ to send</span><button class="send-button" type="submit" :disabled="!question.trim() || busy" aria-label="Send question"><ArrowUp :size="20" /></button></div></div></form><p class="composer-note">{{ live ? 'Always verify important answers against their sources.' : 'Demo mode uses sample answers. Connect Amazon Bedrock to ask your own documents.' }}</p></div>
      </main>
      <main v-else class="content-page">
        <template v-if="section === 'Documents'"><div class="page-heading"><div><div class="eyebrow">YOUR KNOWLEDGE, CONNECTED</div><h1>Documents</h1><p>A shared source of truth for your workspace.</p></div><button class="primary" @click="uploadOpen = true"><Plus :size="17" />Upload documents</button></div><div class="summary-strip"><div><Files :size="20" /><strong>{{ docs.length }}</strong><span>Total documents</span></div><div><Check :size="20" /><strong>{{ docs.filter(d => d.status === 'Ready').length }}</strong><span>Ready to explore</span></div><div><Clock3 :size="20" /><strong>{{ docs.filter(d => d.status !== 'Ready').length }}</strong><span>Awaiting ingestion</span></div></div><div class="table-tools"><label class="search-box"><Search :size="17" /><input v-model="search" placeholder="Search documents..." aria-label="Search documents" /></label><select v-model="category" aria-label="Filter by category"><option>All categories</option><option v-for="c in [...new Set(docs.map(d => d.category))]" :key="c">{{ c }}</option></select></div><div class="table-wrap"><table><thead><tr><th>Document name</th><th>Category</th><th>Status</th><th>Last updated</th><th /></tr></thead><tbody><tr v-for="d in filteredDocs" :key="d.id"><td><button class="document-name" @click="source = { documentId: d.id, title: d.name, excerpt: d.excerpt }"><span class="file-icon"><FileText :size="21" /></span><span><strong>{{ d.name }}</strong><small>{{ d.size }}</small></span></button></td><td>{{ d.category }}</td><td><span class="status-badge" :class="{ pending: d.status !== 'Ready' }"><span />{{ d.status }}</span></td><td>{{ d.updated }}</td><td><button aria-label="View document details" @click="source = { documentId: d.id, title: d.name, excerpt: d.excerpt }"><ChevronRight :size="17" /></button></td></tr></tbody></table><div v-if="!filteredDocs.length" class="empty">No documents match your search.</div></div><p class="footnote">Sample documents are fictional. Uploaded files are queued locally until AWS is connected.</p></template>
        <template v-else-if="section === 'Insights'"><div class="page-heading"><div><div class="eyebrow">QUALITY YOU CAN SEE</div><h1>Workspace insights</h1><p>Real activity from this browser’s demo session.</p></div><span class="demo-pill">Local session</span></div><div class="metric-grid"><article><span>Questions answered</span><strong>{{ totalAnswers.length }}</strong><small>Across {{ conversations.length }} conversations</small></article><article><span>Average response time</span><strong>{{ totalAnswers.length ? (totalAnswers.reduce((sum,m) => sum + (m.latencyMs || 0), 0) / totalAnswers.length / 1000).toFixed(2) : '—' }}<em v-if="totalAnswers.length">s</em></strong><small>Includes simulated demo delay</small></article><article><span>Helpful responses</span><strong>{{ totalAnswers.filter(m => m.feedback === 'up').length }}</strong><small>{{ totalAnswers.filter(m => m.feedback).length }} total ratings</small></article><article><span>Model cost</span><strong>—</strong><small>No model calls in demo mode</small></article></div><div class="integration-card"><ChartNoAxesCombined :size="27" /><h2>Make quality measurable.</h2><p>Connect your AWS telemetry to track token costs, retrieval latency, groundedness, and answer relevance over time.</p><span class="status-badge pending">Awaiting AWS integration</span></div><div class="evaluation"><h2>RAG evaluation checklist</h2><p>Your backend should run a fixed question set before each release.</p><div v-for="item in ['Retrieval relevance — did we find the right source?', 'Groundedness — does the source support the answer?', 'Abstention — does it decline unsupported questions?', 'Permission isolation — can users only retrieve allowed documents?']" :key="item"><span class="empty-check" />{{ item }}</div></div></template>
        <template v-else><div class="page-heading"><div><div class="eyebrow">WORKSPACE SETTINGS</div><h1>Built for your team.</h1><p>Configure your knowledge workspace and review connection status.</p></div></div><div class="settings-card"><h2>Connections & access</h2><div v-for="item in [{ title: 'Amazon Bedrock', detail: 'Retrieval, generation, and source citations', status: live ? 'Connected' : 'Not connected' }, { title: 'Authentication & permissions', detail: 'Cognito sign-in with API Gateway JWT authorization', status: auth.isAuthenticated.value ? 'Signed in' : 'Configured' }, { title: 'Guardrails', detail: 'Apply content and sensitive-information policies on the server', status: 'Next step' }, { title: 'CloudWatch monitoring', detail: 'Track latency, failures, and estimated model costs', status: live ? 'Logs available' : 'Not connected' }]" :key="item.title"><span><strong>{{ item.title }}</strong><p>{{ item.detail }}</p></span><span class="status-badge" :class="{ pending: item.status === 'Next step' || item.status === 'Not connected' }">{{ item.status }}</span></div></div><div class="settings-card"><h2>Session</h2><p v-if="auth.isAuthenticated.value">Signed in as {{ auth.user?.email || auth.displayName.value }}. Tokens are kept in this browser tab’s session storage.</p><p v-else>Sign in with your Cognito company account to access the knowledge assistant.</p><button v-if="auth.isAuthenticated.value" class="secondary" @click="auth.signOut"><LogOut :size="16" />Sign out</button></div></template>
      </main>
      <footer class="app-footer"><span><span class="status-dot" />{{ live ? 'Custom API' : 'Local demo' }}</span><span>Powered by knowledge. Designed for clarity.<span class="footer-brand">atlas.</span></span></footer>
    </div>
    <div v-if="uploadOpen || source" class="modal-backdrop" @click.self="uploadOpen = false; source = null" @keydown.esc="uploadOpen = false; source = null"><section ref="modalElement" @keydown="trapFocus" role="dialog" aria-modal="true" :aria-label="source ? 'Source document' : 'Upload documents'" class="modal"><button class="close-modal" aria-label="Close dialog" autofocus @click="uploadOpen = false; source = null"><X :size="20" /></button><template v-if="source"><span class="file-icon"><FileText :size="25" /></span><h2>{{ source.title }}</h2><span class="demo-pill">{{ source.documentId && sampleDocuments.some(d => d.id === source?.documentId) ? 'Fictional sample · source excerpt' : 'Document details' }}</span><blockquote>{{ source.excerpt }}</blockquote><p class="footnote">Verify answers against the original document once your source service is connected.</p></template><template v-else><h2>Add to your knowledge</h2><p>Bring your company’s documents into one place.</p><button class="upload-zone" @click="fileInput?.click()"><UploadCloud :size="34" /><strong>Choose documents to upload</strong><span>PDF, DOCX, TXT, or MD · Up to 20 MB each</span></button><input ref="fileInput" type="file" accept=".pdf,.docx,.txt,.md" multiple hidden @change="upload" /><p class="upload-info"><ShieldCheck :size="17" />Demo uploads save file names only. AWS storage and indexing are not connected.</p></template></section></div>
    <div v-if="notice" role="status" class="toast"><Check :size="17" /><span>{{ notice }}</span><button aria-label="Dismiss notification" @click="notice = ''"><X :size="17" /></button></div>
  </div>
</template>
