import { createTheme } from '@mantine/core'
import { branding } from './branding'

// Mischt zwei HEX-Farben mit gegebenem Anteil (0..1 Richtung target).
function mix(hex, target, amount) {
  const a = hexToRgb(hex)
  const b = hexToRgb(target)
  const r = Math.round(a.r + (b.r - a.r) * amount)
  const g = Math.round(a.g + (b.g - a.g) * amount)
  const bl = Math.round(a.b + (b.b - a.b) * amount)
  return rgbToHex(r, g, bl)
}

function hexToRgb(hex) {
  const clean = hex.replace('#', '')
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  }
}

function rgbToHex(r, g, b) {
  const toHex = (n) => Math.max(0, Math.min(255, n)).toString(16).padStart(2, '0')
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}

// Erzeugt aus einer Basisfarbe eine 10-stufige Mantine-Palette.
// Index 6 entspricht der Basisfarbe (Mantine-Standard für primaryShade).
function generatePalette(base) {
  return [
    mix(base, '#ffffff', 0.92),
    mix(base, '#ffffff', 0.82),
    mix(base, '#ffffff', 0.62),
    mix(base, '#ffffff', 0.42),
    mix(base, '#ffffff', 0.24),
    mix(base, '#ffffff', 0.1),
    base,
    mix(base, '#000000', 0.18),
    mix(base, '#000000', 0.32),
    mix(base, '#000000', 0.46),
  ]
}

const bodyFont = "'Hanken Grotesk', system-ui, 'Segoe UI', sans-serif"
const displayFont = "'Bricolage Grotesque', system-ui, 'Segoe UI', sans-serif"

// Überträgt die Branding-Farben in globale CSS-Variablen, damit alle Komponenten
// (inkl. Verläufe/Glows) automatisch der zentralen Branding-Konfiguration folgen.
export function applyBrandingVars(target) {
  const root = target || document.documentElement
  const { primary, secondary, accent } = branding.colors
  const rgb = (hex) => {
    const { r, g, b } = hexToRgb(hex)
    return `${r}, ${g}, ${b}`
  }
  const vars = {
    '--ink': secondary,
    '--ink-soft': mix(secondary, '#ffffff', 0.08),
    '--ink-rgb': rgb(secondary),
    '--blue': primary,
    '--blue-rgb': rgb(primary),
    '--gold': accent,
    '--gold-soft': mix(accent, '#ffffff', 0.35),
    '--gold-rgb': rgb(accent),
  }
  Object.entries(vars).forEach(([key, value]) => root.style.setProperty(key, value))
}

export const theme = createTheme({
  primaryColor: 'brand',
  primaryShade: 6,
  fontFamily: bodyFont,
  fontFamilyMonospace: "'SF Mono', ui-monospace, monospace",
  defaultRadius: 'lg',
  headings: {
    fontFamily: displayFont,
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '2.6rem', lineHeight: '1.1', fontWeight: '600' },
      h2: { fontSize: '1.85rem', lineHeight: '1.18', fontWeight: '600' },
      h3: { fontSize: '1.35rem', lineHeight: '1.25', fontWeight: '600' },
    },
  },
  colors: {
    brand: generatePalette(branding.colors.primary),
    secondary: generatePalette(branding.colors.secondary),
    accent: generatePalette(branding.colors.accent),
  },
  components: {
    Button: {
      defaultProps: { radius: 'md' },
      styles: { root: { fontWeight: 600, letterSpacing: '-0.01em' } },
    },
    TextInput: { defaultProps: { radius: 'md', size: 'md' } },
    PasswordInput: { defaultProps: { radius: 'md', size: 'md' } },
    Paper: { defaultProps: { radius: 'lg' } },
  },
})
