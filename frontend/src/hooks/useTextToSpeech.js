import { useState, useCallback, useEffect } from 'react';

export const useTextToSpeech = (initialEnabled = false) => {
    const [ttsEnabled, setTtsEnabled] = useState(initialEnabled);
    const [isSpeaking, setIsSpeaking] = useState(false);

    const speakText = useCallback((text) => {
        if (!ttsEnabled || !('speechSynthesis' in window)) return;

        window.speechSynthesis.cancel();
        setIsSpeaking(true);

        // Clean text
        const cleanText = text
            .replace(/\*\*/g, '')
            .replace(/[📋💰📊📅👥🏥🩺💳💸🔬✅❌📌📛🎫]/g, '')
            .replace(/\n/g, '. ');

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'ar-SA';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);

        window.speechSynthesis.speak(utterance);
    }, [ttsEnabled]);

    const cancelSpeech = useCallback(() => {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            setIsSpeaking(false);
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            cancelSpeech();
        };
    }, [cancelSpeech]);

    return {
        ttsEnabled,
        setTtsEnabled,
        speakText,
        cancelSpeech,
        isSpeaking
    };
};
