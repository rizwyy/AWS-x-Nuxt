export default defineNuxtConfig({
  compatibilityDate: '2025-07-01',
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  app: { head: { title: 'Atlas — Company knowledge, connected', meta: [{ name: 'description', content: 'Your team’s knowledge workspace. Find clear answers grounded in your company documents.' }] } },
  runtimeConfig: {
    public: {
      apiBase: '',
      cognitoDomain: '',
      cognitoClientId: '',
      cognitoRedirectUri: 'http://localhost:3000',
      cognitoLogoutUri: 'http://localhost:3000'
    }
  }
})
