// 主路径 E2E 验证：登录 → 新建规划（真实 AI 工作流）→ 历史列表 → 创建徒步记录
// 用法: node scripts/verify-main-flow.mjs
// 前置: 后端(8001) + 前端(5173) 已启动
// 依赖: Chrome headless + CDP，390px 视口
import { spawn } from 'child_process'
import { mkdtempSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import path from 'path'

const PORT = 9226
const BASE = 'http://localhost:5173'
const API = 'http://localhost:8001'
const TEST_USER = { username: 'e2e_mainflow', email: 'mainflow@test.com', password: 'mainflow123' }
const PLAN_INPUT = '国庆走武功山穿越线，2天1夜，新手，帮我规划路线装备和安全'
const PLAN_MARKER = '装备清单'
const TRIP_TITLE = '武功山金顶 2 日穿越'
const SHOT_DIR = 'D:/徒步助手/frontend/scripts'
const PLAN_TIMEOUT_MS = 180000 // 真实 LLM 工作流上限 3 分钟

async function ensureUser() {
  const tryLogin = async (pw) => {
    const r = await fetch(`${API}/api/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: TEST_USER.username, password: pw }),
    })
    return r.ok
  }
  if (await tryLogin(TEST_USER.password)) return
  const reg = await fetch(`${API}/api/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(TEST_USER),
  })
  if (reg.ok) { console.log('创建测试账号', TEST_USER.username); return }
  console.error('FAIL: 测试账号状态异常'); process.exit(1)
}
await ensureUser()

const userData = mkdtempSync(path.join(tmpdir(), 'chrome-mainflow-'))
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${userData}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=390,844', 'about:blank',
], { stdio: 'ignore' })

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
  if (m.method === 'Runtime.exceptionThrown') consoleErrors.push(m.params.exceptionDetails?.exception?.description || 'exception')
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    const txt = m.params.args.map(a => a.value || a.description || '').join(' ')
    if (!txt.includes('favicon') && !txt.includes('net::')) consoleErrors.push(txt.slice(0, 120))
  }
}
await new Promise(r => ws.onopen = r)
await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })

const sleep = ms => new Promise(r => setTimeout(r, ms))
const evalJs = async (expr) => {
  const res = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
  return res.result?.value
}
const setInput = (selector, value, index) => evalJs(`(() => {
  const list = document.querySelectorAll(${JSON.stringify(selector)})
  const el = ${typeof index === 'number' ? `list[${index}]` : `list[0]`}
  if (!el) return false
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set
  setter.call(el, ${JSON.stringify(value)})
  el.dispatchEvent(new Event('input', { bubbles: true }))
  return el.value
})()`)
const clickText = (text) => evalJs(`(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.innerText.includes(${JSON.stringify(text)}))
  if (!b) return false
  b.click(); return true
})()`)
const shot = async (label) => {
  const s = await send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(path.join(SHOT_DIR, `mainflow-${label}.png`), Buffer.from(s.data, 'base64'))
}
const audit = async (label) => {
  const m = JSON.parse(await evalJs(`JSON.stringify({
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    path: location.pathname,
    body: document.body.innerText.slice(0, 150)
  })`))
  const ok = m.overflow <= 1
  console.log(`${label.padEnd(18)} ${ok ? '✅' : '❌ 溢出'} path=${m.path} | ${m.body.replace(/\\n/g, ' ')}`)
  await shot(label)
  if (consoleErrors.length) { console.log(`   ⚠️ console ${consoleErrors.length} 条: ${consoleErrors.join('; ')}`); consoleErrors.splice(0, consoleErrors.length) }
  return m
}

let failed = false
const check = (cond, label, extra = '') => {
  console.log(`   ${cond ? '✅' : '❌'} ${label}${extra ? ' | ' + extra : ''}`)
  if (!cond) failed = true
}

// ========== 1. 登录 ==========
await send('Page.navigate', { url: `${BASE}/login` }); await sleep(2500)
await setInput('input[type="text"]', TEST_USER.username)
await setInput('input[type="password"]', TEST_USER.password)
await clickText('登录'); await sleep(3500)
const loginState = JSON.parse(await evalJs(`JSON.stringify({ path: location.pathname, body: document.body.innerText.slice(0, 60) })`))
check(loginState.path === '/', '登录成功进入首页', loginState.path)

// ========== 2. 仪表盘 ==========
await audit('dashboard')

// ========== 3. 新建规划（真实工作流） ==========
await send('Page.navigate', { url: `${BASE}/plans/new` }); await sleep(3000)
await setInput('textarea', PLAN_INPUT)
await evalJs(`(() => {
  const ta = document.querySelector('textarea')
  ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }))
  return true
})()`)
await sleep(3000)
const planningStarted = await evalJs(`document.body.innerText.includes('正在规划') || document.body.innerText.includes('AI 正在分析')`)
check(planningStarted, '规划流程已启动（出现 AI 分析中提示）')

console.log('   ⏳ 等待 AI 工作流完成（真实 LLM，最长 3 分钟）...')
let planDone = false
const deadline = Date.now() + PLAN_TIMEOUT_MS
while (Date.now() < deadline) {
  await sleep(5000)
  const body = await evalJs(`document.body.innerText`)
  if (body.includes(PLAN_MARKER)) { planDone = true; break }
  if (body.includes('规划超时')) break
  if (body.includes('规划失败')) break
}
check(planDone, `规划完成（页面出现「${PLAN_MARKER}」）`)
await audit('plan-result')
if (!planDone) {
  const body = await evalJs(`document.body.innerText.slice(0, 400)`)
  console.log('   body:', body.replace(/\n+/g, ' '))
  check(false, '规划结果未在时限内出现')
}

// ========== 4. 历史列表（路由为 /plans，/plans/history 会匹配 plans/:id） ==========
await send('Page.navigate', { url: `${BASE}/plans` }); await sleep(3500)
const historyBody = await evalJs(`document.body.innerText`)
check(historyBody.includes('武功山'), '历史列表包含刚创建的规划')
await audit('history')

// ========== 5. 创建徒步记录 ==========
await send('Page.navigate', { url: `${BASE}/trips` }); await sleep(3000)
await clickText('记录'); await sleep(2000)
const modalOpen = await evalJs(`document.body.innerText.includes('记录一次徒步')`)
check(modalOpen, '徒步记录弹窗打开')
await setInput('input[placeholder*="武功山金顶"]', TRIP_TITLE)
await setInput('input[type="date"]', '2026-09-01', 0)
await setInput('input[type="date"]', '2026-09-02', 1)
await setInput('input[type="number"]', '22.5', 0)
await setInput('input[type="number"]', '1800', 1)
await evalJs(`document.querySelector('button[aria-label="4 星"]').click()`)
await setInput('input[placeholder*="晴"]', '晴，山顶有风')
await setInput('textarea', '金顶日出绝美，云海壮观', 0)
await setInput('textarea', '第二天膝盖有点累，记得带护膝', 1)
await clickText('保存记录'); await sleep(3500)
const tripsBody = await evalJs(`document.body.innerText`)
check(tripsBody.includes(TRIP_TITLE), '徒步记录创建成功并显示在列表')
const tripsStats = await evalJs(`document.body.innerText.match(/徒步次数\\s*(\\d+)/)?.[1] || '?'`)
console.log(`   徒步次数统计: ${tripsStats}`)
await audit('trips')

ws.close()
chrome.kill()
console.log('\n' + (failed ? '❌ 主路径存在失败项，截图已保存 frontend/scripts/mainflow-*.png' : '🎉 主路径全部验证通过，截图已保存 frontend/scripts/mainflow-*.png'))
process.exit(failed ? 1 : 0)
