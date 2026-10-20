import { API_URL } from '@/api';

/**
 * Join base + path safely without touching protocol slashes or corrupting origins.
 */
export const buildAttachmentUrl = (filePath) => {
    if (!filePath) return '';
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) return filePath;
    if (filePath.includes('http://') || filePath.includes('https://')) {
        const httpIdx = filePath.indexOf('http');
        return filePath.substring(httpIdx);
    }
    const base = (API_URL || '').replace(/\/+$/, '');
    const path = String(filePath).replace(/^\/+/, '');
    return `${base}/${path}`;
};

/**
 * Decision PD05 canonical purpose code definitions and human-readable bilingual labels.
 */
export const ATTACHMENT_PURPOSE_OPTIONS = [
    { value: 'PRE_OP_XRAY', labelEn: 'Pre-Op X-Ray', labelAr: 'أشعة قبل العلاج' },
    { value: 'POST_OP_XRAY', labelEn: 'Post-Op X-Ray', labelAr: 'أشعة بعد العلاج' },
    { value: 'WORKING_LENGTH_XRAY', labelEn: 'Working Length X-Ray', labelAr: 'أشعة قياس الطول' },
    { value: 'INTRAORAL_PHOTO', labelEn: 'Intraoral Photo', labelAr: 'صورة داخل الفم' },
    { value: 'EXTRAORAL_PHOTO', labelEn: 'Extraoral Photo', labelAr: 'صورة خارج الفم' },
    { value: 'LAB_SCAN', labelEn: 'Lab Scan', labelAr: 'مسح ضوئي للمختبر' },
    { value: 'CONSENT_DOC', labelEn: 'Consent Document', labelAr: 'إقرار موافقة' },
    { value: 'OTHER', labelEn: 'Other', labelAr: 'أخرى' },
];

export const getPurposeLabel = (purposeCode, isArabic = false) => {
    const item = ATTACHMENT_PURPOSE_OPTIONS.find((opt) => opt.value === purposeCode);
    if (!item) return purposeCode || '';
    return isArabic ? item.labelAr : item.labelEn;
};
