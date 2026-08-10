// 在每次构建前自动 bump Service Worker 缓存名。
// sw.js 里 CACHE_NAME = 'hiking-assistant-v1'，前端更新后浏览器靠内容变化触发更新，
// 旧缓存则由 activate 阶段按版本号清理。此脚本用构建时间戳替换版本号，避免手动改。
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const swPath = fileURLToPath(new URL('../public/sw.js', import.meta.url))
const content = readFileSync(swPath, 'utf8')

// 用时间戳的 base36 简短版本，如 hiking-assistant-vm3k2x0
const version = Date.now().toString(36)
const next = content.replace(
  /hiking-assistant-v[\w-]+/,
  `hiking-assistant-v${version}`
)

if (next === content) {
  console.error('[bump-sw] 未找到 CACHE_NAME 版本号，请检查 public/sw.js')
  process.exit(1)
}

writeFileSync(swPath, next)
console.log(`[bump-sw] CACHE_NAME -> hiking-assistant-v${version}`)
