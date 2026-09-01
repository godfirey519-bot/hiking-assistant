import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import api from '../services/api'

export default function Settings() {
  const { user } = useAuthStore()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwdMsg, setPwdMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [pwdLoading, setPwdLoading] = useState(false)

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwdMsg(null)
    if (newPassword !== confirmPassword) {
      setPwdMsg({ type: 'error', text: '两次输入的新密码不一致' })
      return
    }
    if (newPassword.length < 6) {
      setPwdMsg({ type: 'error', text: '新密码长度不能少于 6 位' })
      return
    }
    setPwdLoading(true)
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setPwdMsg({ type: 'success', text: '密码修改成功' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setPwdMsg({ type: 'error', text: err.response?.data?.detail || '修改失败，请重试' })
    } finally {
      setPwdLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">设置</h2>
      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-2xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">个人资料</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              type="text"
              defaultValue={user?.username}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50"
              disabled
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              type="email"
              defaultValue={user?.email}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg bg-gray-50"
              disabled
            />
          </div>
        </div>

        <hr className="my-6" />

        <h3 className="text-lg font-semibold text-gray-900 mb-4">API 配置</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">LLM API Key</label>
            <input
              type="password"
              placeholder="sk-..."
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <p className="text-xs text-gray-500 mt-1">用于驱动 AI Agent 的 API Key（Claude 或 OpenAI）</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">搜索 API Key</label>
            <input
              type="password"
              placeholder="tvly-..."
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <p className="text-xs text-gray-500 mt-1">Tavily Search API Key，用于 Agent 联网搜索装备信息</p>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-gray-100">
          <button className="px-4 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors">
            保存设置
          </button>
        </div>
      </div>

      <form onSubmit={handleChangePassword} className="bg-white rounded-xl border border-gray-200 p-6 max-w-2xl mt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">修改密码</h3>

        {pwdMsg && (
          <div className={`text-sm px-4 py-3 rounded-lg mb-4 ${
            pwdMsg.type === 'success' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
          }`}>
            {pwdMsg.text}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">新密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="至少 6 位"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              required
            />
          </div>
        </div>

        <div className="mt-6">
          <button
            type="submit"
            disabled={pwdLoading}
            className="px-4 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors disabled:opacity-50"
          >
            {pwdLoading ? '提交中...' : '确认修改'}
          </button>
        </div>
      </form>
    </div>
  )
}
