import { useState, useEffect, useCallback } from 'react';
import { db, ensureAuth } from '../lib/firebase';
import { doc, getDoc, setDoc, onSnapshot } from 'firebase/firestore';
import type { VoterProfile } from '../types/voter';

export function useVoterProfile(sessionId: string) {
  const [profile, setProfile] = useState<VoterProfile>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const loadProfile = async () => {
      try {
        const uid = await ensureAuth();
        const docRef = doc(db, 'sessions', sessionId);

        unsubscribe = onSnapshot(
          docRef,
          (docSnap) => {
            if (docSnap.exists()) {
              const data = docSnap.data();
              setProfile(data.voterProfile || {});
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

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [sessionId]);

  const updateChecklist = useCallback(
    async (checklist: Record<string, boolean>) => {
      try {
        const uid = await ensureAuth();
        const docRef = doc(db, 'sessions', sessionId);

        await setDoc(
          docRef,
          {
            uid,
            voterProfile: {
              ...profile,
              checklist,
            },
            updatedAt: new Date().toISOString(),
          },
          { merge: true }
        );

        setProfile((prev) => ({ ...prev, checklist }));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update checklist');
        throw err;
      }
    },
    [sessionId, profile]
  );

  return { profile, updateChecklist, isLoading, error };
}
