import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles, User, Bot, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import PlanResult from './PlanResult'
import { mapPlanToResult } from '../../utils/planMapper'
import { shouldPlan } from '../../utils/planIntent'
import api from '../../services/api'

const PLAN_LOADING = '正在规划...'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  plan?: any
}

const CHAT_STORAGE_KEY = 'hiking-chat-messages'

function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveMessages(msgs: Message[]) {
  try {
    // Only persist the last 20 messages to avoid bloat
    const trimmed = msgs.slice(-20)
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(trimmed))
  } catch { /* quota exceeded, ignore */ }
}

export default function AgentChat({ initialInput = '' }: { initialInput?: string }) {
  const [input, setInput] = useState(initialInput)
  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 当 initialInput 变化时更新（从路线页跳转过来）
  useEffect(() => {
    if (initialInput) setInput(initialInput)
  }, [initialInput])

  // Persist messages to localStorage
  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  const pollForResult = async (pid: number, msgId: string) => {
    // Poll the plan endpoint every 2 seconds until completed
    for (let i = 0; i < 60; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      try {
        const res = await api.get(`/plans/${pid}`)
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          setLoading(false)
          if (res.data.sections?.length > 0) {
            buildFinalPlan(res.data, msgId)
          }
          return
        }
      } catch { /* retry */ }
    }
    // Timeout after 2 minutes
    setLoading(false)
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, content: '规划超时，请重试' } : m
    ))
  }

  const buildFinalPlan = (data: any, msgId: string) => {
    const plan = mapPlanToResult(data)
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, plan } : m
    ))
  }

  // 通用对话：AI 直接回答任意问题（带徒步引导）
  const sendGeneralChat = async (userInput: string, msgId: string) => {
    // 用当前（尚未加入本轮）的历史消息构建上下文
    const history = messages
      .filter(m => m.content && !m.plan && m.content !== PLAN_LOADING)
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await api.post('/chat', { message: userInput, history })
      const reply = res.data?.reply || '（抱歉，没有收到回复）'
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, content: reply } : m))
    } catch (err: any) {
      setMessages(prev => prev.map(m =>
        m.id === msgId ? { ...m, content: `❌ ${err.response?.data?.detail || '回复失败，请稍后重试'}` } : m
      ))
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userInput = input.trim()
    setInput('')
    const msgId = Date.now().toString()

    setMessages(prev => [...prev, { id: msgId, role: 'user', content: userInput }])

    // 明确表达规划意图（含天数或徒步上下文）→ 完整工作流；其余 → 通用对话
    if (shouldPlan(userInput)) {
      setMessages(prev => [...prev, { id: `a-${msgId}`, role: 'assistant', content: PLAN_LOADING }])
      setLoading(true)

      try {
        const planRes = await api.post('/plans/', { title: userInput.slice(0, 100), description: userInput })
        const pid = planRes.data.id
        await api.post(`/agents/start-planning/${pid}`)
        // Simple polling - no SSE complexity
        pollForResult(pid, `a-${msgId}`)
      } catch (err: any) {
        setLoading(false)
        setMessages(prev => prev.map(m =>
          m.id === `a-${msgId}` ? { ...m, content: `❌ ${err.response?.data?.detail || '规划失败'}` } : m
        ))
      }
    } else {
      setMessages(prev => [...prev, { id: `a-${msgId}`, role: 'assistant', content: '' }])
      setLoading(true)
      await sendGeneralChat(userInput, `a-${msgId}`)
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      {/* Clear button */}
      {messages.length > 0 && (
        <div className="flex justify-end mb-2">
          <button
            onClick={() => { setMessages([]); localStorage.removeItem(CHAT_STORAGE_KEY) }}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 transition-colors px-2.5 py-2"
          >
            <Trash2 className="w-3 h-3" /> 清除对话
          </button>
        </div>
      )}

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto mb-4 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <Sparkles className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">AI 徒步规划助手</p>
            <p className="text-sm mt-1">我可以回答任何问题，也能帮你生成完整徒步方案</p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {[
                '国庆走武功山穿越线，2天1夜，帮我规划',
                '10月适合去哪里徒步？推荐几条路线',
                '雨崩3天徒步需要什么装备？',
                '新手第一次徒步要注意什么？',
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => setInput(hint)}
                  className="px-3 py-2 text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-primary" />
              </div>
            )}

            <div className={`max-w-[92%] sm:max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              {/* User message bubble */}
              {msg.role === 'user' && (
                <div className="bg-primary text-white px-4 py-2.5 rounded-2xl rounded-br-md text-sm break-words">
                  {msg.content}
                </div>
              )}

              {/* Assistant: loading (plan) */}
              {msg.role === 'assistant' && !msg.plan && msg.content === PLAN_LOADING && (
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-md">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>AI 正在分析路线、规划装备、评估安全...</span>
                  </div>
                </div>
              )}

              {/* Assistant: loading (general chat) */}
              {msg.role === 'assistant' && !msg.plan && msg.content === '' && (
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-md">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    <span>AI 正在思考...</span>
                  </div>
                </div>
              )}

              {/* Assistant: text reply (markdown) */}
              {msg.role === 'assistant' && !msg.plan && msg.content !== '' && msg.content !== PLAN_LOADING && (
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-md text-sm leading-relaxed text-gray-700">
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => <h3 className="font-bold text-gray-900 mt-2 mb-1">{children}</h3>,
                      h2: ({ children }) => <h3 className="font-bold text-gray-900 mt-2 mb-1">{children}</h3>,
                      h3: ({ children }) => <h4 className="font-semibold text-gray-900 mt-2 mb-1">{children}</h4>,
                      p: ({ children }) => <p className="my-1.5">{children}</p>,
                      ul: ({ children }) => <ul className="list-disc pl-5 my-1.5 space-y-0.5">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal pl-5 my-1.5 space-y-0.5">{children}</ol>,
                      li: ({ children }) => <li className="my-0.5">{children}</li>,
                      strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                      a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-primary underline">{children}</a>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}

              {/* Assistant: final plan */}
              {msg.role === 'assistant' && msg.plan && (
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md overflow-hidden">
                  <PlanResult plan={msg.plan} />
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-gray-500" />
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator (new message pending) */}
        {loading && messages.length === 0 && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-md">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                AI 正在规划...
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // 中文输入法组合中不发送（isComposing 判断）
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="描述你的徒步计划...&#10;例如：国庆走武功山穿越线，2天1夜，新手，需要装备推荐"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary text-sm"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="self-end px-4 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
