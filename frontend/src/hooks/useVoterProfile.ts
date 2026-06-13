import { useState, useEffect, useCallback } from 'react';
import { db, ensureAuth, auth } from '../lib/firebase';
import { doc, onSnapshot } from 'firebase/firestore';
import type { VoterProfile } from '../types/voter';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

export function useVoterProfile(sessionId: string) {
  const [profile, setProfile] = useState<VoterProfile>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Subscribe to real-time Firestore updates for this session
  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const loadProfile = async () => {
      try {
        await ensureAuth();
        const docRef = doc(db, 'sessions', sessionId);

        unsubscribe = onSnapshot(
          docRef,
          (docSnap) => {
            if (docSnap.exists()) {
              const data = docSnap.data();
              setProfile(data.voterProfile ?? {});
            }
            setIsLoading(false);
          },
          (err) => {
            setError(err.message);
            setIsLoading(false);
          }
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile');
        setIsLoading(false);
      }
    };

    loadProfile();
    return () => { if (unsubscribe) unsubscribe(); };
  }, [sessionId]);

  /**
   * Update the checklist via the backend PATCH endpoint — NOT a direct
   * Firestore write. Direct writes bypass the backend's EPIC encryption,
   * which would put the plaintext EPIC number back into Firestore.
   */
  const updateChecklist = useCallback(
    async (checklist: Record<string, boolean>) => {
      try {
        const user = auth.currentUser;
        if (!user) throw new Error('Not authenticated');
        const token = await user.getIdToken();

        const res = await fetch(`${BACKEND_URL}/profile/${sessionId}/checklist`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ checklist }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail ?? `Request failed (${res.status})`);
        }

        // Firestore onSnapshot will pick up the change automatically —
        // no need to call setProfile manually here.
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to update checklist';
        setError(msg);
        throw err;
      }
    },
    [sessionId]
  );

  return { profile, updateChecklist, isLoading, error };
}