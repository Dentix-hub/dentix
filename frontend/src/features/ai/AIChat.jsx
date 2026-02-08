/**
 * AI Chat Component - Smart Dent Clinic
 * Floating chat interface for natural language queries with voice support
 * Features: Context Memory, Medical Scribe Mode
 */

import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, User, Loader2, Sparkles, AlertCircle, Mic, MicOff, Calendar, Users, DollarSign, Building2, Volume2, VolumeX, FileEdit } from 'lucide-react';
import { sendAIQuery } from '@/api';
import aiAvatar from '@/assets/dental_ai_avatar.png';
import { useVoiceInput } from '@/hooks/useVoiceInput';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import { formatAIResponse } from '@/utils/aiResponseFormatter';
import { useTranslation } from 'react-i18next';

export default function AIChat() {
    const { t } = useTranslation();

    // Initial greeting in current language
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: t('ai_chat.welcome_message'),
            type: 'greeting'
        }
    ]);

    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [autoSendAfterSpeech, setAutoSendAfterSpeech] = useState(false);
    const [lastPatientName, setLastPatientName] = useState(null); // For context memory
    const [scribeMode, setScribeMode] = useState(false); // Medical Scribe Mode

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Custom Hooks
    const {
        isListening,
        toggleListening,
        stopListening,
        startListening,
        speechSupported,
        transcript
    } = useVoiceInput((finalText) => {
        if (finalText.trim()) {
            setAutoSendAfterSpeech(true);
        }
    });

    const {
        ttsEnabled,
        setTtsEnabled,
        speakText
    } = useTextToSpeech(false);

    // Sync transcript to input
    useEffect(() => {
        if (isListening) {
            setInput(transcript);
        }
    }, [transcript, isListening]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus();
        }
    }, [isOpen]);

    // Auto-send after speech recognition ends
    useEffect(() => {
        if (autoSendAfterSpeech && input.trim() && !isListening) {
            setAutoSendAfterSpeech(false);
            handleSend();
        }
    }, [autoSendAfterSpeech, isListening, input]);

    // Sync Scribe Mode with Microphone
    useEffect(() => {
        if (scribeMode) {
            if (!isListening) startListening();
        } else {
            if (isListening) stopListening();
        }
    }, [scribeMode]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        // Stop listening if active
        if (isListening) {
            stopListening();
        }

        const userMessage = input.trim();
        setInput('');

        // Add user message
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            // Build conversation context (last 10 messages)
            const conversationContext = messages.slice(-10).map(m => ({
                role: m.role,
                content: m.content
            }));

            // Send query with context (Phase 1: Memory)
            const response = await sendAIQuery(userMessage, {
                context: conversationContext,
                last_patient_name: lastPatientName,
                scribe_mode: scribeMode
            });

            // Format response based on tool
            let assistantMessage = formatAIResponse(response.data);
            setMessages(prev => [...prev, assistantMessage]);

            // Text-to-Speech
            if (ttsEnabled && assistantMessage.content) {
                speakText(assistantMessage.content);
            }

            // Remember patient name for context
            if (response.data?.data?.patient?.name) {
                setLastPatientName(response.data.data.patient.name);
            } else if (response.data?.data?.patient_name) {
                setLastPatientName(response.data.data.patient_name);
            }
        } catch (err) {
            console.error('AI Query Error:', err);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: err.response?.data?.detail || t('ai_chat.chat.connection_error'),
                type: 'error'
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    // Quick action handler - transmits the exact query to backend
    const handleQuickAction = (displayLabel, queryText) => {
        // We display the queryText in input for clarity, but the button label was translated
        setInput(queryText);
        // Trigger send after a short delay
        setTimeout(() => {
            if (inputRef.current) {
                // const event = new KeyboardEvent('keypress', { key: 'Enter' }); 
                // Removed unused event
                handleSend();
            }
        }, 100);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const getMessageStyle = (type) => {
        switch (type) {
            case 'error': return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
            case 'warning': return 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800';
            case 'success': return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800';
            default: return 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700';
        }
    };

    return (
        <>
            {/* Floating Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`fixed bottom-6 z-50 p-0 rounded-full shadow-2xl transition-all duration-300 ltr:right-6 rtl:left-6 ${isOpen
                    ? 'bg-slate-700 hover:bg-slate-800 rotate-90 w-14 h-14 flex items-center justify-center'
                    : 'bg-transparent animate-bounce-slow hover:scale-110'
                    }`}
            >
                {isOpen ? (
                    <X size={24} className="text-white" />
                ) : (
                    <img
                        src={aiAvatar}
                        alt="AI Assistant"
                        className="w-16 h-16 md:w-24 md:h-24 drop-shadow-2xl filter hover:brightness-110 transition-all transform hover:scale-105"
                    />
                )}
            </button>

            {/* Chat Window */}
            {isOpen && (
                <div className="fixed bottom-24 z-50 w-96 max-w-[calc(100vw-3rem)] h-[500px] max-h-[70vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-300 ltr:right-6 rtl:left-6">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-violet-600 to-indigo-600 p-4 flex items-center gap-3">
                        <div className="bg-white/10 rounded-full border border-white/20 w-12 h-12 flex items-center justify-center overflow-hidden shrink-0">
                            <img src={aiAvatar} alt="AI" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-white font-bold">{t('ai_chat.title')}</h3>
                            <p className="text-violet-200 text-xs">{t('ai_chat.subtitle')}</p>
                        </div>
                        {isListening && (
                            <div className="flex items-center gap-1 bg-red-500 text-white px-2 py-1 rounded-full text-xs animate-pulse">
                                <Mic size={12} />
                                <span>{t('ai_chat.listening')}</span>
                            </div>
                        )}
                        {/* TTS Toggle */}
                        <button
                            onClick={() => setTtsEnabled(!ttsEnabled)}
                            className={`p-2 rounded-lg transition-all ${ttsEnabled ? 'bg-green-500 text-white' : 'bg-white/20 text-white/70 hover:bg-white/30'}`}
                            title={ttsEnabled ? t('ai_chat.toggle_sound_off') : t('ai_chat.toggle_sound_on')}
                        >
                            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                        </button>
                    </div>

                    {/* Quick Actions */}
                    <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-700 flex gap-2 overflow-x-auto">
                        <button
                            onClick={() => handleQuickAction(t('ai_chat.quick_actions.appointments'), t('ai_chat.quick_queries.appointments'))}
                            className="flex items-center gap-1 px-3 py-1.5 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 rounded-full text-xs whitespace-nowrap hover:bg-violet-200 dark:hover:bg-violet-900/50 transition-all"
                        >
                            <Calendar size={12} />
                            <span>{t('ai_chat.quick_actions.appointments')}</span>
                        </button>
                        <button
                            onClick={() => handleQuickAction(t('ai_chat.quick_actions.debtors'), t('ai_chat.quick_queries.debtors'))}
                            className="flex items-center gap-1 px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full text-xs whitespace-nowrap hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-all"
                        >
                            <DollarSign size={12} />
                            <span>{t('ai_chat.quick_actions.debtors')}</span>
                        </button>
                        <button
                            onClick={() => handleQuickAction(t('ai_chat.quick_actions.staff'), t('ai_chat.quick_queries.staff'))}
                            className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-xs whitespace-nowrap hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-all"
                        >
                            <Users size={12} />
                            <span>{t('ai_chat.quick_actions.staff')}</span>
                        </button>
                        <button
                            onClick={() => handleQuickAction(t('ai_chat.quick_actions.clinic'), t('ai_chat.quick_queries.clinic'))}
                            className="flex items-center gap-1 px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded-full text-xs whitespace-nowrap hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition-all"
                        >
                            <Building2 size={12} />
                            <span>{t('ai_chat.quick_actions.clinic')}</span>
                        </button>
                        {/* Medical Scribe Mode Toggle */}
                        <button
                            onClick={() => setScribeMode(!scribeMode)}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-all ${scribeMode
                                ? 'bg-rose-500 text-white animate-pulse'
                                : 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-900/50'
                                }`}
                            title={t('ai_chat.scribe_mode.tooltip')}
                        >
                            <FileEdit size={12} />
                            <span>{scribeMode ? t('ai_chat.scribe_mode.button_active') : t('ai_chat.scribe_mode.button_inactive')}</span>
                        </button>
                    </div>

                    {/* Scribe Mode Banner */}
                    {scribeMode && (
                        <div className="px-3 py-2 bg-gradient-to-r from-rose-500 to-pink-500 text-white text-xs flex items-center justify-between">
                            <span>{t('ai_chat.scribe_mode.banner')}</span>
                            <button
                                onClick={() => setScribeMode(false)}
                                className="px-2 py-0.5 bg-white/20 rounded hover:bg-white/30"
                            >
                                {t('ai_chat.scribe_mode.stop')}
                            </button>
                        </div>
                    )}

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[85%] ${msg.role === 'user'
                                    ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-2xl rounded-br-sm'
                                    : `${getMessageStyle(msg.type)} border rounded-2xl rounded-bl-sm`
                                    } p-3 shadow-sm`}>
                                    {msg.role === 'assistant' && (
                                        <div className="flex items-center gap-2 mb-2 text-violet-600 dark:text-violet-400">
                                            <Bot size={16} />
                                            <span className="text-xs font-bold">{t('ai_chat.chat.assistant_label')}</span>
                                        </div>
                                    )}
                                    <div className={`text-sm whitespace-pre-wrap ${msg.role === 'user' ? '' : 'text-slate-700 dark:text-slate-300'}`}>
                                        {msg.content.split('**').map((part, i) =>
                                            i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                                        )}
                                    </div>
                                    {/* Smart Suggestions */}
                                    {msg.suggestions && msg.suggestions.length > 0 && (
                                        <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-600 flex flex-wrap gap-2">
                                            {msg.suggestions.map((suggestion, si) => (
                                                <button
                                                    key={si}
                                                    onClick={() => handleQuickAction(suggestion, suggestion)}
                                                    className="text-xs px-2 py-1 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 rounded-full hover:bg-violet-200 dark:hover:bg-violet-900/50 transition-all"
                                                >
                                                    💡 {suggestion}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-sm p-4 flex items-center gap-2">
                                    <Loader2 size={16} className="animate-spin text-violet-600" />
                                    <span className="text-sm text-slate-500">{t('ai_chat.processing')}</span>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input with Voice */}
                    <div className="p-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                        <div className="flex gap-2">
                            {/* Voice Button */}
                            {speechSupported && (
                                <button
                                    onClick={toggleListening}
                                    disabled={isLoading}
                                    className={`px-4 py-3 rounded-xl transition-all ${isListening
                                        ? 'bg-red-500 text-white animate-pulse'
                                        : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-600'
                                        } disabled:opacity-50`}
                                >
                                    {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                                </button>
                            )}

                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder={isListening ? t('ai_chat.chat.input_listening') : t('ai_chat.chat.input_placeholder')}
                                className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50"
                                disabled={isLoading}
                                dir="auto"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-4 py-3 rounded-xl hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50 disabled:hover:scale-100 md:w-auto"
                            >
                                <Send size={20} />
                            </button>
                        </div>
                        <div className="text-center mt-2">
                            <p className="text-[10px] text-slate-400">
                                {t('ai_chat.chat.powered_by')} • {speechSupported ? t('ai_chat.chat.voice_enabled') : t('ai_chat.chat.voice_unsupported')}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
