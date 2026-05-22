import { useState } from 'react';
import { MapPin, Navigation, Phone } from 'lucide-react';
import { getEROLocation } from '../../lib/api';

export default function EROLocator() {
  const [pincode, setPincode] = useState('');
  const [ero, setEro] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!pincode || pincode.length !== 6) {
      setError('Please enter a valid 6-digit pincode');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getEROLocation(pincode);
      setEro(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to find ERO office');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="w-4 h-4 text-saffron" />
        <h3 className="text-sm font-medium text-ink">Find ERO Office</h3>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={pincode}
          onChange={(e) => setPincode(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="Enter 6-digit pincode"
          maxLength={6}
          className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:border-saffron"
        />
        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="px-4 py-2 bg-saffron hover:bg-saffron-warm text-bg rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {isLoading ? 'Searching...' : 'Find'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose/10 border border-rose/20 rounded-lg mb-4">
          <p className="text-sm text-rose">{error}</p>
        </div>
      )}

      {ero && (
        <div className="space-y-3">
          <div>
            <p className="text-xs text-ink-faint">Office Name</p>
            <p className="text-sm text-ink">{ero.name}</p>
          </div>
          <div>
            <p className="text-xs text-ink-faint">Address</p>
            <p className="text-sm text-ink">{ero.address}</p>
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <p className="text-xs text-ink-faint">Phone</p>
              <p className="text-sm text-ink">{ero.phone}</p>
            </div>
            <div className="flex-1">
              <p className="text-xs text-ink-faint">Distance</p>
              <p className="text-sm text-ink">{ero.distance_km} km</p>
            </div>
          </div>
          <a
            href={ero.directions_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-saffron hover:text-saffron-warm"
          >
            <Navigation className="w-4 h-4" />
            <span>Get Directions</span>
          </a>
        </div>
      )}
    </div>
  );
}
