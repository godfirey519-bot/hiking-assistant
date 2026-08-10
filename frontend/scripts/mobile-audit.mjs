// 移动端适配验证脚本：用 Chrome headless + CDP 在 390x844 视口下检测横向溢出并截图
// 用法: node scripts/mobile-audit.mjs
import { spawn } from 'child_process'
import { mkdtempSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import path from 'path'

const PORT = 9222
const BASE = 'http://localhost:5173'
const API = 'http://localhost:8001'
const VIEWPORT = { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }

// 1) 登录拿 token
const loginRes = await fetch(`${API}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'e2e_test_0804', password: 'test123456' }),
})
const { access_token, user } = await loginRes.json()
const authJson = JSON.stringify({ state: { token: access_token, user }, version: 0 })

// 2) 启动 Chrome headless
const userData = mkdtempSync(path.join(tmpdir(), 'chrome-audit-'))
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${userData}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=390,844', 'about:blank',
], { stdio: 'ignore' })

// 等待调试端口
let wsUrl = null
for (let i = 0; i < 50; i++) {
  try {
    const list = await (await fetch(`http://localhost:${PORT}/json`)).json()
    const page = list.find(t => t.type === 'page')
    if (page) { wsUrl = page.webSocketDebuggerUrl; break }
  } catch { }
  await new Promise(r => setTimeout(r, 200))
}
if (!wsUrl) { console.error('FAIL: 无法连接 Chrome 调试端口'); chrome.kill(); process.exit(1) }

// 3) CDP 客户端
const ws = new WebSocket(wsUrl)
let msgId = 0
const pending = new Map()
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++msgId
  pending.set(id, { resolve, reject })
  ws.send(JSON.stringify({ id, method, params }))
})
const consoleErrors = []
ws.onmessage = (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id).resolve(m.result); pending.delete(m.id) }
  if (m.method === 'Runtime.exceptionThrown') {
    consoleErrors.push(m.params.exceptionDetails?.exception?.description || 'exception')
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    const txt = m.params.args.map(a => a.value || a.description || '').join(' ')
    if (!txt.includes('favicon') && !txt.includes('net::')) consoleErrors.push(txt.slice(0, 120))
  }
}
await new Promise(r => ws.onopen = r)

// 注入登录态（在页面脚本运行前）
await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', {
  width: VIEWPORT.width, height: VIEWPORT.height,
  deviceScaleFactor: VIEWPORT.deviceScaleFactor, mobile: VIEWPORT.mobile,
})
await send('Page.addScriptToEvaluateOnNewDocument', {
  source: `localStorage.setItem('hiking-auth', ${JSON.stringify(authJson)});`,
})

const sleep = ms => new Promise(r => setTimeout(r, ms))

async function audit(label, url, interact) {
  await send('Page.navigate', { url })
  await sleep(4000) // 等 SPA 渲染
  if (interact) await interact()

  // 检测横向溢出 + 视口元信息
  const metrics = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      viewport: getComputedStyle(document.documentElement).width
    })`,
    returnByValue: true,
  })
  const m = JSON.parse(metrics.result.value)

  // 截图
  const shot = await send('Page.captureScreenshot', { format: 'png' })
  const file = path.join('D:/徒步助手/frontend/scripts', `mobile-${label}.png`)
  writeFileSync(file, Buffer.from(shot.data, 'base64'))

  const status = m.overflow > 1 ? '❌ 横向溢出' : '✅ 无溢出'
  console.log(`${label.padEnd(18)} ${status}  (scrollW=${m.scrollW}, innerW=${m.innerW}, overflow=${m.overflow})`)

  // console 错误
  if (consoleErrors.length) {
    console.log(`   ⚠️ console 错误: ${consoleErrors.length} 条`)
    consoleErrors.splice(0, consoleErrors.length)
  }
  return m
}

// 逐页审计
await audit('dashboard', `${BASE}/`)
await audit('equipment', `${BASE}/equipment`)
await audit('plans-new', `${BASE}/plans/new`)
await audit('routes', `${BASE}/routes`)
await audit('trips', `${BASE}/trips`)
await audit('settings', `${BASE}/settings`)

ws.close()
chrome.kill()
console.log('\n截图已保存到 frontend/scripts/mobile-*.png')
process.exit(0)
