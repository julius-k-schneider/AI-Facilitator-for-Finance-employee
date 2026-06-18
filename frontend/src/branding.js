import logo from './assets/Lufthansa_Group_2025.svg.png'

/**
 * Central branding configuration.
 *
 * Logo and the three brand colors can be adjusted here to re-skin the app
 * for a different tenant / company. The values are translated into a Mantine
 * theme in main.jsx.
 *
 *  - primary:   Primary color – buttons, active navigation, primary actions
 *  - secondary: Secondary color – hero/header surfaces, headings
 *  - accent:    Accent color – highlights, emphasis, badges
 *
 * Provide colors as HEX (#rrggbb). The logo can be replaced with another file
 * in the assets folder (adjust the import above) or with a URL.
 */
export const branding = {
  name: 'AI Facilitator',
  tagline: 'AI Enablement for the Lufthansa Group',
  logo,
  logoAlt: 'Lufthansa Group',
  colors: {
    primary: '#0e2eb8',
    secondary: '#05164d',
    accent: '#ffb81c',
  },
}
