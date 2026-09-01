// 密码重置流程 E2E 验证：Chrome headless + CDP，390px 视口
// 用法: node scripts/verify-password-reset.mjs
// 前置: 后端(8001) + 前端(5173) 已启动，且有测试账号 test_pwreset（脚本会自动创建）
import { spawn } from 'child_process'
import { mkdtempSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import path from 'path'

const PORT = 9223
const BASE = 'http://localhost:5173'
const API = 'http://localhost:8001'
const TEST_USER = { username: 'test_pwreset', email: 'pwreset@example.com', password: 'oldpass123' }
const NEW_PASSWORD = 'newpass456'
const SHOT_DIR = 'D:/徒步助手/frontend/scripts'

// 0) 确保测试账号存在（兼容旧密码/新密码/全新注册三种状态）
async function ensureUser() {
  const tryLogin = async (pw) => {
    const r = await fetch(`${API}/api/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: TEST_USER.username, password: pw }),
    })
    return r.ok
  }
  if (await tryLogin(TEST_USER.password)) return
  if (await tryLogin(NEW_PASSWORD)) { console.log('测试账号密码已是新密码，直接使用'); return }
  const reg = await fetch(`${API}/api/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(TEST_USER),
  })
  if (reg.ok) { console.log('创建测试账号', TEST_USER.username); return }
  console.error('FAIL: 测试账号状态异常', await reg.text()); process.exit(1)
}
await ensureUser()

// 1) 启动 Chrome headless（不注入登录态 → 可访问 /forgot-password /reset-password）
const userData = mkdtempSync(path.join(tmpdir(), 'chrome-pwreset-'))
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

// React 受控输入赋值：用原生 setter + input 事件（支持选择器或索引）
const setInput = (selector, value, index) => evalJs(`(() => {
  const list = document.querySelectorAll(${JSON.stringify(selector)})
  const el = ${typeof index === 'number' ? `list[${index}]` : `list[0]`}
  if (!el) return false
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(el, ${JSON.stringify(value)})
  el.dispatchEvent(new Event('input', { bubbles: true }))
  return el.value
})()`)

async function audit(label, url, { wait = 3000 } = {}) {
  await send('Page.navigate', { url })
  await sleep(wait)
  const m = JSON.parse(await evalJs(`JSON.stringify({
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    scrollW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
    path: location.pathname,
    hasResetLink: !!document.querySelector('a[href*="forgot-password"]'),
    bodyText: document.body.innerText.slice(0, 100)
  })`))
  const shot = await send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(path.join(SHOT_DIR, `pwreset-${label}.png`), Buffer.from(shot.data, 'base64'))
  const status = m.overflow > 1 ? '❌ 溢出' : '✅'
  console.log(`${label.padEnd(16)} ${status} path=${m.path} overflow=${m.overflow} ${m.bodyText ? '| ' + m.bodyText.replace(/\\n/g, ' ') : ''}`)
  if (consoleErrors.length) { console.log(`   ⚠️ console 错误 ${consoleErrors.length} 条: ${consoleErrors.join('; ')}`); consoleErrors.splice(0, consoleErrors.length) }
  return m
}

// 2) 登录页：验证"忘记密码？"链接
const login = await audit('login', `${BASE}/login`)
if (!login.hasResetLink) console.error('❌ FAIL: 登录页没有"忘记密码？"链接')
else console.log('   ✅ 登录页有"忘记密码？"链接')

// 3) 进入忘记密码页，填邮箱提交
await send('Page.navigate', { url: `${BASE}/forgot-password` }); await sleep(2500)
await setInput('input[type="email"]', TEST_USER.email)
await evalJs(`document.querySelector('button[type="submit"]').click()`)
await sleep(2500)
const step1 = JSON.parse(await evalJs(`JSON.stringify({
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  bodyText: document.body.innerText.slice(0, 200)
})`))
const shot1 = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync(path.join(SHOT_DIR, 'pwreset-1-forgot-submit.png'), Buffer.from(shot1.data, 'base64'))
const step1ok = step1.bodyText.includes('前往设置新密码')
console.log(`${'forgot-submit'.padEnd(16)} ${step1.overflow > 1 ? '❌ 溢出' : '✅'} overflow=${step1.overflow} | 成功卡片: ${step1ok ? '✅' : '❌'}`)
if (!step1ok) { console.error('   FAIL: 忘记密码提交后未显示"前往设置新密码"'); console.error('   body:', step1.bodyText); ws.close(); chrome.kill(); process.exit(1) }

// 4) 点击"前往设置新密码" → 进入重置页
await evalJs(`[...document.querySelectorAll('button')].find(b => b.innerText.includes('前往设置新密码')).click()`)
await sleep(2500)
const step2 = JSON.parse(await evalJs(`JSON.stringify({
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  path: location.pathname,
  hasToken: location.search.includes('token='),
  bodyText: document.body.innerText.slice(0, 100)
})`))
const shot2 = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync(path.join(SHOT_DIR, 'pwreset-2-reset-page.png'), Buffer.from(shot2.data, 'base64'))
console.log(`${'reset-page'.padEnd(16)} ${step2.overflow > 1 ? '❌ 溢出' : '✅'} path=${step2.path} token=${step2.hasToken ? '✅' : '❌'} | ${step2.bodyText.replace(/\\n/g, ' ')}`)
if (!step2.hasToken) { console.error('   FAIL: 重置页没有 token 参数'); ws.close(); chrome.kill(); process.exit(1) }

// 5) 填新密码并提交
const pwInputs = await evalJs(`document.querySelectorAll('input[type="password"]').length`)
if (pwInputs !== 2) console.error(`   ⚠️ 密码输入框数量异常: ${pwInputs}`)
await setInput('input[type="password"]', NEW_PASSWORD, 0)
await setInput('input[type="password"]', NEW_PASSWORD, 1)
await evalJs(`document.querySelector('button[type="submit"]').click()`)
await sleep(2500)
const step3 = JSON.parse(await evalJs(`JSON.stringify({
  overflow: document.documentElement.scrollWidth - window.innerWidth,
  bodyText: document.body.innerText.slice(0, 150)
})`))
const shot3 = await send('Page.captureScreenshot', { format: 'png' })
writeFileSync(path.join(SHOT_DIR, 'pwreset-3-reset-done.png'), Buffer.from(shot3.data, 'base64'))
const step3ok = step3.bodyText.includes('密码已重置')
console.log(`${'reset-done'.padEnd(16)} ${step3.overflow > 1 ? '❌ 溢出' : '✅'} overflow=${step3.overflow} | 重置成功卡片: ${step3ok ? '✅' : '❌'}`)
if (!step3ok) { console.error('   FAIL: 未显示"密码已重置"'); console.error('   body:', step3.bodyText); ws.close(); chrome.kill(); process.exit(1) }

// 6) 用新密码登录验证
await evalJs(`[...document.querySelectorAll('button')].find(b => b.innerText.includes('去登录')).click()`)
await sleep(2000)
await setInput('input[type="text"]', TEST_USER.username)
await setInput('input[type="password"]', NEW_PASSWORD)
await evalJs(`document.querySelector('button[type="submit"]').click()`)
await sleep(3000)
const step4 = JSON.parse(await evalJs(`JSON.stringify({ path: location.pathname, loggedIn: !location.pathname.includes('login') })`))
console.log(`login-with-new-pw: ${step4.loggedIn ? '✅ 新密码登录成功' : '❌ 登录失败'} (path=${step4.path})`)

ws.close()
chrome.kill()
console.log('\n全部验证通过，截图已保存 frontend/scripts/pwreset-*.png')
process.exit(step4.loggedIn ? 0 : 1)
