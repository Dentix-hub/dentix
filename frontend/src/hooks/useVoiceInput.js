
import { useState, useRef, useEffect, useCallback } from 'react';

export const useVoiceInput = (onFinalTranscript) => {
    const [isListening, setIsListening] = useState(false);
    const [finalTranscript, setFinalTranscript] = useState('');
    const [interimTranscript, setInterimTranscript] = useState('');
    const [speechSupported, setSpeechSupported] = useState(false);
    const recognitionRef = useRef(null);
    const onFinalTranscriptRef = useRef(onFinalTranscript);
    const silenceTimerRef = useRef(null);

    // Update callback ref to avoid re-triggering effect
    useEffect(() => {
        onFinalTranscriptRef.current = onFinalTranscript;
    }, [onFinalTranscript]);

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            setSpeechSupported(true);
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'ar-EG';
            recognition.maxAlternatives = 1;

            recognition.onresult = (event) => {
                // Clear any pending stop timer as user is speaking
                if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

                let newInterim = '';
                let newFinal = '';

                // Smart incremental handling
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const chunk = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        newFinal += chunk;
                    } else {
                        newInterim += chunk;
                    }
                }

                if (newFinal) {
                    setFinalTranscript(prev => {
                        const spacer = prev && !prev.endsWith(' ') && !newFinal.startsWith(' ') ? ' ' : '';
                        return prev + spacer + newFinal;
                    });

                    if (onFinalTranscriptRef.current) {
                        onFinalTranscriptRef.current(newFinal);
                    }

                    // Auto-stop after silence following a final phrase
                    silenceTimerRef.current = setTimeout(() => {
                        try { recognition.stop(); } catch (e) { }
                    }, 2000);
                }

                setInterimTranscript(newInterim);
            };

            recognition.onend = () => {
                setIsListening(false);
                if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            };

            recognition.onerror = (event) => {
                console.warn('Speech recognition error:', event.error);
                if (event.error === 'not-allowed') {
                    setIsListening(false);
                    alert('يرجى السماح بالوصول للميكروفون 🎤');
                } else if (event.error === 'no-speech') {
                    // Just stop listening on silence timeout
                    setIsListening(false);
                }
                else {
                    // Stop on other errors
                    setIsListening(false);
                }
            };

            recognitionRef.current = recognition;

            // Cleanup on unmount
            return () => {
                if (recognitionRef.current) {
                    try { recognitionRef.current.abort(); } catch (e) { }
                }
                if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
            };
        }
    }, []);

    const startListening = useCallback(() => {
        if (!recognitionRef.current) return;

        setFinalTranscript('');
        setInterimTranscript('');

        // Optimistic Start: Try to start immediately for lowest latency
        try {
            recognitionRef.current.start();
            setIsListening(true);
        } catch (error) {
            // If failed (e.g. already running/zombie), then force reset
            console.warn("Speech start failed, resetting:", error);
            try { recognitionRef.current.abort(); } catch (e) { }

            setTimeout(() => {
                try {
                    recognitionRef.current.start();
                    setIsListening(true);
                } catch (retryError) {
                    console.error("Speech retry start error:", retryError);
                }
            }, 50);
        }
    }, []);

    const stopListening = useCallback(() => {
        if (!recognitionRef.current) return;
        try {
            recognitionRef.current.stop();
        } catch (e) { }
        setIsListening(false);
    }, []);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    // Construct full transcript for UI
    const transcript = finalTranscript + (interimTranscript ? (finalTranscript ? ' ' : '') + interimTranscript : '');

    return {
        isListening,
        toggleListening,
        stopListening,
        startListening,
        speechSupported,
        transcript
    };
};
