import logo from './assets/Lufthansa_Group_2025.svg.png'

/**
 * Zentrale Branding-Konfiguration.
 *
 * Hier lassen sich Logo und die drei Markenfarben anpassen, um die App
 * für einen anderen Mandanten / ein anderes Unternehmen einzufärben.
 * Die Werte werden in main.jsx in ein Mantine-Theme übersetzt.
 *
 *  - primary:   Hauptfarbe – Buttons, aktive Navigation, primäre Aktionen
 *  - secondary: Sekundärfarbe – Hero-/Header-Flächen, Überschriften
 *  - accent:    Akzentfarbe – Highlights, Hervorhebungen, Badges
 *
 * Farben als HEX (#rrggbb) angeben. Das Logo kann durch eine andere Datei
 * im assets-Ordner ersetzt werden (Import oben anpassen) oder durch eine URL.
 */
export const branding = {
  name: 'AI Facilitator',
  tagline: 'AI Enablement für die Lufthansa Group',
  logo,
  logoAlt: 'Lufthansa Group',
  colors: {
    primary: '#0e2eb8',
    secondary: '#05164d',
    accent: '#ffb81c',
  },
}
