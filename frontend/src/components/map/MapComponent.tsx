'use client';

/**
 * MapComponent.tsx — Mapbox GL JS map for MatdaanMitra
 *
 * Responsibilities:
 *  - Renders an interactive Mapbox map centred on India.
 *  - Shows a custom saffron marker for the found ERO office.
 *  - Flies to the ERO location with a smooth animation and auto-opens a popup.
 *  - Provides user geolocation (GeolocateControl).
 *  - Handles missing token and map load errors gracefully.
 *  - Fully unmounts the map on component destruction to prevent memory leaks.
 *
 * NOTE: This component MUST be imported with next/dynamic + { ssr: false }
 * because mapbox-gl accesses browser globals (window, WebGL context).
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { EROOffice } from '../../types/voter';

// ─── Constants ────────────────────────────────────────────────────────────────

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ?? process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? '';

/** Geographical centre of India */
const INDIA_CENTER: [number, number] = [78.9629, 20.5937];
const INDIA_ZOOM = 4.2;
const OFFICE_ZOOM = 14.5;
const FLY_DURATION_MS = 1800;

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MapComponentProps {
    /** When provided, the map flies to the office and renders a marker + popup. */
    eroOffice: EROOffice | null;
    /** Additional Tailwind/CSS classes applied to the outer container. */
    className?: string;
    /** Height of the map canvas. Defaults to 320px. */
    height?: number | string;
}

// ─── Custom Marker Element ────────────────────────────────────────────────────

/**
 * Creates a DOM element for the ERO office marker.
 * Uses a saffron teardrop pin matching the MatdaanMitra design system.
 */
function createMarkerEl(): HTMLElement {
    const wrapper = document.createElement('div');
    wrapper.setAttribute('role', 'img');
    wrapper.setAttribute('aria-label', 'ERO Office location');
    wrapper.style.cssText = 'cursor: pointer; filter: drop-shadow(0 4px 12px rgba(255,153,51,0.55));';

    wrapper.innerHTML = `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="42"
      height="52"
      viewBox="0 0 42 52"
      fill="none"
      style="transition: transform 0.2s cubic-bezier(.34,1.56,.64,1); transform-origin: bottom center;"
    >
      <!-- Teardrop pin body -->
      <path
        d="M21 0C9.402 0 0 9.402 0 21c0 14.5 21 31 21 31S42 35.5 42 21C42 9.402 32.598 0 21 0z"
        fill="#FF9933"
      />
      <!-- Inner circle (white) -->
      <circle cx="21" cy="21" r="9" fill="white" opacity="0.95"/>
      <!-- Ashok Chakra inspired centre dot -->
      <circle cx="21" cy="21" r="3.5" fill="#FF9933"/>
      <!-- Small spokes at 45° angles — simplified Chakra feel -->
      <line x1="21" y1="12" x2="21" y2="15" stroke="#FF9933" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="21" y1="27" x2="21" y2="30" stroke="#FF9933" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="12" y1="21" x2="15" y2="21" stroke="#FF9933" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="27" y1="21" x2="30" y2="21" stroke="#FF9933" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
  `;

    const svg = wrapper.querySelector('svg') as SVGElement;

    wrapper.addEventListener('mouseenter', () => {
        svg.style.transform = 'scale(1.18)';
    });
    wrapper.addEventListener('mouseleave', () => {
        svg.style.transform = 'scale(1)';
    });

    return wrapper;
}

// ─── Popup HTML ───────────────────────────────────────────────────────────────

function buildPopupHTML(office: EROOffice): string {
    const phoneHtml = office.phone && office.phone !== 'N/A'
        ? `<a
        href="tel:${office.phone}"
        style="color:#FF9933;text-decoration:none;display:flex;align-items:center;gap:5px;margin-bottom:5px;"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="#FF9933" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498A1 1 0 0121 15.72V19a2 2 0 01-2 2h-1C9.163 21 3 14.837 3 7V5z"/>
        </svg>
        ${office.phone}
      </a>`
        : '';

    return `
    <div style="
      font-family: 'Nunito', system-ui, sans-serif;
      min-width: 230px;
      max-width: 270px;
      padding: 14px 16px 12px;
    ">
      <!-- Header -->
      <div style="display:flex;align-items:flex-start;gap:9px;margin-bottom:11px;padding-bottom:10px;border-bottom:1px solid #f0f0f0;">
        <div style="
          width:34px;height:34px;border-radius:8px;
          background:linear-gradient(135deg,#FF9933,#e8851e);
          display:flex;align-items:center;justify-content:center;
          flex-shrink:0;
        ">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="white" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
          </svg>
        </div>
        <div>
          <p style="margin:0;font-size:12px;font-weight:700;color:#111;line-height:1.4;letter-spacing:0.01em;">
            ${office.name}
          </p>
          <p style="margin:2px 0 0;font-size:11px;color:#888;font-weight:500;">
            Electoral Registration Officer
          </p>
        </div>
      </div>

      <!-- Details -->
      <div style="font-size:12px;color:#555;line-height:1.5;">
        <p style="margin:0 0 6px;display:flex;gap:5px;align-items:flex-start;">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="#999" stroke-width="2" style="flex-shrink:0;margin-top:1px;">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <span>${office.address || 'Address not available'}</span>
        </p>
        ${phoneHtml}
        <p style="margin:0 0 12px;display:flex;align-items:center;gap:5px;color:#777;">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="#999" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
          </svg>
          ${office.distance_km} km straight-line distance
        </p>
      </div>

      <!-- CTA -->
      <a
        href="${office.directions_url}"
        target="_blank"
        rel="noopener noreferrer"
        style="
          display:flex;align-items:center;justify-content:center;gap:7px;
          padding:9px 14px;
          background:#FF9933;
          color:#fff;
          border-radius:9px;
          text-decoration:none;
          font-size:12px;
          font-weight:700;
          letter-spacing:0.02em;
          transition:background 0.15s;
        "
        onmouseover="this.style.background='#e8851e'"
        onmouseout="this.style.background='#FF9933'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="white" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        Open in Maps
      </a>
    </div>
  `;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function MapComponent({
    eroOffice,
    className = '',
    height = 320,
}: MapComponentProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<mapboxgl.Map | null>(null);
    const markerRef = useRef<mapboxgl.Marker | null>(null);
    const popupRef = useRef<mapboxgl.Popup | null>(null);
    const flyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [mapError, setMapError] = useState<string | null>(null);
    const [isMapReady, setIsMapReady] = useState(false);

    // ── Map Initialisation ─────────────────────────────────────────────────────
    useEffect(() => {
        if (!containerRef.current || mapRef.current) return;

        if (!TOKEN) {
            setMapError('Mapbox token is missing. Add NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN to .env.local');
            return;
        }

        mapboxgl.accessToken = TOKEN;

        let map: mapboxgl.Map;
        try {
            map = new mapboxgl.Map({
                container: containerRef.current,
                // Dark style fits the MatdaanMitra card theme
                style: 'mapbox://styles/mapbox/dark-v11',
                center: INDIA_CENTER,
                zoom: INDIA_ZOOM,
                // Restrict to India + neighbours for performance
                maxBounds: [
                    [60.0, 5.0],   // SW corner
                    [100.0, 40.0], // NE corner
                ],
                attributionControl: false,
                logoPosition: 'bottom-left',
                cooperativeGestures: false,
            });
        } catch (err) {
            setMapError('WebGL is not supported in your browser. Please use a modern browser.');
            return;
        }

        // Controls
        map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right');
        map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(
            new mapboxgl.GeolocateControl({
                positionOptions: { enableHighAccuracy: true },
                trackUserLocation: false,
                showAccuracyCircle: true,
                fitBoundsOptions: { maxZoom: 13 },
            }),
            'top-right',
        );
        map.addControl(new mapboxgl.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left');

        map.on('load', () => setIsMapReady(true));
        map.on('error', (e) => {
            console.error('[MatdaanMitra] Mapbox error:', e.error);
        });

        mapRef.current = map;

        return () => {
            if (flyTimerRef.current) clearTimeout(flyTimerRef.current);
            map.remove();
            mapRef.current = null;
            setIsMapReady(false);
        };
    }, []); // intentionally empty — map init happens once

    // ── Marker + Popup update when eroOffice changes ───────────────────────────
    const updateMarker = useCallback(() => {
        const map = mapRef.current;
        if (!map) return;

        // Clean up previous marker and popup
        if (flyTimerRef.current) clearTimeout(flyTimerRef.current);
        popupRef.current?.remove();
        markerRef.current?.remove();
        popupRef.current = null;
        markerRef.current = null;

        if (!eroOffice) {
            // Reset view to India
            map.flyTo({ center: INDIA_CENTER, zoom: INDIA_ZOOM, duration: 1200 });
            return;
        }

        const { latitude, longitude } = eroOffice;

        const popup = new mapboxgl.Popup({
            offset: [0, -46], // clear the top of the teardrop pin
            maxWidth: '290px',
            className: 'mm-ero-popup',
            closeButton: true,
            closeOnClick: false,
            focusAfterOpen: false,
        }).setHTML(buildPopupHTML(eroOffice));

        const marker = new mapboxgl.Marker({
            element: createMarkerEl(),
            anchor: 'bottom',
        })
            .setLngLat([longitude, latitude])
            .setPopup(popup)
            .addTo(map);

        markerRef.current = marker;
        popupRef.current = popup;

        // Fly to the office, then open the popup after the animation lands
        map.flyTo({
            center: [longitude, latitude],
            zoom: OFFICE_ZOOM,
            duration: FLY_DURATION_MS,
            essential: true,
            curve: 1.35,
            speed: 0.9,
        });

        flyTimerRef.current = setTimeout(() => {
            marker.togglePopup();
        }, FLY_DURATION_MS + 120);
    }, [eroOffice]);

    useEffect(() => {
        if (isMapReady) {
            updateMarker();
        }
    }, [eroOffice, isMapReady, updateMarker]);

    // ── Error state ─────────────────────────────────────────────────────────────
    if (mapError) {
        return (
            <div
                className={`flex flex-col items-center justify-center bg-surface rounded-lg border border-border text-center p-6 ${className}`}
                style={{ height }}
            >
                <svg
                    className="w-10 h-10 text-ink-faint mb-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                    />
                </svg>
                <p className="text-sm text-ink-faint max-w-xs">{mapError}</p>
            </div>
        );
    }

    return (
        <>
            {/* Scoped popup styles — Mapbox injects popups into document.body,
          so global styles are needed (component CSS-in-JS won't reach them). */}
            <style>{`
        .mm-ero-popup .mapboxgl-popup-content {
          border-radius: 14px;
          padding: 0;
          box-shadow: 0 8px 40px rgba(0,0,0,0.22), 0 0 0 1px rgba(255,153,51,0.15);
          overflow: hidden;
          animation: mm-popup-in 0.22s cubic-bezier(.34,1.56,.64,1);
        }
        .mm-ero-popup .mapboxgl-popup-tip {
          border-top-color: #fff;
        }
        .mm-ero-popup .mapboxgl-popup-close-button {
          font-size: 18px;
          color: #bbb;
          padding: 6px 10px;
          line-height: 1;
          background: transparent;
          border: none;
          cursor: pointer;
          position: absolute;
          top: 4px;
          right: 4px;
        }
        .mm-ero-popup .mapboxgl-popup-close-button:hover {
          color: #555;
        }
        @keyframes mm-popup-in {
          from { opacity: 0; transform: scale(0.88) translateY(6px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
        /* Tighten Mapbox attribution to not clash with card border-radius */
        .mapboxgl-ctrl-attrib {
          font-size: 10px !important;
        }
        /* Align controls with card rounding */
        .mapboxgl-ctrl-top-right {
          margin-top: 10px;
          margin-right: 10px;
        }
      `}</style>

            <div
                ref={containerRef}
                className={`relative w-full overflow-hidden ${className}`}
                style={{ height }}
                role="application"
                aria-label="Interactive map showing ERO office location"
            >
                {/* Overlay shown while map tiles load */}
                {!isMapReady && (
                    <div className="absolute inset-0 flex items-center justify-center bg-surface z-10 pointer-events-none">
                        <div className="flex flex-col items-center gap-3">
                            <div className="w-8 h-8 border-2 border-saffron/30 border-t-saffron rounded-full animate-spin" />
                            <p className="text-xs text-ink-faint">Loading map…</p>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}