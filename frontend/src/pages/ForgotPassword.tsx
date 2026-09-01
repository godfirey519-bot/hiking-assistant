import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { Footprints } from 'lucide-react'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ message: string; reset_token?: string | null } | null>(null)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/forgot-password', { email })
      setResult(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '发送失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Footprints className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">徒步助手</h1>
          <p className="text-gray-500 mt-1">重置你的密码</p>
        </div>

        {!result ? (
          <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">忘记密码</h2>

            {error && (
              <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-lg">{error}</div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">注册邮箱</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                placeholder="you@example.com"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50"
            >
              {loading ? '发送中...' : '获取重置凭证'}
            </button>

            <p className="text-center text-sm text-gray-500">
              想起密码了？<Link to="/login" className="text-primary hover:underline">返回登录</Link>
            </p>
          </form>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">凭证已生成</h2>
            <p className="text-sm text-gray-600">{result.message}</p>

            {result.reset_token ? (
              <>
                <button
                  onClick={() => navigate(`/reset-password?token=${encodeURIComponent(result.reset_token!)}`)}
                  className="w-full py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
                >
                  前往设置新密码 →
                </button>
                <p className="text-xs text-gray-400 text-center">
                  开发模式：重置凭证直接展示，生产环境会通过邮件发送
                </p>
              </>
            ) : (
              <p className="text-sm text-gray-500">请前往注册邮箱点击重置链接</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
