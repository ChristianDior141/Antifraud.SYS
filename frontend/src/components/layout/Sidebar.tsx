import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { cn } from '@/utils/cn';
import { logout } from '@/store/slices/authSlice';
import type { RootState } from '@/store';
import {
  LayoutDashboard, Users, FileText, AlertTriangle,
  BarChart3, Settings, LogOut, Shield, CreditCard, ClipboardCheck,
  Ticket, Sliders, Activity,
} from 'lucide-react';

const navItems = {
  client: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/profile', label: 'My Profile', icon: Users },
    { to: '/kyc', label: 'KYC Form', icon: FileText },
    { to: '/documents', label: 'Documents', icon: ClipboardCheck },
    { to: '/transactions', label: 'Transactions', icon: CreditCard },
  ],
  compliance_officer: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/clients', label: 'Clients', icon: Users },
    { to: '/reviews', label: 'Reviews', icon: ClipboardCheck },
    { to: '/aml', label: 'AML Alerts', icon: AlertTriangle },
    { to: '/incidents', label: 'Incidents', icon: Ticket },
    { to: '/rules', label: 'Rule Tuning', icon: Sliders },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/incident-analytics', label: 'Incident Analytics', icon: Activity },
  ],
  risk_analyst: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/clients', label: 'Clients', icon: Users },
    { to: '/aml', label: 'AML Monitoring', icon: AlertTriangle },
    { to: '/incidents', label: 'Incidents', icon: Ticket },
    { to: '/rules', label: 'Rule Tuning', icon: Sliders },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/incident-analytics', label: 'Incident Analytics', icon: Activity },
  ],
  admin: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/clients', label: 'Clients', icon: Users },
    { to: '/aml', label: 'AML Alerts', icon: AlertTriangle },
    { to: '/incidents', label: 'Incidents', icon: Ticket },
    { to: '/rules', label: 'Rule Tuning', icon: Sliders },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/incident-analytics', label: 'Incident Analytics', icon: Activity },
    { to: '/admin', label: 'Admin Panel', icon: Settings },
  ],
};

export function Sidebar() {
  const { user } = useSelector((s: RootState) => s.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const role = user?.role ?? 'client';
  const items = navItems[role as keyof typeof navItems] ?? navItems.client;

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-white">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white">
          <Shield className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold text-gray-900">KYC/AML</p>
          <p className="text-xs text-gray-500">Risk Platform</p>
        </div>
      </div>

      {/* User Info */}
      <div className="border-b px-6 py-4">
        <p className="truncate text-sm font-medium text-gray-900">{user?.full_name}</p>
        <p className="mt-0.5 truncate text-xs text-gray-500 capitalize">
          {role.replace(/_/g, ' ')}
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {items.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  )
                }
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Logout */}
      <div className="border-t p-3">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-red-50 hover:text-red-600"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
