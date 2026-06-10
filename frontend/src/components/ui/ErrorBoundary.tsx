'use client';

import React from 'react';

interface Props {
    children: React.ReactNode;
    /** Optional custom fallback UI — defaults to the branded error screen */
    fallback?: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: React.ErrorInfo | null;
}

/**
 * ErrorBoundary — catches React render errors and shows a recovery UI
 * instead of crashing to a white screen.
 *
 * Wrap the root layout with this component so Firebase/Mapbox/API
 * initialisation failures never produce a blank page.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <YourApp />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        this.setState({ errorInfo });
        // In production, send to your error tracking service (e.g. Sentry)
        console.error('[MatdaanMitra] Unhandled render error:', error, errorInfo);
    }

    handleReload = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (!this.state.hasError) return this.props.children;
        if (this.props.fallback) return this.props.fallback;

        const isFirebaseError = this.state.error?.message?.includes('Firebase') ||
            this.state.error?.message?.includes('auth/');
        const isNetworkError = this.state.error?.message?.includes('fetch') ||
            this.state.error?.message?.includes('network');

        return (
            <div style={{
                minHeight: '100vh',
                background: 'var(--bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 24,
                fontFamily: 'Instrument Sans, system-ui, sans-serif',
            }}>
                <div style={{
                    maxWidth: 460,
                    width: '100%',
                    background: 'var(--card)',
                    border: '1px solid var(--border)',
                    borderRadius: 16,
                    overflow: 'hidden',
                }}>
                    {/* Tricolor strip */}
                    <div style={{
                        height: 3,
                        background: 'linear-gradient(to right, #FF9933 33.33%, #F0EDE6 33.33% 66.66%, #138808 66.66%)',
                    }} />

                    <div style={{ padding: '28px 28px 24px' }}>
                        {/* Icon */}
                        <div style={{
                            width: 52, height: 52, borderRadius: 14,
                            background: 'var(--rose-dim)',
                            border: '1px solid rgba(251,113,133,0.3)',
                            display: 'flex', alignItems: 'center',
                            justifyContent: 'center', fontSize: 24, marginBottom: 18,
                        }}>
                            ⚠️
                        </div>

                        {/* Title */}
                        <h2 style={{
                            fontFamily: 'Fraunces, Georgia, serif',
                            fontSize: 20, fontWeight: 700,
                            color: 'var(--ink)', margin: '0 0 8px',
                        }}>
                            Something went wrong
                        </h2>

                        {/* Contextual message */}
                        <p style={{ fontSize: 13, color: 'var(--ink-dim)', lineHeight: 1.6, margin: '0 0 20px' }}>
                            {isFirebaseError
                                ? 'There was a problem connecting to authentication services. Check your internet connection and try reloading.'
                                : isNetworkError
                                    ? 'A network request failed. Please check your connection and try again.'
                                    : 'An unexpected error occurred. Reloading the page usually fixes this.'}
                        </p>

                        {/* Error detail (dev only) */}
                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <details style={{ marginBottom: 20 }}>
                                <summary style={{
                                    fontSize: 11, color: 'var(--ink-ghost)',
                                    cursor: 'pointer', marginBottom: 6,
                                }}>
                                    Error details
                                </summary>
                                <pre style={{
                                    fontSize: 10,
                                    background: 'var(--surface)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 8,
                                    padding: '10px 12px',
                                    color: 'var(--rose)',
                                    overflow: 'auto',
                                    maxHeight: 160,
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-all',
                                }}>
                                    {this.state.error.message}
                                    {this.state.errorInfo?.componentStack}
                                </pre>
                            </details>
                        )}

                        {/* Actions */}
                        <div style={{ display: 'flex', gap: 10 }}>
                            <button
                                onClick={this.handleReload}
                                style={{
                                    flex: 1, padding: '11px',
                                    background: 'linear-gradient(135deg, var(--saffron), #C2410C)',
                                    color: '#030508', border: 'none',
                                    borderRadius: 10, fontSize: 13, fontWeight: 700,
                                    cursor: 'pointer',
                                }}
                            >
                                🔄 Reload Page
                            </button>
                            <a
                                href="tel:1950"
                                style={{
                                    padding: '11px 16px',
                                    background: 'var(--surface)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 10, fontSize: 13,
                                    color: 'var(--ink-dim)',
                                    textDecoration: 'none',
                                    display: 'flex', alignItems: 'center', gap: 6,
                                }}
                            >
                                📞 1950
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

/**
 * Convenience wrapper for use with Next.js App Router.
 * Catches async errors from Server Components too.
 */
export function withErrorBoundary<P extends object>(
    Component: React.ComponentType<P>,
    fallback?: React.ReactNode,
) {
    const Wrapped = (props: P) => (
        <ErrorBoundary fallback={fallback}>
            <Component {...props} />
        </ErrorBoundary>
    );
    Wrapped.displayName = `withErrorBoundary(${Component.displayName ?? Component.name})`;
    return Wrapped;
}