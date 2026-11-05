import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setTokens } from '../api/client';
import api from '../api/client';
import { useAuth } from '../auth/AuthContext';

/**
 * Handles the SSO redirect callback.
 * Reads access and refresh tokens from the URL hash fragment (#access=...&refresh=...),
 * stores them, fetches the user profile, cleans the URL, and redirects to /.
 */
export const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [statusText, setStatusText] = useState('Completing authentication...');

  useEffect(() => {
    const hash = window.location.hash.startsWith('#')
      ? window.location.hash.substring(1)
      : window.location.hash;

    const params = new URLSearchParams(hash);
    const access = params.get('access');
    const refresh = params.get('refresh');

    if (access) {
      setTokens(access, refresh || undefined);

      // Clean the URL hash
      window.history.replaceState(null, '', window.location.pathname);

      api
        .get('/auth/me/')
        .then((res) => {
          setUser(res.data);
          navigate('/', { replace: true });
        })
        .catch(() => {
          navigate('/', { replace: true });
        });
    } else {
      setStatusText('Authentication failed. Redirecting to login...');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1500);
    }
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm max-w-sm w-full text-center space-y-3">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-600 font-medium">{statusText}</p>
      </div>
    </div>
  );
};

export default AuthCallbackPage;
