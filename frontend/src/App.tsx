import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import PlanNew from './pages/PlanNew'
import PlanDetail from './pages/PlanDetail'
import PlanHistory from './pages/PlanHistory'
import SharePage from './pages/SharePage'
import Equipment from './pages/Equipment'
import Backpacks from './pages/Backpacks'
import RoutesPage from './pages/RoutesPage'
import RouteDetail from './pages/RouteDetail'
import TripRecords from './pages/TripRecords'
import TripDetail from './pages/TripDetail'
import Settings from './pages/Settings'

function App() {
  const { token } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to="/" /> : <Login />} />
      <Route path="/register" element={token ? <Navigate to="/" /> : <Register />} />
      <Route path="/forgot-password" element={token ? <Navigate to="/" /> : <ForgotPassword />} />
      <Route path="/reset-password" element={token ? <Navigate to="/" /> : <ResetPassword />} />
      {/* 公开分享页（免登录只读） */}
      <Route path="/share/plans/:token" element={<SharePage />} />
      <Route path="/" element={token ? <MainLayout /> : <Navigate to="/login" />}>
        <Route index element={<Dashboard />} />
        <Route path="plans/new" element={<PlanNew />} />
        <Route path="plans/:id" element={<PlanDetail />} />
        <Route path="plans" element={<PlanHistory />} />
        <Route path="equipment" element={<Equipment />} />
        <Route path="backpacks" element={<Backpacks />} />
        <Route path="routes" element={<RoutesPage />} />
        <Route path="routes/:id" element={<RouteDetail />} />
        <Route path="trips" element={<TripRecords />} />
        <Route path="trips/:id" element={<TripDetail />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
