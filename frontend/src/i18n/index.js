import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import de from './locales/de.json'
import en from './locales/en.json'

// Zentrale i18n-Konfiguration. Neue Sprachen hier ergänzen und eine
// passende JSON-Datei unter ./locales anlegen.
export const SUPPORTED_LANGUAGES = ['de', 'en']
const STORAGE_KEY = 'app-language'

function initialLanguage() {
  // 1. Explizite Nutzerwahl aus einer früheren Sitzung hat Vorrang.
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) return stored
  } catch {
    /* localStorage nicht verfügbar – weiter mit Browsersprache */
  }

  // 2. Browsersprache(n) – erste unterstützte Übereinstimmung gewinnt.
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
  interpolation: { escapeValue: false }, // React schützt bereits vor XSS
})

// Sprachwahl persistieren und <html lang> aktuell halten.
i18n.on('languageChanged', (lng) => {
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    /* ignorieren */
  }
  if (typeof document !== 'undefined') document.documentElement.lang = lng
})

if (typeof document !== 'undefined') document.documentElement.lang = i18n.language

export default i18n
