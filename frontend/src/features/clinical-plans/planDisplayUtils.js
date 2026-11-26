import { CANONICAL_PROCEDURES_BY_CODE } from '@/features/clinical-chart/domain/catalogDefinitions';

const DEFAULT_PHASE_NAME_PATTERN = /^phase\s+(\d+)$/i;

/**
 * Localizes persisted default phase names like "Phase 1" while preserving custom phase titles.
 */
export function formatPhaseName(phaseName, t) {
    if (typeof phaseName !== 'string') return '';
    const trimmed = phaseName.trim();
    if (!trimmed) return '';

    const match = trimmed.match(DEFAULT_PHASE_NAME_PATTERN);
    if (match && typeof t === 'function') {
        return t('clinical_plans.phase_n', 'Phase {{n}}', { n: match[1] });
    }
    return trimmed;
}

/**
 * Resolves a human-readable procedure label from a ClinicalWorkItem payload.
 * Prefers explicit display_name/title, then localizes canonical `code`/`procedure_code`,
 * and falls back to a localized item placeholder instead of "undefined".
 */
export function formatWorkItemLabel(workItem, { language = 'en', t, fallbackId } = {}) {
    const explicitLabel = [workItem?.display_name, workItem?.title]
        .find((val) => typeof val === 'string' && val.trim().length > 0);
    if (explicitLabel) {
        return explicitLabel.trim();
    }

    const rawCode = [workItem?.code, workItem?.procedure_code]
        .find((val) => typeof val === 'string' && val.trim().length > 0);
    if (rawCode) {
        const cleanCode = rawCode.trim();
        const catalogDef = CANONICAL_PROCEDURES_BY_CODE.get(cleanCode.toUpperCase());
        if (catalogDef) {
            const isArabic = String(language || '').toLowerCase().startsWith('ar');
            return isArabic ? catalogDef.nameAr : catalogDef.name;
        }
        return cleanCode;
    }

    const itemId = fallbackId ?? workItem?.id;
    if (itemId !== null && itemId !== undefined && itemId !== '') {
        return typeof t === 'function'
            ? t('clinical_plans.item_fallback', 'Item #{{id}}', { id: itemId })
            : `Item #${itemId}`;
    }

    return typeof t === 'function'
        ? t('clinical_plans.unnamed_procedure', 'Procedure')
        : 'Procedure';
}

/**
 * Formats work-item tooth and surface targets, supporting both `surface` and backend `surface_code`.
 */
export function formatWorkItemTargets(targets) {
    if (!Array.isArray(targets)) return '';
    return targets
        .map((tg) => {
            if (!tg?.tooth_key) return '';
            const surface = tg.surface || tg.surface_code;
            return surface ? `${tg.tooth_key} (${surface})` : String(tg.tooth_key);
        })
        .filter(Boolean)
        .join(', ');
}

/**
 * Translates clinical plan or work-item status keys with raw status fallback.
 */
export function formatClinicalPlanStatus(status, t) {
    if (typeof status !== 'string') return '';
    const trimmed = status.trim();
    if (!trimmed) return '';

    const normalized = trimmed.toLowerCase();
    return typeof t === 'function'
        ? t(`clinical_plans.status.${normalized}`, trimmed)
        : trimmed;
}
