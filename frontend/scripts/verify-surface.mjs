import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { chromium } from '@playwright/test'

const args = process.argv.slice(2)

function readArg(name, fallback) {
  const index = args.indexOf(name)
  if (index >= 0 && index + 1 < args.length) {
    return args[index + 1]
  }
  return fallback
}

const baseURL = readArg('--base-url', process.env.FRONTEND_VERIFY_BASE_URL || 'http://127.0.0.1:4173')
const distDirArg = readArg('--dist-dir', process.env.FRONTEND_DIST_DIR || 'dist')
const distDir = path.resolve(process.cwd(), distDirArg)

const routes = [
  { path: '/', finalPath: '/', markers: ['方案與價格', '免費開始', '登入'] },
  { path: '/pricing', finalPath: '/pricing', markers: ['方案與價格', '免費開始'] },
  { path: '/login', finalPath: '/login', markers: ['企業專屬AI人資長', '登入'] },
  { path: '/signup', finalPath: '/signup', markers: ['建立帳號', '公開網站提供方案'] },
  { path: '/welcome', finalPath: '/', markers: ['企業專屬AI人資長'] },
  { path: '/app/documents', finalPath: '/login', markers: ['登入'] },
  { path: '/usage', finalPath: '/login', markers: ['登入'] },
]

function getDistBundle() {
  const assetsDir = path.join(distDir, 'assets')
  const files = fs.readdirSync(assetsDir)
  const js = files.filter((file) => /^index-.*\.js$/.test(file)).sort().at(-1)
  const css = files.filter((file) => /^index-.*\.css$/.test(file)).sort().at(-1)

  if (!js || !css) {
    throw new Error(`Could not find built entry assets under ${assetsDir}`)
  }

  return { js, css }
}

async function getPageBundle(page) {
  const script = await page.locator('script[src*="/assets/index-"]').first().getAttribute('src')
  const style = await page.locator('link[href*="/assets/index-"][rel="stylesheet"]').first().getAttribute('href')
  return {
    script: script ? path.basename(script) : null,
    style: style ? path.basename(style) : null,
  }
}

async function main() {
  const distBundle = getDistBundle()
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const failures = []
  const publicBundles = new Map()

  try {
    for (const route of routes) {
      await page.goto(new URL(route.path, `${baseURL}/`).toString(), { waitUntil: 'networkidle' })
      const finalPath = new URL(page.url()).pathname
      const content = await page.content()

      console.log(`[check] ${route.path} -> ${finalPath}`)

      if (finalPath !== route.finalPath) {
        failures.push(`${route.path} ended at ${finalPath}, expected ${route.finalPath}`)
      }

      for (const marker of route.markers) {
        if (!content.includes(marker)) {
          failures.push(`${route.path} is missing marker: ${marker}`)
        }
      }

      if (['/', '/pricing', '/login', '/signup'].includes(route.path)) {
        publicBundles.set(route.path, await getPageBundle(page))
      }
    }

    const referenceBundle = publicBundles.get('/')
    for (const [route, bundle] of publicBundles.entries()) {
      if (bundle.script !== referenceBundle?.script || bundle.style !== referenceBundle?.style) {
        failures.push(`${route} served a different entry bundle: ${JSON.stringify(bundle)} vs ${JSON.stringify(referenceBundle)}`)
      }
    }

    if (referenceBundle?.script !== distBundle.js) {
      failures.push(`Live JS bundle ${referenceBundle?.script} does not match dist ${distBundle.js}`)
    }

    if (referenceBundle?.style !== distBundle.css) {
      failures.push(`Live CSS bundle ${referenceBundle?.style} does not match dist ${distBundle.css}`)
    }
  } finally {
    await browser.close()
  }

  if (failures.length > 0) {
    console.error('\n[fail] Frontend surface verification failed:')
    for (const failure of failures) {
      console.error(`  - ${failure}`)
    }
    process.exit(1)
  }

  console.log('\n[pass] Frontend surface verification passed.')
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})