import { afterEach, describe, expect, it } from 'vitest';
import { detectPlatform } from './platform';

const originalUserAgent = window.navigator.userAgent;

function setUserAgent(ua) {
    Object.defineProperty(window.navigator, 'userAgent', { value: ua, configurable: true });
}

afterEach(() => {
    setUserAgent(originalUserAgent);
    // Remove own-property overrides so prototype getters apply again.
    Reflect.deleteProperty(window.navigator, 'platform');
    Reflect.deleteProperty(window.navigator, 'maxTouchPoints');
});

describe('PWA platform detection', () => {
    it('detects iPhone as ios', () => {
        setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1');
        expect(detectPlatform()).toBe('ios');
    });

    it('detects iPadOS 13+ desktop-mode Safari (MacIntel + touch) as ios', () => {
        setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15');
        Object.defineProperty(window.navigator, 'platform', { value: 'MacIntel', configurable: true });
        Object.defineProperty(window.navigator, 'maxTouchPoints', { value: 5, configurable: true });
        expect(detectPlatform()).toBe('ios');
    });

    it('detects Android as android', () => {
        setUserAgent('Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36');
        expect(detectPlatform()).toBe('android');
    });

    it('detects desktop browsers as desktop', () => {
        setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36');
        expect(detectPlatform()).toBe('desktop');
    });
});
