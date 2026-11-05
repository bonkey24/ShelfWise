import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { LogOut, Menu } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { useAuth } from '../auth/AuthContext';

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/upload': 'Upload',
  '/forecast': 'Forecast',
  '/inventory': 'Inventory',
  '/assistant': 'ShelfWise Assistant',
};

export const Layout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const pageTitle = pageTitles[location.pathname] || 'ShelfWise';
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Persistent Left Sidebar on Desktop, Drawer on Mobile */}
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      {/* Main Content Area */}
      <div className="md:ml-64 flex-1 flex flex-col min-h-screen w-full">
        {/* Top Bar */}
        <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-200 px-4 sm:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-1.5 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-base sm:text-lg font-semibold text-slate-900 tracking-tight">
              {pageTitle}
            </h1>
          </div>
          <div className="flex items-center gap-3 sm:gap-4">
            <span className="text-xs text-slate-500 truncate max-w-[120px] sm:max-w-none">
              {user?.email}
            </span>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-600 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 sm:p-8 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
