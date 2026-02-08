'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import NavBar from '@/components/NavBar';
import Footer from '@/components/Footer';
import { API_BASE_URL } from '@/lib/config';

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');

  useEffect(() => {
    const verify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Missing verification token.');
        return;
      }
      try {
        const res = await fetch(`${API_BASE_URL}/user/verify-email?token=${encodeURIComponent(token)}`);
        const data = await res.json();
        if (res.ok) {
          setStatus('success');
          setMessage(data?.data?.message || 'Email verified. You can now log in.');
        } else {
          setStatus('error');
          setMessage(data?.detail || data?.data?.message || 'Verification failed.');
        }
      } catch (err) {
        setStatus('error');
        setMessage('Verification failed. Please try again.');
      }
    };

    verify();
  }, [token]);

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-32 pb-20 px-6">
        <div className="max-w-2xl mx-auto text-center glass-dark p-10 rounded-3xl border border-white/10">
          <h1 className="text-3xl font-bold text-white mb-4">Email Verification</h1>
          <p className="text-white/70 mb-6">{message}</p>
          {status === 'success' && (
            <Link
              href="/login"
              className="inline-flex items-center px-6 py-3 rounded-full bg-white text-black hover:bg-white/90 transition-colors"
            >
              Go to Login
            </Link>
          )}
          {status === 'error' && (
            <Link
              href="/contact"
              className="inline-flex items-center px-6 py-3 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            >
              Contact Support
            </Link>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
