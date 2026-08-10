import { useAuthStore } from '../store/authStore'

export default function Settings() {
  const { user } = useAuthStore()

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
    </div>
  )
}
