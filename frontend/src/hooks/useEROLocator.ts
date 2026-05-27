/**
 * useEROLocator.ts — React hook for ERO office lookup
 *
 * Encapsulates loading, error, and data state so EROLocator.tsx
 * (and any future component) can stay as a pure display layer.
 */

import { useState, useCallback } from 'react';
import { getEROLocation, ApiError } from '../lib/api';
import type { EROOffice } from '../types/voter';

// Fallback error messages keyed by language code.
// These cover the case where the backend or Sarvam AI is unreachable.
const FALLBACK_ERRORS: Record<string, string> = {
    en: 'Could not find the ERO office. Please try again later.',
    hi: 'ERO कार्यालय नहीं मिला। कृपया बाद में पुनः प्रयास करें।',
    gu: 'ERO કાર્યાલય મળ્યું નહીં. કૃપા કરીને ફરી પ્રયાસ કરો.',
    mr: 'ERO कार्यालय सापडले नाही. कृपया नंतर पुन्हा प्रयत्न करा.',
    ta: 'ERO அலுவலகம் கண்டுபிடிக்கப்படவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.',
    te: 'ERO కార్యాలయం కనుగొనబడలేదు. దయచేసి తిరిగి ప్రయత్నించండి.',
    bn: 'ERO অফিস পাওয়া যায়নি। পরে আবার চেষ্টা করুন।',
    kn: 'ERO ಕಚೇರಿ ಕಂಡುಹಿಡಿಯಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
};

const VALIDATION_ERRORS: Record<string, string> = {
    en: 'Please enter a valid 6-digit pincode.',
    hi: 'कृपया 6 अंकों का सही पिनकोड दर्ज करें।',
    gu: 'કૃપા કરીને 6 અંકોનો માન્ય પિન કોડ દાખલ કરો.',
    mr: 'कृपया 6 अंकी वैध पिनकोड प्रविष्ट करा.',
    ta: '6 இலக்க சரியான பின்கோட்டை உள்ளிடவும்.',
    te: '6 అంకెల చెల్లుబాటు అయ్యే పిన్‌కోడ్‌ను నమోదు చేయండి.',
    bn: 'একটি বৈধ ৬-সংখ্যার পিনকোড লিখুন।',
    kn: '6 ಅಂಕಿಗಳ ಮಾನ್ಯ ಪಿನ್‌ಕೋಡ್ ನಮೂದಿಸಿ.',
};

export interface UseEROLocatorReturn {
    /** The found ERO office, or null if not yet searched / not found. */
    ero: EROOffice | null;
    isLoading: boolean;
    error: string | null;
    /** HTTP status of the last failed request, for differentiated UI. */
    errorStatus: number | null;
    /** Triggers a new search. Accepts the active UI language for localized errors. */
    search: (pincode: string, language?: string) => Promise<void>;
    /** Clears results and errors — useful when the user clears the input. */
    reset: () => void;
}

export function useEROLocator(): UseEROLocatorReturn {
    const [ero, setEro] = useState<EROOffice | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [errorStatus, setErrorStatus] = useState<number | null>(null);

    const search = useCallback(async (pincode: string, language = 'en') => {
        const lang = FALLBACK_ERRORS[language] ? language : 'en';

        if (!pincode || pincode.length !== 6) {
            setError(VALIDATION_ERRORS[lang]);
            return;
        }

        setIsLoading(true);
        setError(null);
        setErrorStatus(null);

        try {
            const result = await getEROLocation(pincode);
            setEro(result);
        } catch (err) {
            let message = FALLBACK_ERRORS[lang];
            let status: number | null = null;

            if (err instanceof ApiError) {
                // Surface the backend's message if it's meaningful
                if (err.message && !err.message.startsWith('Request failed')) {
                    message = err.message;
                }
                status = err.status;
            }

            setError(message);
            setErrorStatus(status);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const reset = useCallback(() => {
        setEro(null);
        setError(null);
        setErrorStatus(null);
    }, []);

    return { ero, isLoading, error, errorStatus, search, reset };
}