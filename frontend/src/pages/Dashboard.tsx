export default function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">仪表盘</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardCard
          title="路线总数"
          value="0"
          icon="🗺️"
          color="bg-blue-50 text-blue-700"
        />
        <DashboardCard
          title="徒步记录"
          value="0"
          icon="📝"
          color="bg-green-50 text-green-700"
        />
        <DashboardCard
          title="装备数量"
          value="0"
          icon="🎒"
          color="bg-amber-50 text-amber-700"
        />
        <DashboardCard
          title="规划方案"
          value="0"
          icon="📋"
          color="bg-purple-50 text-purple-700"
        />
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 最近的规划 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">最近的规划</h3>
          <div className="text-center py-8 text-gray-400">
            <FootprintsIcon />
            <p className="mt-2">还没有规划，点击"新建规划"开始吧</p>
          </div>
        </div>

        {/* 即将到来的徒步 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">即将到来</h3>
          <div className="text-center py-8 text-gray-400">
            <CalendarIcon />
            <p className="mt-2">暂无安排的徒步计划</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function DashboardCard({ title, value, icon, color }: {
  title: string; value: string; icon: string; color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center text-2xl`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function FootprintsIcon() {
  return (
    <svg className="w-12 h-12 mx-auto opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 6l2-2l2 2l-2 2l-2-2zM7 18l-1 1l-2-1l1-2l2 2zm6-8l3 4l-2 1l-3-4l2-1zm-6 4l2 3l-1 1l-2-3l1-1z" />
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg className="w-12 h-12 mx-auto opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}
