import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const distDir = resolve(process.argv[2] ?? 'dist')
const base = normalizeBase(process.argv[3] ?? '/')
const readDist = (path, encoding) => readFile(resolve(distDir, path), encoding)

function normalizeBase(value) {
  return `/${value.split('/').filter(Boolean).join('/')}${value === '/' ? '' : '/'}`
}

function pngSize(buffer) {
  assert.equal(buffer.toString('ascii', 1, 4), 'PNG', 'icon must be a PNG')
  return [buffer.readUInt32BE(16), buffer.readUInt32BE(20)]
}

const [html, manifestText, serviceWorker, registerScript, icon192, icon512] = await Promise.all([
  readDist('index.html', 'utf8'),
  readDist('manifest.webmanifest', 'utf8'),
  readDist('sw.js', 'utf8'),
  readDist('registerSW.js', 'utf8'),
  readDist('icons/192.png'),
  readDist('icons/512.png'),
])
const manifest = JSON.parse(manifestText)
const deploymentUrl = new URL(base, 'https://example.test')
const deployedPath = (value) => new URL(value, deploymentUrl).pathname

assert.equal(manifest.name, 'Palworld Pal Editor')
assert.equal(manifest.short_name, 'Pal Editor')
assert.equal(manifest.display, 'standalone')
assert.equal(manifest.theme_color, '#181818')
assert.equal(manifest.background_color, '#181818')
assert.equal(deployedPath(manifest.start_url), base)
assert.equal(deployedPath(manifest.scope), base)

assert.deepEqual(pngSize(icon192), [192, 192])
assert.deepEqual(pngSize(icon512), [512, 512])
for (const size of ['192x192', '512x512']) {
  const icon = manifest.icons.find((candidate) => candidate.sizes === size)
  assert.ok(icon, `manifest must include the ${size} icon`)
  assert.equal(icon.type, 'image/png')
  assert.equal(icon.purpose, 'any')
  assert.equal(deployedPath(icon.src), `${base}icons/${size.slice(0, 3)}.png`)
}

assert.match(html, new RegExp(`href=["']${base.replaceAll('/', '\\/')}manifest\\.webmanifest["']`))
assert.match(html, new RegExp(`src=["']${base.replaceAll('/', '\\/')}registerSW\\.js["']`))
assert.match(registerScript, new RegExp(`register\\(["']${base.replaceAll('/', '\\/')}sw\\.js["'],\\s*\\{\\s*scope:\\s*["']${base.replaceAll('/', '\\/')}["']`))

assert.match(serviceWorker, /index\.html/)
assert.match(serviceWorker, /assets\//)
assert.match(serviceWorker, /CacheFirst/)
assert.match(serviceWorker, /\/image\//)
assert.match(serviceWorker, /searchParams\.get\(["']v["']\)/)
assert.match(serviceWorker, /\[0-9a-f\].*\{6\}/i)
assert.doesNotMatch(serviceWorker, /\/api(?:\/|["'])/)

console.log(`PWA artifacts are valid for base ${base}`)
