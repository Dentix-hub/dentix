
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import translationAR from './locales/ar/translation.json';
import translationEN from './locales/en/translation.json';

// the translations
const resources = {
    ar: {
        translation: translationAR
    },
    en: {
        translation: translationEN
    }
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next) // passes i18n down to react-i18next
    .init({
        resources,
        fallbackLng: 'ar', // Default language is Arabic
        supportedLngs: ['ar', 'en'], // Supported languages

        detection: {
            order: ['localStorage', 'htmlTag', 'path', 'subdomain'],
            caches: ['localStorage'],
        },

        interpolation: {
            escapeValue: false // react already safes from xss
        }
    });

export default i18n;
