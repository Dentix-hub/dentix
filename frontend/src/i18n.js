import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import translationAR from './locales/ar/translation.json';
import translationEN from './locales/en/translation.json';
import { patientWorkspaceAR, patientWorkspaceEN } from './locales/patientWorkspace';

const extendTranslation = (base, extension) => ({
    ...base,
    common: {
        ...(base.common || {}),
        ...(extension.common || {}),
    },
    patients: {
        ...(base.patients || {}),
        ...(extension.patients || {}),
    },
});

const resources = {
    ar: {
        translation: extendTranslation(translationAR, patientWorkspaceAR),
    },
    en: {
        translation: extendTranslation(translationEN, patientWorkspaceEN),
    },
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        fallbackLng: 'ar',
        supportedLngs: ['ar', 'en'],
        detection: {
            order: ['localStorage', 'htmlTag', 'path', 'subdomain'],
            caches: ['localStorage'],
        },
        interpolation: {
            escapeValue: false,
        },
    });

export default i18n;
