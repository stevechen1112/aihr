import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { publicApi } from '../api'

interface Branding {
  tenant_name: string
  brand_name: string | null
  brand_logo_url: string | null
  brand_primary_color: string | null
  brand_secondary_color: string | null
  brand_favicon_url: string | null
}

const defaultBranding: Branding = {
  tenant_name: '',
  brand_name: null,
  brand_logo_url: null,
  brand_primary_color: null,
  brand_secondary_color: null,
  brand_favicon_url: null,
}

const BrandingContext = createContext<Branding>(defaultBranding)

export function useBranding() {
  return useContext(BrandingContext)
}

/** Apply CSS custom properties from branding */
function applyBrandingCSS(branding: Branding) {
  const root = document.documentElement
  if (branding.brand_primary_color) {
    root.style.setProperty('--color-primary', branding.brand_primary_color)
    // Darken primary for hover (simple approach)
    root.style.setProperty('--color-primary-hover', darkenColor(branding.brand_primary_color, 15))
  }
  if (branding.brand_favicon_url) {
    let link = document.querySelector<HTMLLinkElement>("link[rel*='icon']")
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    link.href = branding.brand_favicon_url
  }
  if (branding.brand_name || branding.tenant_name) {
    document.title = branding.brand_name || branding.tenant_name || 'UniHR'
  }
}

function darkenColor(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = Math.max(0, (num >> 16) - Math.round(2.55 * percent))
  const g = Math.max(0, ((num >> 8) & 0x00ff) - Math.round(2.55 * percent))
  const b = Math.max(0, (num & 0x0000ff) - Math.round(2.55 * percent))
  return `#${(r << 16 | g << 8 | b).toString(16).padStart(6, '0')}`
}

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>(defaultBranding)

  useEffect(() => {
    // Resolve branding from current domain
    const domain = window.location.hostname
    publicApi
      .branding({ domain: domain !== 'localhost' ? domain : undefined })
      .then((data: Branding) => {
        setBranding(data)
        applyBrandingCSS(data)
      })
      .catch(() => {
        // Silently fall back to defaults
      })
  }, [])

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  )
}
