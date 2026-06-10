/** @type {import('next').NextConfig} */

const nextConfig = {
  // Required for standalone Docker/Cloud Run deployment
  output: 'standalone',

  reactStrictMode: true,

  // Suppress hydration warnings from browser extensions
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // ── Mapbox GL JS transpilation ─────────────────────────────────────────────
  // mapbox-gl ships as ES modules and must be transpiled for Next.js
  transpilePackages: ['mapbox-gl'],

  webpack(config, { isServer }) {
    // mapbox-gl uses browser globals — exclude from server bundle
    if (isServer) {
      config.externals = [...(config.externals || []), 'mapbox-gl'];
    }
    return config;
  },

  // ── Security headers ───────────────────────────────────────────────────────
  async headers() {
    const csp = [
      "default-src 'self'",
      // Next.js inline scripts + Firebase SDK
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://*.firebaseapp.com https://apis.google.com",
      // API calls, Mapbox tiles, Firebase, Sarvam AI
      [
        "connect-src 'self'",
        'https://*.googleapis.com',
        'https://*.mapbox.com',
        'https://events.mapbox.com',
        'https://api.sarvam.ai',
        'https://*.firebaseio.com',
        'wss://*.firebaseio.com',
        'https://identitytoolkit.googleapis.com',
        'https://securetoken.googleapis.com',
      ].join(' '),
      // Mapbox map tiles and local blobs
      "img-src 'self' data: blob: https://*.mapbox.com https://maps.gstatic.com",
      // Google Fonts + inline styles (Mapbox GL injects inline)
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' data: https://fonts.gstatic.com",
      // Mapbox GL worker (runs in a blob Web Worker)
      "worker-src blob:",
      "frame-src 'none'",
      "object-src 'none'",
      "base-uri 'self'",
    ].join('; ');

    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(self), payment=()',
          },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          { key: 'Content-Security-Policy', value: csp },
        ],
      },
      // Long-cache for static assets
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
};

export default nextConfig;
