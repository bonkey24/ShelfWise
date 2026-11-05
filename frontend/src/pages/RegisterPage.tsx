import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Logo } from '../components/Logo';
import { useAuth } from '../auth/AuthContext';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, register } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(email, password, name || undefined);
      navigate('/');
    } catch (err: any) {
      const data = err.response?.data;
      const msg =
        data?.detail ||
        data?.email?.[0] ||
        data?.password?.[0] ||
        (Array.isArray(data) ? data.join(' ') : null) ||
        'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen flex flex-col lg:flex-row bg-slate-50 text-slate-900">
      {/* LEFT: Brand Panel */}
      <section className="lg:w-1/2 w-full bg-gradient-to-br from-[#1E40AF] via-blue-600 to-[#1d4ed8] text-white flex flex-col justify-center items-center p-8 xl:p-14 relative overflow-hidden shrink-0">
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25px 25px, rgba(255,255,255,0.4) 2px, transparent 0)',
            backgroundSize: '32px 32px',
          }}
        />
        <div className="relative z-10 text-center space-y-6 max-w-md">
          <Logo variant="white" size="xl" />
          <h1 className="text-3xl font-bold leading-tight tracking-tight">
            Know what to stock, before the shelf runs empty.
          </h1>
          <p className="text-white/80 text-base leading-relaxed">
            Predictive retail AI built for boutique operators and multi-location managers.
          </p>
        </div>
      </section>

      {/* RIGHT: Register Form */}
      <section className="lg:w-1/2 w-full flex flex-col justify-center items-center p-6 md:p-12 xl:p-16 overflow-y-auto">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm">
            <div className="mb-6">
              <Logo variant="dark" size="md" className="mb-4" />
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
                Create your account
              </h2>
              <p className="text-sm text-slate-500">
                Get started with ShelfWise retail intelligence.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Doe"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1.5">
                  Email
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
                  placeholder="Min. 8 characters"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full h-11 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer shadow-sm group"
              >
                <span>{loading ? 'Creating account...' : 'Create account'}</span>
                {!loading && (
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                )}
              </button>
            </form>

            <div className="mt-5 pt-5 border-t border-slate-200 text-center">
              <p className="text-sm text-slate-500">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-semibold text-blue-600 hover:text-blue-700 hover:underline ml-1"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default RegisterPage;

