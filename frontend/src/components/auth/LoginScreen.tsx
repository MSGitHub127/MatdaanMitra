'use client';

import { useState } from 'react';
import { signInWithGoogle, ensureAuth } from '../../lib/firebase';

interface LoginScreenProps {
    onAuthenticated: (uid: string, isAnonymous: boolean) => void;
}

export default function LoginScreen({ onAuthenticated }: LoginScreenProps) {
    const [googleLoading, setGoogleLoading] = useState(false);
    const [anonLoading, setAnonLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleGoogle = async () => {
        setGoogleLoading(true);
        setError(null);
        try {
            const uid = await signInWithGoogle();
            onAuthenticated(uid, false);
        } catch (err: unknown) {
            const code = (err as { code?: string })?.code;
            if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
                // User dismissed — not an error
            } else {
                setError('Sign-in failed. Please try again or continue without an account.');
            }
        } finally {
            setGoogleLoading(false);
        }
    };

    const handleAnonymous = async () => {
        setAnonLoading(true);
        setError(null);
        try {
            const uid = await ensureAuth();
            onAuthenticated(uid, true);
        } catch {
            setError('Could not initialize session. Please check your connection.');
        } finally {
            setAnonLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
            fontFamily: 'Instrument Sans, system-ui, sans-serif',
        }}>

            {/* Background radial glow */}
            <div style={{
                position: 'fixed', inset: 0, pointerEvents: 'none',
                background: 'radial-gradient(ellipse at 50% 30%, rgba(249,115,22,0.06) 0%, transparent 65%)',
            }} />

            <div style={{
                width: '100%', maxWidth: 420, position: 'relative', zIndex: 1,
            }}>

                {/* Logo card */}
                <div style={{
                    background: 'var(--card)',
                    border: '1px solid var(--border)',
                    borderRadius: 20,
                    overflow: 'hidden',
                    boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
                }}>
                    {/* Tricolor strip */}
                    <div style={{
                        height: 4,
                        background: 'linear-gradient(to right, #FF9933 33.33%, #F0EDE6 33.33% 66.66%, #138808 66.66%)',
                    }} />

                    <div style={{ padding: '36px 32px 32px' }}>

                        {/* Logo mark */}
                        <div style={{ textAlign: 'center', marginBottom: 28 }}>
                            <div style={{
                                width: 64, height: 64, borderRadius: '50%',
                                background: 'conic-gradient(#FF9933 0deg 120deg, #F0EDE6 120deg 240deg, #138808 240deg 360deg)',
                                margin: '0 auto 14px',
                                boxShadow: '0 0 0 2px rgba(249,115,22,0.4), 0 0 28px rgba(249,115,22,0.18)',
                                position: 'relative',
                            }}>
                                <div style={{
                                    position: 'absolute', top: '50%', left: '50%',
                                    transform: 'translate(-50%,-50%)',
                                    width: 26, height: 26, borderRadius: '50%',
                                    background: '#00008B',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                }}>
                                    <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'rgba(255,255,255,0.9)' }} />
                                </div>
                            </div>

                            <h1 style={{
                                fontFamily: 'Fraunces, Georgia, serif',
                                fontSize: 28, fontWeight: 700, color: 'var(--saffron)',
                                margin: '0 0 4px', letterSpacing: '-0.02em',
                            }}>
                                मतदान मित्र
                            </h1>
                            <p style={{ fontSize: 11, color: 'var(--ink-ghost)', letterSpacing: '.16em' }}>
                                MATDAAN MITRA · ECI VERIFIED
                            </p>
                        </div>

                        {/* Tagline */}
                        <p style={{
                            textAlign: 'center', fontSize: 13.5,
                            color: 'var(--ink-dim)', lineHeight: 1.65,
                            marginBottom: 28,
                        }}>
                            Your intelligent, multilingual guide to<br />
                            voter registration and Indian elections.
                        </p>

                        {/* Error */}
                        {error && (
                            <div style={{
                                marginBottom: 16, padding: '10px 13px',
                                background: 'var(--rose-dim)',
                                border: '1px solid rgba(251,113,133,0.3)',
                                borderRadius: 10, fontSize: 12, color: 'var(--rose)',
                            }}>
                                {error}
                            </div>
                        )}

                        {/* Google Sign-In */}
                        <button
                            onClick={handleGoogle}
                            disabled={googleLoading || anonLoading}
                            style={{
                                all: 'unset', cursor: 'pointer',
                                width: '100%', padding: '13px',
                                background: '#fff', border: '1px solid #dadce0',
                                borderRadius: 12,
                                display: 'flex', alignItems: 'center',
                                justifyContent: 'center', gap: 10,
                                fontSize: 14, fontWeight: 600, color: '#3c4043',
                                transition: 'all .15s',
                                boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
                                marginBottom: 10,
                                opacity: (googleLoading || anonLoading) ? 0.6 : 1,
                            }}
                            onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.18)')}
                            onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.12)')}
                        >
                            {googleLoading ? (
                                <div style={{
                                    width: 18, height: 18, borderRadius: '50%',
                                    border: '2px solid #dadce0', borderTop: '2px solid #4285F4',
                                    animation: 'spin 0.8s linear infinite',
                                }} />
                            ) : (
                                // Google G logo SVG
                                <svg width="18" height="18" viewBox="0 0 18 18">
                                    <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z" />
                                    <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2.01c-.72.48-1.63.77-2.7.77-2.08 0-3.84-1.4-4.47-3.29H1.83v2.07A8 8 0 0 0 8.98 17z" />
                                    <path fill="#FBBC05" d="M4.51 10.53c-.16-.48-.25-.98-.25-1.53s.09-1.05.25-1.53V5.4H1.83A8 8 0 0 0 .98 9c0 1.29.31 2.51.85 3.6l2.68-2.07z" />
                                    <path fill="#EA4335" d="M8.98 3.58c1.17 0 2.23.4 3.06 1.2L14.5 2.3A8 8 0 0 0 8.98 1a8 8 0 0 0-7.15 4.4l2.68 2.07c.63-1.89 2.39-3.3 4.47-3.3z" />
                                </svg>
                            )}
                            {googleLoading ? 'Signing in…' : 'Continue with Google'}
                        </button>

                        {/* Divider */}
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: 10, margin: '6px 0',
                        }}>
                            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                            <span style={{ fontSize: 11, color: 'var(--ink-ghost)' }}>or</span>
                            <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                        </div>

                        {/* Anonymous continue */}
                        <button
                            onClick={handleAnonymous}
                            disabled={googleLoading || anonLoading}
                            style={{
                                all: 'unset', cursor: 'pointer',
                                width: '100%', padding: '11px',
                                background: 'var(--surface)',
                                border: '1px solid var(--border)',
                                borderRadius: 12,
                                display: 'flex', alignItems: 'center',
                                justifyContent: 'center', gap: 8,
                                fontSize: 13, color: 'var(--ink-dim)',
                                transition: 'all .15s', marginTop: 6,
                                opacity: (googleLoading || anonLoading) ? 0.6 : 1,
                            }}
                            onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(249,115,22,0.4)')}
                            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                        >
                            {anonLoading ? '⏳' : '👤'}
                            {anonLoading ? 'Starting session…' : 'Continue without account'}
                        </button>

                        {/* Privacy note */}
                        <p style={{
                            marginTop: 18, fontSize: 10.5, color: 'var(--ink-ghost)',
                            textAlign: 'center', lineHeight: 1.6,
                        }}>
                            Google Sign-In preserves your voter profile across devices.<br />
                            Anonymous sessions are cleared after 30 days of inactivity.
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <p style={{
                    textAlign: 'center', marginTop: 16,
                    fontSize: 10, color: 'var(--ink-ghost)',
                }}>
                    Not affiliated with any political party · Official ECI data only ·{' '}
                    <a href="tel:1950" style={{ color: 'var(--saffron)', textDecoration: 'none' }}>
                        Helpline: 1950
                    </a>
                </p>
            </div>

            <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
        </div>
    );
}