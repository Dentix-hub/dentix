// Data is generated from backend constants and Python's Unicode character rules.
import policy from './passwordPolicyData.json';

export const PASSWORD_MIN_LENGTH = policy.minLength;
export const PASSWORD_MAX_LENGTH = policy.maxLength;
const weakPasswords = new Set(policy.weakPasswords);

const trimIdentity = (value) => {
    const chars = Array.from(value);
    while (chars.length && policy.whitespace.includes(chars[0])) chars.shift();
    while (chars.length && policy.whitespace.includes(chars.at(-1))) chars.pop();
    return chars.join('');
};

const normalizeIdentity = (value) => trimIdentity(value).toLowerCase()
    .replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي');

const containsCharacter = (chars, ranges) => chars.some((char) => {
    const code = char.codePointAt(0);
    return ranges.some(([first, last]) => code >= first && code <= last);
});

/** Return a translation-key suffix, or null when the local policy passes.
 * Reset-token forms don't know the username; the server still checks that rule.
 */
export function passwordPolicyError(password, username = '') {
    const chars = Array.from(password);
    if (chars.length < PASSWORD_MIN_LENGTH) return 'password_min_length';
    if (chars.length > PASSWORD_MAX_LENGTH) return 'password_max_length';
    if (!containsCharacter(chars, policy.letterRanges) || !containsCharacter(chars, policy.digitRanges)) {
        return 'password_weak';
    }
    if (username && normalizeIdentity(username) && normalizeIdentity(password) === normalizeIdentity(username)) {
        return 'password_same_as_username';
    }
    if (weakPasswords.has(password.toLowerCase())) return 'password_common';
    return null;
}
