import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, TrendingUp, Bell, Bot } from 'lucide-react';
import { Logo } from '../components/Logo';
import { useAuth } from '../auth/AuthContext';
import { API_BASE_URL } from '../api/client';
import api from '../api/client';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // SSO
  const [ssoEnabled, setSsoEnabled] = useState(false);

  // If already logged in, redirect
  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  // Check SSO availability
  useEffect(() => {
    api
      .get<{ enabled: boolean }>('/auth/sso/config/')
      .then((res) => setSsoEnabled(res.data.enabled))
      .catch(() => setSsoEnabled(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.email?.[0] ||
        err.response?.data?.password?.[0] ||
        'Invalid email or password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemo = () => {
    setEmail('demo@shelfwise.app');
    setPassword('Demo@12345');
    setError(null);
  };

  const ssoUrl = `${API_BASE_URL.replace(/\/api$/, '')}/api/auth/sso/login/`;

  return (
    <div className="w-full min-h-screen flex flex-col lg:flex-row bg-slate-50 text-slate-900">
      {/* LEFT: Brand Showcase Panel */}
      <section className="lg:w-1/2 w-full bg-gradient-to-br from-[#1E40AF] via-blue-600 to-[#1d4ed8] text-white flex flex-col justify-between p-8 xl:p-14 relative overflow-hidden shrink-0">
        {/* Decorative background */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25px 25px, rgba(255,255,255,0.4) 2px, transparent 0)',
            backgroundSize: '32px 32px',
          }}
        />
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-white opacity-10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-blue-300 opacity-20 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col h-full justify-between gap-8">
          {/* Header */}
          <div className="flex items-center gap-3">
            <Logo variant="white" size="lg" />
            <span className="px-2.5 py-1 rounded-full bg-white/15 backdrop-blur-sm border border-white/25 text-xs font-medium tracking-wide">
              Retail Intelligence
            </span>
          </div>

          {/* Value Proposition */}
          <div className="space-y-8 my-auto py-4">
            <div className="space-y-3 max-w-xl">
              <h1 className="text-3xl xl:text-[32px] font-bold leading-tight tracking-tight">
                Know what to stock, before the shelf runs empty.
              </h1>
              <p className="text-white/80 text-base leading-relaxed max-w-lg">
                Predictive retail AI built for boutique operators and multi-location
                managers. Seamless forecasting without legacy ERP drag.
              </p>
            </div>

            {/* Feature Cards */}
            <div className="space-y-3 max-w-lg">
              <div className="flex items-start gap-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/15">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center shrink-0">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold">28-day demand forecasts</h2>
                  <p className="text-xs text-white/80 mt-0.5">
                    Anticipate customer surge events and seasonal trends with high accuracy.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/15">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center shrink-0">
                  <Bell className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold">Reorder alerts</h2>
                  <p className="text-xs text-white/80 mt-0.5">
                    Automated lead-time triggers before critical SKUs drop below safety thresholds.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/15">
                <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold">AI assistant</h2>
                  <p className="text-xs text-white/80 mt-0.5">
                    Natural language inventory queries and grounded reorder recommendations.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="text-xs text-white/60">
            ShelfWise Demand Forecasting Platform
          </div>
        </div>
      </section>

      {/* RIGHT: Auth Form */}
      <section className="lg:w-1/2 w-full bg-slate-50 flex flex-col justify-between items-center p-6 md:p-12 xl:p-16 overflow-y-auto">
        {/* Mobile brand (lg:hidden) */}
        <div className="lg:hidden w-full flex items-center justify-between pb-6 mb-2 border-b border-slate-200">
          <Logo variant="dark" size="md" />
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-blue-600 font-medium">
            Retail Intelligence
          </span>
        </div>

        <div className="w-full max-w-md my-auto py-4">
          <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm">
            {/* Header */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
                Welcome back
              </h2>
              <p className="text-sm text-slate-500">
                Enter your details to access your ShelfWise store intelligence.
              </p>
            </div>

            {/* Google SSO */}
            {ssoEnabled && (
              <>
                <a
                  href={ssoUrl}
                  className="w-full h-11 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-900 text-sm font-medium flex items-center justify-center gap-3 transition-colors"
                >
                  <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
                  </svg>
                  <span>Sign in with Google</span>
                </a>

                {/* Divider */}
                <div className="relative my-6 flex items-center justify-center">
                  <div className="w-full border-t border-slate-200" />
                  <span className="absolute px-3 bg-white text-slate-400 text-xs uppercase tracking-wider">
                    or sign in with email
                  </span>
                </div>
              </>
            )}

            {/* Error */}
            {error && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                {error}
              </div>
            )}

            {/* Credentials Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">
                  Store Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@store.com"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full h-11 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer shadow-sm group"
              >
                <span>{loading ? 'Signing in...' : 'Sign in to Dashboard'}</span>
                {!loading && (
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                )}
              </button>
            </form>

            {/* Demo account quick-fill */}
            {import.meta.env.VITE_SHOW_DEMO_LOGIN === 'true' && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleFillDemo}
                  className="w-full py-2 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer flex-wrap text-center"
                >
                  <span>Use demo account:</span>
                  <span className="font-semibold text-blue-600">demo@shelfwise.app</span>
                </button>
              </div>
            )}

            {/* Register link */}
            <div className="mt-5 pt-5 border-t border-slate-200 text-center">
              <p className="text-sm text-slate-500">
                Don't have an account?{' '}
                <Link
                  to="/register"
                  className="font-semibold text-blue-600 hover:text-blue-700 hover:underline ml-1"
                >
                  Create an account
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="w-full text-center py-3">
          <p className="text-[11px] text-slate-400">
            ShelfWise Demand Forecasting Platform
          </p>
        </footer>
      </section>
    </div>
  );
};

export default LoginPage;
