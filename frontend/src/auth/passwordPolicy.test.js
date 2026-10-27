import { describe, it, expect } from 'vitest';
import { passwordPolicyError, PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH } from './passwordPolicy';

describe('shared password policy', () => {
    it('uses the backend limits', () => {
        expect(PASSWORD_MIN_LENGTH).toBe(8);
        expect(PASSWORD_MAX_LENGTH).toBe(72);
    });
    it.each(['abc12345', 'ahmed2024', 'كلمة1234', 'كلمة١٢٣٤', 'abcde²fg', 'ALLCAPS2026'])('accepts %s', (password) => {
        expect(passwordPolicyError(password)).toBeNull();
    });
    it.each([
        ['abcdefgh', 'password_weak'], ['12345678', 'password_weak'],
        ['abc1234', 'password_min_length'], ['a1'.repeat(37), 'password_max_length'],
        ['password1', 'password_common'], ['PASSWORD1', 'password_common'],
        ['11111111a1', 'password_common'], ['qwerty123', 'password_common'],
        ['admin123', 'password_common'], ['dentix123', 'password_common'],
    ])('rejects %s', (password, error) => {
        expect(passwordPolicyError(password)).toBe(error);
    });
    it('matches username normalization, including Arabic and outer whitespace', () => {
        expect(passwordPolicyError('أحمد2024', 'احمد2024')).toBe('password_same_as_username');
        expect(passwordPolicyError('  dr_sara12  ', 'dr_sara12')).toBe('password_same_as_username');
    });
    it('counts Unicode code points, and blocklists only exact lowercase matches', () => {
        expect(passwordPolicyError('a1' + '😀'.repeat(70))).toBeNull();
        expect(passwordPolicyError('a1' + '😀'.repeat(71))).toBe('password_max_length');
        expect(passwordPolicyError(' password1 ')).toBeNull();
    });
});
