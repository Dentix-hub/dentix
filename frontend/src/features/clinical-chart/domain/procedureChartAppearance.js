import { CANONICAL_PROCEDURES_BY_CODE } from './catalogDefinitions';
import {
    resolveMarkerPaletteColor,
    resolvePaletteColor,
} from './procedureChartPalette';
import { VISUAL_RULE_REGISTRY } from './visualRuleRegistry';

/**
 * Canonical 9 procedure chart appearance templates (Architecture A2).
 * `PROS_DENTURE` is deliberately excluded because it has no visual rule.
 */
export const CHART_APPEARANCE_TEMPLATES = Object.freeze([
    Object.freeze({
        template: 'REST_COMPOSITE',
        labelAr: 'حشوة سطحية',
        labelEn: 'Surface filling',
        glyphType: 'surface',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'ENDO_RCT',
        labelAr: 'علاج عصب',
        labelEn: 'Root canal',
        glyphType: 'root',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'PROS_CROWN',
        labelAr: 'تاج',
        labelEn: 'Crown',
        glyphType: 'crown',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'PROS_BRIDGE',
        labelAr: 'جسر',
        labelEn: 'Bridge unit',
        glyphType: 'bridge',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'IMPLANT_FIXTURE',
        labelAr: 'زرعة',
        labelEn: 'Implant',
        glyphType: 'implant-fixture',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'IMPLANT_CROWN',
        labelAr: 'تاج زرعة',
        labelEn: 'Implant crown',
        glyphType: 'implant-crown',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'SURG_EXTRACTION',
        labelAr: 'خلع',
        labelEn: 'Extraction',
        glyphType: 'extraction',
        isRenderableCanonical: true,
    }),
    Object.freeze({
        template: 'MARKER',
        labelAr: 'علامة على السن',
        labelEn: 'Tooth marker',
        glyphType: 'marker',
        isRenderableCanonical: false,
    }),
    Object.freeze({
        template: 'NONE',
        labelAr: 'بدون ظهور على الرسم',
        labelEn: 'Billing only',
        glyphType: 'none',
        isRenderableCanonical: false,
    }),
]);

export const CHART_APPEARANCE_TEMPLATES_BY_KEY = Object.freeze(
    Object.fromEntries(CHART_APPEARANCE_TEMPLATES.map((item) => [item.template, item])),
);

export const RENDERABLE_CHART_TEMPLATE_KEYS = Object.freeze(
    CHART_APPEARANCE_TEMPLATES
        .filter((item) => item.isRenderableCanonical)
        .map((item) => item.template),
);

const RENDERABLE_TEMPLATE_SET = new Set(RENDERABLE_CHART_TEMPLATE_KEYS);

/**
 * U4C #5: New procedures default to `MARKER` + no color (`null`) so they are
 * visible on the dental chart by default unless the user selects another option.
 */
export const NEW_PROCEDURE_DEFAULT_CHART_STYLE = Object.freeze({
    template: 'MARKER',
    color_key: null,
});

/**
 * Ordered keyword table for suggesting a chart appearance template (U4C #3).
 * Specific patterns MUST precede general patterns:
 * - `عصب|قناة|root canal|rct` -> `ENDO_RCT` BEFORE `حشو|كومبوزيت|filling|composite` -> `REST_COMPOSITE`
 *   so that `"حشو عصب"` suggests `ENDO_RCT`.
 * - `تاج زرعة|implant crown` -> `IMPLANT_CROWN` BEFORE `كراون|تاج|crown` and `زرع|implant`.
 */
export const PROCEDURE_TEMPLATE_SUGGESTION_RULES = Object.freeze([
    Object.freeze({
        template: 'ENDO_RCT',
        keywords: Object.freeze(['عصب', 'قناة', 'root canal', 'rct']),
    }),
    Object.freeze({
        template: 'REST_COMPOSITE',
        keywords: Object.freeze(['حشو', 'كومبوزيت', 'كمبوزيت', 'filling', 'composite']),
    }),
    Object.freeze({
        template: 'IMPLANT_CROWN',
        keywords: Object.freeze(['تاج زرعة', 'تاج زرع', 'implant crown']),
    }),
    Object.freeze({
        template: 'PROS_CROWN',
        keywords: Object.freeze(['كراون', 'تاج', 'طربوش', 'crown']),
    }),
    Object.freeze({
        template: 'PROS_BRIDGE',
        keywords: Object.freeze(['جسر', 'bridge']),
    }),
    Object.freeze({
        template: 'IMPLANT_FIXTURE',
        keywords: Object.freeze(['زرع', 'implant']),
    }),
    Object.freeze({
        template: 'SURG_EXTRACTION',
        keywords: Object.freeze(['خلع', 'extraction']),
    }),
]);

/**
 * Returns a template suggestion for a procedure name or procedure record,
 * or `null` if the procedure already has a style or allowlist code, or no keyword matches.
 * Never auto-applies or mutates anything.
 */
export const suggestProcedureChartTemplate = (procedureOrName) => {
    if (!procedureOrName) return null;

    if (typeof procedureOrName === 'object') {
        const hasStyle = Boolean(procedureOrName.chart_style?.template);
        const hasAllowlistCode = Boolean(procedureOrName.canonical_code);
        if (hasStyle || hasAllowlistCode) {
            return null;
        }
    }

    const rawName = typeof procedureOrName === 'string'
        ? procedureOrName
        : String(procedureOrName.name || '');
    const normalized = rawName.trim().toLowerCase();
    if (!normalized) return null;

    for (const rule of PROCEDURE_TEMPLATE_SUGGESTION_RULES) {
        const matchedKeyword = rule.keywords.find((kw) => normalized.includes(kw.toLowerCase()));
        if (matchedKeyword) {
            const meta = CHART_APPEARANCE_TEMPLATES_BY_KEY[rule.template];
            return Object.freeze({
                template: rule.template,
                labelAr: meta.labelAr,
                labelEn: meta.labelEn,
                matchedKeyword,
            });
        }
    }

    return null;
};

/**
 * Resolves the preview fill and stroke colors for a given `(template, colorKey)` pair.
 */
export const resolveTemplatePreviewColors = (template, colorKey = null) => {
    if (!template || template === 'NONE') {
        return { fill: 'transparent', stroke: '#94a3b8', paletteSwatch: null };
    }

    if (template === 'MARKER') {
        const swatch = resolveMarkerPaletteColor(colorKey);
        return {
            fill: swatch.fill,
            stroke: swatch.stroke,
            paletteSwatch: swatch,
        };
    }

    const explicitSwatch = resolvePaletteColor(colorKey);
    if (explicitSwatch) {
        return {
            fill: explicitSwatch.fill,
            stroke: explicitSwatch.stroke,
            paletteSwatch: explicitSwatch,
        };
    }

    const rule = VISUAL_RULE_REGISTRY.procedure?.[template];
    if (rule?.presentation) {
        return {
            fill: rule.presentation.fill || '#ede9fe',
            stroke: rule.presentation.stroke || '#475569',
            paletteSwatch: null,
        };
    }

    return { fill: '#2563eb', stroke: '#1d4ed8', paletteSwatch: null };
};

/**
 * Computes the effective launcher behavior for a clinic procedure (U4C #4):
 * - `effectiveChartTemplate` = `chart_style.template` (if renderable) ?? allowlist `canonical_code`.
 * - `MARKER` items allow `['tooth', 'surface']` targets and show their palette swatch on the card.
 * - "Billing only" tag is shown only when the effective template is `NONE`/absent AND there is no allowlist code.
 * - `canonical_code` (`code`) remains allowlist-only for Flow A / native link validation.
 */
export const resolveEffectiveProcedureChartBehavior = (proc) => {
    const allowlistCode = proc?.canonical_code || null;
    const rawStyleTemplate = proc?.chart_style?.template || null;
    const rawColorKey = proc?.chart_style?.color_key || null;

    const isRenderableStyle = Boolean(
        rawStyleTemplate && RENDERABLE_TEMPLATE_SET.has(rawStyleTemplate),
    );
    const isMarkerStyle = rawStyleTemplate === 'MARKER';
    const isNoneStyle = rawStyleTemplate === 'NONE';

    // Effective canonical template for target kinds, requires_lab, and category:
    // renderable chart_style.template ?? allowlist canonical_code
    const effectiveRenderableCode = isRenderableStyle
        ? rawStyleTemplate
        : (!isMarkerStyle && !isNoneStyle ? allowlistCode : null);

    const canonicalDef = effectiveRenderableCode
        ? CANONICAL_PROCEDURES_BY_CODE.get(effectiveRenderableCode)
        : (allowlistCode ? CANONICAL_PROCEDURES_BY_CODE.get(allowlistCode) : null);

    let allowed_target_kinds = ['tooth'];
    let requires_lab = false;
    let category = 'clinic';

    if (isMarkerStyle) {
        allowed_target_kinds = ['tooth', 'surface'];
        requires_lab = false;
        category = canonicalDef?.category || 'clinic';
    } else if (canonicalDef) {
        allowed_target_kinds = canonicalDef.allowed_target_kinds || ['tooth'];
        requires_lab = Boolean(canonicalDef.requires_lab);
        category = canonicalDef.category || 'clinic';
    }

    // "billing only" tag: shown only when the effective template is NONE/absent AND there is no allowlist code
    const effectiveTemplate = isRenderableStyle
        ? rawStyleTemplate
        : (isMarkerStyle ? 'MARKER' : (isNoneStyle ? 'NONE' : allowlistCode));
    const showBillingOnlyTag = (!effectiveTemplate || effectiveTemplate === 'NONE') && !allowlistCode;
    const hasChartMapping = !showBillingOnlyTag;

    // Swatch shown on the launcher card when the procedure has a palette swatch (or MARKER default swatch)
    let paletteSwatch = null;
    if (!isNoneStyle) {
        if (rawColorKey) {
            paletteSwatch = resolvePaletteColor(rawColorKey);
        } else if (isMarkerStyle) {
            paletteSwatch = resolveMarkerPaletteColor(null);
        }
    }

    return {
        allowlistCode,
        styleTemplate: rawStyleTemplate,
        styleColorKey: paletteSwatch?.key || resolvePaletteColor(rawColorKey)?.key || null,
        effectiveTemplate,
        effectiveRenderableCode,
        allowed_target_kinds,
        requires_lab,
        category,
        hasChartMapping,
        showBillingOnlyTag,
        paletteSwatch,
    };
};
