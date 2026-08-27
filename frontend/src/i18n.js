import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import translationAR from './locales/ar/translation.json';
import translationEN from './locales/en/translation.json';
import { patientWorkspaceAR, patientWorkspaceEN } from './locales/patientWorkspace';
import { superAdminAR, superAdminEN } from './locales/superAdmin';
import {
    superAdminImpersonationAR,
    superAdminImpersonationEN,
} from './locales/superAdminImpersonation';

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

const SUPER_ADMIN_NAMESPACES = [
    'system',
    'profile',
    'backup',
    'features',
    'tenant_detail',
    'impersonation',
];

const extendSuperAdminTranslation = (base, extension) => {
    const baseSuperAdmin = base.super_admin || {};
    const extensionSuperAdmin = extension.super_admin || {};

    return {
        ...base,
        super_admin: {
            ...baseSuperAdmin,
            ...extensionSuperAdmin,
            ...Object.fromEntries(
                SUPER_ADMIN_NAMESPACES.map((namespace) => [
                    namespace,
                    {
                        ...(baseSuperAdmin[namespace] || {}),
                        ...(extensionSuperAdmin[namespace] || {}),
                    },
                ]),
            ),
        },
    };
};

const buildTranslation = (base, patientWorkspace, superAdmin, impersonation) =>
    extendSuperAdminTranslation(
        extendSuperAdminTranslation(
            extendTranslation(base, patientWorkspace),
            superAdmin,
        ),
        impersonation,
    );

const resources = {
    ar: {
        translation: buildTranslation(
            translationAR,
            patientWorkspaceAR,
            superAdminAR,
            superAdminImpersonationAR,
        ),
    },
    en: {
        translation: buildTranslation(
            translationEN,
            patientWorkspaceEN,
            superAdminEN,
            superAdminImpersonationEN,
        ),
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
