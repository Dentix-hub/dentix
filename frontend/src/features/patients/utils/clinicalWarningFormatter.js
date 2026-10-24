/**
 * Utility for formatting clinical workspace warnings into plain language.
 *
 * Requirements (D4 / A5):
 * - Translates technical backend warning codes into clear Arabic / English sentences.
 * - Retains technical codes strictly for collapsed admin details.
 * - Handles unknown or future warning codes gracefully with a generic friendly message.
 */

export const KNOWN_CLINICAL_WARNING_CODES = [
    'FALLBACK_DATA_ACTIVE',
    'LEGACY_WRITE_COMPATIBILITY_ACTIVE',
    'UNSUPPORTED_CLINICAL_CODE',
    'UNSUPPORTED_RENDERER_TARGET',
    'UNKNOWN_PROCEDURE_CODE',
    'UNKNOWN_TOOTH_STATUS_CONDITION',
    'UNKNOWN_STATUS_CODE',
    'INVALID_PROCEDURE_TYPE',
    'INVALID_STATUS_TYPE',
    'INVALID_TOOTH_NOTATION',
    'INVALID_TOOTH_STATUS_CONDITION_TYPE',
    'MISSING_TOOTH_TARGET',
    'MISSING_PARENT_TREATMENT',
    'PARENT_TREATMENT_ID_MISMATCH',
    'PATIENT_OWNERSHIP_MISMATCH',
    'TENANT_MISMATCH',
    'EXACT_DUPLICATE_RECORD',
    'MALFORMED_LAB_LINK_NOTE',
    'LAB_ORDER_NOT_FOUND',
    'CROSS_PATIENT_LAB_LINK_REJECTED',
    'CROSS_TENANT_LAB_LINK_REJECTED',
    'AMBIGUOUS_MULTIPLE_LAB_ORDERS',
    'AMBIGUOUS_ATTACHMENT_TOOTH_LINK',
    'AMBIGUOUS_ATTACHMENT_TREATMENT_LINK',
    'ATTACHMENT_TREATMENT_NOT_FOUND',
];

export function formatClinicalWarning(warning, t) {
    if (!warning) {
        return {
            friendlyMessage: '',
            technicalCode: '',
            rawMessage: '',
            rawValue: '',
        };
    }

    const code = warning.code || 'GENERIC_UNKNOWN_WARNING';
    const isKnown = KNOWN_CLINICAL_WARNING_CODES.includes(code);
    const key = isKnown
        ? `clinical.warning_messages.${code}`
        : 'clinical.warning_messages.GENERIC_UNKNOWN_WARNING';

    const rawVal = warning.raw_value ?? warning.rawValue ?? warning.value ?? '';
    const displayValue = rawVal || t('clinical.unspecified', 'غير محدد');

    const friendlyMessage = t(key, { value: displayValue });

    return {
        friendlyMessage,
        technicalCode: code,
        rawMessage: warning.message || '',
        rawValue: rawVal,
    };
}
