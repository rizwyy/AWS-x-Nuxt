type CognitoTokens = {
  access_token: string
  id_token: string
  refresh_token?: string
  expires_in: number
}

type CognitoClaims = {
  email?: string
  name?: string
  given_name?: string
  username?: string
  'cognito:username'?: string
  exp?: number
}

const TOKEN_KEY = 'atlas-cognito-session'
const VERIFIER_KEY = 'atlas-cognito-verifier'
const STATE_KEY = 'atlas-cognito-state'

function encode(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function randomValue(size = 32) {
  const bytes = new Uint8Array(size)
  crypto.getRandomValues(bytes)
  return encode(bytes)
}

function claims(token?: string): CognitoClaims {
  if (!token) return {}
  try {
    const payload = token.split('.')[1]
    if (!payload) return {}
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=')))
  } catch { return {} }
}

export function useCognitoAuth() {
  const config = useRuntimeConfig()
  const tokens = useState<CognitoTokens | null>('cognito-tokens', () => null)
  const loading = useState('cognito-loading', () => true)
  const authError = useState('cognito-error', () => '')
  const initialized = useState('cognito-initialized', () => false)
  const configured = computed(() => Boolean(config.public.cognitoDomain && config.public.cognitoClientId))
  const user = computed(() => claims(tokens.value?.id_token || tokens.value?.access_token))
  const isAuthenticated = computed(() => Boolean(tokens.value?.access_token && (user.value.exp || 0) * 1000 > Date.now()))
  const displayName = computed(() => user.value.name || user.value.given_name || user.value.email?.split('@')[0] || user.value['cognito:username'] || user.value.username || 'Team member')
  const initial = computed(() => displayName.value.charAt(0).toUpperCase())

  function save(value: CognitoTokens | null) {
    tokens.value = value
    if (!import.meta.client) return
    if (value) sessionStorage.setItem(TOKEN_KEY, JSON.stringify(value))
    else sessionStorage.removeItem(TOKEN_KEY)
  }

  async function exchange(params: URLSearchParams) {
    const response = await $fetch<CognitoTokens>(`${config.public.cognitoDomain}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params.toString()
    })
    save(response)
  }

  async function initialize() {
    if (!import.meta.client || initialized.value) return
    initialized.value = true
    loading.value = true
    try {
      const stored = sessionStorage.getItem(TOKEN_KEY)
      if (stored) save(JSON.parse(stored))
      const url = new URL(window.location.href)
      const code = url.searchParams.get('code')
      const returnedState = url.searchParams.get('state')
      const verifier = sessionStorage.getItem(VERIFIER_KEY)
      const expectedState = sessionStorage.getItem(STATE_KEY)
      if (url.searchParams.get('error')) throw new Error(url.searchParams.get('error_description') || 'Sign-in was cancelled.')
      if (code) {
        if (!verifier || !returnedState || returnedState !== expectedState) {
          authError.value = 'That sign-in was started outside Atlas. Please sign in again.'
        } else {
          await exchange(new URLSearchParams({ grant_type: 'authorization_code', client_id: config.public.cognitoClientId, code, redirect_uri: config.public.cognitoRedirectUri, code_verifier: verifier }))
          authError.value = ''
        }
        sessionStorage.removeItem(VERIFIER_KEY)
        sessionStorage.removeItem(STATE_KEY)
        history.replaceState({}, '', url.pathname + url.hash)
      }
      if (tokens.value && !isAuthenticated.value) save(null)
    } catch (error) {
      save(null)
      authError.value = error instanceof Error ? error.message : 'Sign-in could not be completed.'
    } finally { loading.value = false }
  }

  async function signIn() {
    if (!configured.value) return
    authError.value = ''
    const verifier = randomValue(48)
    const state = randomValue()
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
    sessionStorage.setItem(VERIFIER_KEY, verifier)
    sessionStorage.setItem(STATE_KEY, state)
    const query = new URLSearchParams({ response_type: 'code', client_id: config.public.cognitoClientId, redirect_uri: config.public.cognitoRedirectUri, scope: 'openid email', state, code_challenge_method: 'S256', code_challenge: encode(new Uint8Array(digest)) })
    window.location.assign(`${config.public.cognitoDomain}/oauth2/authorize?${query}`)
  }

  function signOut() {
    save(null)
    const query = new URLSearchParams({ client_id: config.public.cognitoClientId, logout_uri: config.public.cognitoLogoutUri })
    window.location.assign(`${config.public.cognitoDomain}/logout?${query}`)
  }

  return { tokens, user: user as typeof user & CognitoClaims, configured, loading, authError, isAuthenticated, displayName, initial, initialize, signIn, signOut }
}
