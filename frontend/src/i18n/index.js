import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import de from './locales/de.json'
import en from './locales/en.json'

// Central i18n configuration. Add new languages here and create a matching
// JSON file under ./locales.
export const SUPPORTED_LANGUAGES = ['de', 'en']
const STORAGE_KEY = 'app-language'

function initialLanguage() {
  // 1. An explicit user choice from an earlier session takes precedence.
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) return stored
  } catch {
    /* localStorage not available – fall back to the browser language */
  }

  // 2. Browser language(s) – the first supported match wins.
  if (typeof navigator !== 'undefined') {
    const candidates = navigator.languages?.length ? navigator.languages : [navigator.language]
    for (const lang of candidates) {
      const base = lang?.toLowerCase().split('-')[0] // "de-DE" -> "de"
      if (SUPPORTED_LANGUAGES.includes(base)) return base
    }
  }

  // 3. Fallback.
  return 'de'
}

i18n.use(initReactI18next).init({
  resources: {
    de: { translation: de },
    en: { translation: en },
  },
  lng: initialLanguage(),
  fallbackLng: 'de',
  interpolation: { escapeValue: false }, // React already protects against XSS
})

// Persist the language choice and keep <html lang> up to date.
i18n.on('languageChanged', (lng) => {
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    /* ignore */
  }
  if (typeof document !== 'undefined') document.documentElement.lang = lng
})

if (typeof document !== 'undefined') document.documentElement.lang = i18n.language

export default i18n
