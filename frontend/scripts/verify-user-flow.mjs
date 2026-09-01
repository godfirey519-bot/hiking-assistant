// P3-1 预自测 E2E：以"真实用户"视角覆盖测试清单剩余环节
// 覆盖: 注册(UI) → 设置改密 → 路线搜索/对比 → GPX上传 → 背包创建 → 记录媒体上传
// 用法: node scripts/verify-user-flow.mjs（需前后端已启动）
import { spawn } from 'child_process'
import { mkdtempSync, writeFileSync } from 'fs'
import { tmpdir } from 'os'
import path from 'path'

const PORT = 9230
const BASE = 'http://localhost:5173'
const SHOT_DIR = 'D:/徒步助手/frontend/scripts'
const UNIQ = Date.now().toString(36).slice(-6)
const USER = { username: `uitest_${UNIQ}`, email: `uitest_${UNIQ}@test.com`, password: 'uitest123' }
const NEW_PW = 'uitest456'

// 准备测试文件
const gpxPath = path.join(tmpdir(), `uitest-${UNIQ}.gpx`)
writeFileSync(gpxPath, `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>UI Test Trail</name><trkseg>
    <trkpt lat="30.28" lon="114.15"><ele>50</ele></trkpt>
    <trkpt lat="30.29" lon="114.16"><ele>120</ele></trkpt>
    <trkpt lat="30.30" lon="114.17"><ele>200</ele></trkpt>
    <trkpt lat="30.28" lon="114.15"><ele>50</ele></trkpt>
  </trkseg></trk></gpx>`)
const pngPath = path.join(tmpdir(), `uitest-${UNIQ}.png`)
// 1x1 PNG
writeFileSync(pngPath, Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64'))

// 启动 Chrome
const userData = mkdtempSync(path.join(tmpdir(), 'chrome-uitest-'))
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
if (!wsUrl) { console.error('FAIL: no CDP'); chrome.kill(); process.exit(1) }

const ws = new WebSocket(wsUrl)
let msgId = 0
const pending = new Map()
// CDP 调用带超时：防止某一步卡死导致整个脚本挂起
const send = (method, params = {}) => new Promise((resolve) => {
  const id = ++msgId
  const timer = setTimeout(() => {
    pending.delete(id)
    resolve({ error: `CDP timeout: ${method}` })
  }, 15000)
  pending.set(id, (result) => {
    clearTimeout(timer)
    resolve(result)
  })
  try {
    ws.send(JSON.stringify({ id, method, params }))
  } catch {
    clearTimeout(timer)
    pending.delete(id)
    resolve({ error: `CDP send failed: ${method}` })
  }
})
const consoleErrors = []
ws.onmessage = (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id) }
  if (m.method === 'Runtime.exceptionThrown') consoleErrors.push(m.params.exceptionDetails?.exception?.description || 'exception')
}
// WebSocket 断开时把挂起的调用全部 resolve，避免永久等待
ws.onclose = () => {
  for (const [id, fn] of pending) { fn({ error: 'CDP closed' }); pending.delete(id) }
}
await new Promise(r => ws.onopen = r)
await send('Page.enable')
await send('Runtime.enable')
await send('DOM.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }))?.result?.value
const sleep = ms => new Promise(r => setTimeout(r, ms))
const setInput = (sel, value, index) => evalJs(`(() => {
  const list = document.querySelectorAll(${JSON.stringify(sel)})
  const el = ${typeof index === 'number' ? `list[${index}]` : `list[0]`}
  if (!el) return false
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set
  setter.call(el, ${JSON.stringify(value)})
  el.dispatchEvent(new Event('input', { bubbles: true }))
  return true
})()`)
const clickText = (text) => evalJs(`(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.innerText.includes(${JSON.stringify(text)}))
  if (!b) return false
  b.click(); return true
})()`)
const setFile = async (selector, filePath) => {
  const { root } = await send('DOM.getDocument')
  const q = await send('DOM.querySelector', { nodeId: root.nodeId, selector })
  if (!q.nodeId) return false
  await send('DOM.setFileInputFiles', { nodeId: q.nodeId, files: [filePath] })
  return true
}
const audit = async (label) => {
  let m = { overflow: 99, path: '?' }
  try {
    const raw = await evalJs(`JSON.stringify({ overflow: document.documentElement.scrollWidth - window.innerWidth, path: location.pathname })`)
    if (raw) m = JSON.parse(raw)
  } catch { /* 页面异常时降级 */ }
  const ok = m.overflow <= 1
  console.log(`${label.padEnd(22)} ${ok ? '✅' : '❌ 溢出'} path=${m.path}`)
  try {
    const s = await send('Page.captureScreenshot', { format: 'png' })
    if (s.data) writeFileSync(path.join(SHOT_DIR, `uitest-${label}.png`), Buffer.from(s.data, 'base64'))
  } catch { /* 截图失败不影响结果 */ }
  return ok
}

let failed = 0
const check = (cond, label, extra = '') => {
  console.log(`   ${cond ? '✅' : '❌'} ${label}${extra ? ' | ' + extra : ''}`)
  if (!cond) failed++
}

// ===== 1. 注册（UI 全流程）→ 自动登录 =====
await send('Page.navigate', { url: `${BASE}/register` }); await sleep(3000)
const regPageOk = await evalJs(`location.pathname === '/register' && !!document.querySelector('form')`)
check(regPageOk, '注册页正常渲染')
await setInput('input[type="text"]', USER.username)
await setInput('input[type="email"]', USER.email)
await setInput('input[type="password"]', USER.password)
const regClicked = await clickText('注册')
check(regClicked, '点击注册按钮')
await sleep(3500)
const regPath = await evalJs('location.pathname')
check(regPath === '/', '注册成功并自动登录', regPath)
if (regPath !== '/') {
  const err = await evalJs(`document.body.innerText.slice(0, 200)`)
  console.log('   注册页状态:', err.replace(/\n+/g, ' ').slice(0, 150))
}
await audit('1-register')

// ===== 2. 设置页修改密码 =====
// 注意: Settings 页有 5 个密码输入框（LLM Key/搜索 Key 在 API 配置区），
// 修改密码表单内的 3 个用 form 限定范围: 0=当前 1=新 2=确认
await send('Page.navigate', { url: `${BASE}/settings` }); await sleep(3000)
await setInput('form input[type="password"]', USER.password, 0)   // 当前密码
await setInput('form input[type="password"]', NEW_PW, 1)          // 新密码
await setInput('form input[type="password"]', NEW_PW, 2)          // 确认
await clickText('确认修改'); await sleep(2500)
const pwdOk = await evalJs(`document.body.innerText.includes('密码修改成功')`)
check(pwdOk, '设置页修改密码成功')
if (!pwdOk) {
  const msg = await evalJs(`[...document.querySelectorAll('form')].find(f => f.innerText.includes('修改密码'))?.innerText.slice(0, 200)`)
  console.log('   表单状态:', msg?.replace(/\n+/g, ' '))
}
await audit('2-change-password')

// 退出 → 新密码登录
await evalJs(`document.querySelector('button[title="退出登录"]').click()`); await sleep(2000)
await send('Page.navigate', { url: `${BASE}/login` }); await sleep(2000)
await setInput('input[type="text"]', USER.username)
await setInput('input[type="password"]', NEW_PW)
await clickText('登录'); await sleep(3000)
const loginOk = await evalJs(`location.pathname === '/'`)
check(loginOk, '新密码登录成功')

// ===== 3. 路线搜索 + 对比 =====
await send('Page.navigate', { url: `${BASE}/routes` }); await sleep(3500)
await setInput('input[placeholder*="搜索路线"]', '武功')
await sleep(1500)
const searchOk = await evalJs(`document.body.innerText.includes('武功山')`)
check(searchOk, '路线搜索命中「武功山」')
// 加入对比（前两个卡片）
await evalJs(`(() => {
  const btns = [...document.querySelectorAll('button')].filter(b => (b.title === '加入对比' || b.title === '取消对比')).slice(0, 2)
  btns.forEach(b => b.click())
  return btns.length
})()`)
await sleep(1500)
await clickText('开始对比'); await sleep(2500)
const cmpOk = await evalJs(`document.body.innerText.includes('对比') && document.body.innerText.includes('距离')`)
check(cmpOk, '路线对比弹窗展示')
await audit('3-routes-compare')

// ===== 4. GPX 上传（UI） =====
await send('Page.navigate', { url: `${BASE}/routes` }); await sleep(2500)
const uploaded = await setFile('input[type="file"]', gpxPath)
await sleep(4000)
const gpxOk = await evalJs(`document.body.innerText.includes('导入成功')`)
check(uploaded && gpxOk, 'GPX 上传并出现新路线')
if (!gpxOk) {
  console.log('   上传区文案:', (await evalJs(`[...document.querySelectorAll('div')].find(d => d.innerText.includes('GPX'))?.innerText.slice(0, 120)`))?.replace(/\n+/g, ' '))
}
await audit('4-gpx-upload')

// ===== 5. 背包方案 UI 创建 =====
await send('Page.navigate', { url: `${BASE}/backpacks` }); await sleep(2500)
await clickText('新建方案'); await sleep(1500)
await setInput('input[placeholder*="方案名称"]', '自测背包')
await clickText('创建'); await sleep(2500)
const bpOk = await evalJs(`document.body.innerText.includes('自测背包')`)
check(bpOk, '自定义背包方案创建成功')
await audit('5-backpack-create')

// ===== 6. 徒步记录 + 媒体上传 =====
await send('Page.navigate', { url: `${BASE}/trips` }); await sleep(2500)
await clickText('记录'); await sleep(1500)
await setInput('input[placeholder*="武功山金顶"]', '自测徒步记录')
await setInput('input[type="number"]', '12.5', 0)
await setInput('input[type="number"]', '900', 1)
await clickText('保存记录'); await sleep(3000)
const tripOk = await evalJs(`document.body.innerText.includes('自测徒步记录')`)
check(tripOk, '徒步记录创建成功')
// 打开详情并上传照片（带超时保护）
const navClicked = await evalJs(`(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.innerText.includes('自测徒步记录'))
  if (!b) return false
  b.click(); return true
})()`)
await sleep(3000)
const detailPath = await evalJs(`location.pathname`)
check(navClicked && detailPath.startsWith('/trips/'), '进入记录详情页', detailPath)
await audit('6a-trip-detail')
const mediaUploaded = await Promise.race([
  setFile('input[type="file"]', pngPath),
  sleep(8000).then(() => 'timeout'),
])
check(mediaUploaded === true, '媒体文件已注入上传框')
await sleep(3500)
const mediaOk = await evalJs(`document.querySelectorAll('img').length > 1 || document.body.innerText.includes('照片')`)
check(mediaOk, '记录媒体上传成功')
await audit('6-trip-media')

// console 错误汇总
if (consoleErrors.length) {
  console.log(`\n⚠️ 页面 JS 异常 ${consoleErrors.length} 条:`)
  consoleErrors.slice(0, 5).forEach(e => console.log('   -', String(e).slice(0, 150)))
  failed += consoleErrors.length > 2 ? 1 : 0
}

ws.close(); chrome.kill()
console.log(`\n${failed === 0 ? '🎉 全部自测通过，截图已存 frontend/scripts/uitest-*.png' : `❌ ${failed} 项失败`}`)
process.exit(failed === 0 ? 0 : 1)
