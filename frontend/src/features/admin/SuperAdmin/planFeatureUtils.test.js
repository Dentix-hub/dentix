import { expect, it } from 'vitest';
import { parseFeatures, serializeFeatures } from './planFeatureUtils';
it('preserves explicit false grants when editing an object policy', () => {
    const original='{"clinical":true,"inventory":false}';
    const parsed=parseFeatures(original);
    const saved=JSON.parse(serializeFeatures(parsed.keys,parsed.custom,original));
    expect(saved).toEqual({clinical:true,inventory:false});
});
it('keeps legacy array policy representation compatible', () => {
    expect(JSON.parse(serializeFeatures(['clinical'],'','["clinical"]'))).toEqual(['clinical']);
});
it('does not treat string booleans as enabled grants', () => {
    expect(parseFeatures('{"clinical":"false","inventory":true}').keys).toEqual(['inventory']);
});
it('changes only the selected grant and retains other explicit false values', () => {
    expect(JSON.parse(serializeFeatures(['clinical','inventory'],'','{"clinical":true,"inventory":false,"billing":false}'))).toEqual({clinical:true,inventory:true,billing:false});
});
it('does not convert malformed custom alias values into a true grant while saving', () => {
    const original = '{"clinical":true,"financial_reports":"false"}';
    const parsed = parseFeatures(original);
    expect(parsed.custom).toBe('');
    expect(JSON.parse(serializeFeatures(parsed.keys, parsed.custom, original))).toEqual({ clinical: true, financial_reports: false });
});
