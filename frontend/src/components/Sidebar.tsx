import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  TrendingUp,
  Package,
  Bot,
  LogOut,
  X,
} from 'lucide-react';
import { Logo } from './Logo';
import { useAuth } from '../auth/AuthContext';

export interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onClose }) => {
  const { user, logout } = useAuth();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Upload', path: '/upload', icon: UploadCloud },
    { name: 'Forecast', path: '/forecast', icon: TrendingUp },
    { name: 'Inventory', path: '/inventory', icon: Package },
    { name: 'Assistant', path: '/assistant', icon: Bot },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 z-40 md:hidden transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-screen w-64 z-50 md:z-30 bg-white border-r border-slate-200 flex flex-col justify-between p-4 transition-transform duration-200 ${
          mobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex flex-col gap-6">
          {/* Brand & Mobile Close */}
          <div className="px-2 pt-2 flex items-center justify-between">
            <div className="flex flex-col">
              <Logo variant="dark" size="md" />
              <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase mt-1">
                Retail Intelligence
              </span>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="md:hidden p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors cursor-pointer"
                aria-label="Close navigation"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* User & Logout */}
        <div className="border-t border-slate-200 pt-3 flex items-center justify-between">
          <div className="truncate mr-2">
            <p className="text-xs font-semibold text-slate-800 truncate">
              {user?.name || user?.email || 'User'}
            </p>
            <p className="text-[11px] text-slate-500 truncate">
              {user?.email || ''}
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
