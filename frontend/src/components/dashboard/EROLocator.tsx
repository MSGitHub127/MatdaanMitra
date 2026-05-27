'use client';

/**
 * EROLocator.tsx — Electoral Registration Officer lookup dashboard card
 *
 * Renders a pincode search field above the Mapbox map.
 * On a successful search the map flies to the ERO office and shows a popup.
 * Error messages are localised via useEROLocator (Hindi, Gujarati, etc.).
 */

import { useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import { MapPin, Navigation, Phone, Ruler, AlertCircle, RefreshCw } from 'lucide-react';
import { useEROLocator } from '../../hooks/useEROLocator';

// ── Dynamic import prevents SSR crash from mapbox-gl's browser globals ────────
const MapComponent = dynamic(
  () => import('../map/MapComponent'),
  {
    ssr: false,
    loading: () => (
      <div
        className="w-full bg-surface animate-pulse flex flex-col items-center justify-center gap-2"
        style={{ height: 300 }}
      >
        <div className="w-7 h-7 border-2 border-saffron/30 border-t-saffron rounded-full animate-spin" />
        <p className="text-xs text-ink-faint">Loading map…</p>
      </div>
    ),
  },
);

// ─── Component ────────────────────────────────────────────────────────────────

export default function EROLocator() {
  const [pincode, setPincode] = useState('');
  // Language could later come from a global context / VoterProfile; defaulting to 'en'.
  const [language] = useState('en');

  const inputRef = useRef<HTMLInputElement>(null);
  const { ero, isLoading, error, errorStatus, search, reset } = useEROLocator();

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleSearch = () => {
    search(pincode.trim(), language);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleClear = () => {
    setPincode('');
    reset();
    inputRef.current?.focus();
  };

  const handlePincodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '').slice(0, 6);
    setPincode(raw);
    // If user clears the field, reset map state too
    if (!raw) reset();
  };

  // ── Derived state ──────────────────────────────────────────────────────────

  const canSearch = pincode.length === 6 && !isLoading;

  // Differentiate 404 (no office found) from 500 (server error)
  const isNotFound = errorStatus === 404;
  const isServerError = errorStatus !== null && errorStatus >= 500;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden flex flex-col">

      {/* ── Search Header ───────────────────────────────────────────────────── */}
      <div className="p-4 border-b border-border space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-saffron/10 flex items-center justify-center">
            <MapPin className="w-4 h-4 text-saffron" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink leading-none">Find ERO Office</h3>
            <p className="text-xs text-ink-faint mt-0.5">Enter your pincode to locate the nearest office</p>
          </div>
        </div>

        {/* Input row */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={pincode}
              onChange={handlePincodeChange}
              onKeyDown={handleKeyDown}
              placeholder="e.g. 380001"
              maxLength={6}
              aria-label="6-digit pincode"
              aria-describedby={error ? 'ero-error' : undefined}
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-saffron/40 focus:border-saffron transition-colors pr-8"
            />
            {/* Clear button — visible only when there's input */}
            {pincode.length > 0 && (
              <button
                onClick={handleClear}
                aria-label="Clear pincode"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          <button
            onClick={handleSearch}
            disabled={!canSearch}
            aria-label="Search for ERO office"
            className="px-4 py-2 bg-saffron hover:bg-saffron-warm text-bg rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Searching…</span>
              </>
            ) : (
              'Find Office'
            )}
          </button>
        </div>

        {/* Pincode progress indicator */}
        {pincode.length > 0 && pincode.length < 6 && (
          <p className="text-xs text-ink-faint">
            {6 - pincode.length} more digit{6 - pincode.length !== 1 ? 's' : ''} needed
          </p>
        )}

        {/* Error banner */}
        {error && (
          <div
            id="ero-error"
            role="alert"
            className="flex items-start gap-2 p-3 bg-rose/10 border border-rose/20 rounded-lg"
          >
            <AlertCircle className="w-4 h-4 text-rose flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-rose leading-snug">{error}</p>
              {isNotFound && (
                <p className="text-xs text-rose/70 mt-1">
                  Try an adjacent pincode, or call the helpline:{' '}
                  <a href="tel:1950" className="underline font-medium">1950</a>
                </p>
              )}
              {isServerError && (
                <p className="text-xs text-rose/70 mt-1">
                  This is a temporary issue. Please try again in a moment.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Map ─────────────────────────────────────────────────────────────── */}
      <MapComponent eroOffice={ero} height={300} />

      {/* ── ERO Office Detail Card ───────────────────────────────────────────── */}
      {ero && (
        <div className="p-4 border-t border-border space-y-3 bg-surface/40">
          {/* Office name */}
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 rounded-lg bg-saffron/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <MapPin className="w-4 h-4 text-saffron" />
            </div>
            <div>
              <p className="text-xs text-ink-faint mb-0.5">Office Name</p>
              <p className="text-sm font-medium text-ink leading-snug">{ero.name}</p>
            </div>
          </div>

          {/* Address */}
          <div className="pl-10">
            <p className="text-xs text-ink-faint mb-0.5">Address</p>
            <p className="text-sm text-ink leading-snug">{ero.address || '—'}</p>
          </div>

          {/* Phone + Distance row */}
          <div className="pl-10 flex flex-wrap gap-4">
            {ero.phone && ero.phone !== 'N/A' && (
              <div>
                <p className="text-xs text-ink-faint mb-0.5">Phone</p>
                <a
                  href={`tel:${ero.phone}`}
                  className="text-sm text-saffron hover:text-saffron-warm flex items-center gap-1.5 transition-colors"
                >
                  <Phone className="w-3.5 h-3.5" />
                  {ero.phone}
                </a>
              </div>
            )}
            <div>
              <p className="text-xs text-ink-faint mb-0.5">Distance</p>
              <p className="text-sm text-ink flex items-center gap-1.5">
                <Ruler className="w-3.5 h-3.5 text-ink-faint" />
                {ero.distance_km} km
              </p>
            </div>
          </div>

          {/* Directions CTA */}
          <a
            href={ero.directions_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2.5 bg-saffron hover:bg-saffron-warm text-bg rounded-lg text-sm font-semibold transition-colors"
          >
            <Navigation className="w-4 h-4" />
            Get Directions
          </a>
        </div>
      )}

      {/* ── Empty state hint ─────────────────────────────────────────────────── */}
      {!ero && !error && (
        <div className="px-4 py-3 flex items-center gap-2 border-t border-border">
          <div className="w-1.5 h-1.5 rounded-full bg-saffron animate-pulse" />
          <p className="text-xs text-ink-faint">
            Enter your pincode above to find your local ERO office on the map.
          </p>
        </div>
      )}
    </div>
  );
}