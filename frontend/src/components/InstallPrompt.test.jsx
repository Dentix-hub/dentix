import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ar from '../locales/ar/translation.json';
import en from '../locales/en/translation.json';

const pwaMocks = vi.hoisted(() => ({
    setNeedRefresh: vi.fn(),
    updateServiceWorker: vi.fn(),
}));

vi.mock('virtual:pwa-register/react', () => ({
    useRegisterSW: () => ({
        needRefresh: [true, pwaMocks.setNeedRefresh],
        offlineReady: [false, vi.fn()],
        updateServiceWorker: pwaMocks.updateServiceWorker,
    }),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => `translated:${key}`,
    }),
}));

import { InstallPrompt } from './InstallPrompt';

describe('InstallPrompt PWA updates', () => {
    beforeEach(() => {
        pwaMocks.setNeedRefresh.mockClear();
        pwaMocks.updateServiceWorker.mockClear();
    });

    it('asks before replacing the running clinical app and updates only on confirmation', () => {
        render(<InstallPrompt />);

        expect(screen.getByText('translated:pwa.update.title')).toBeInTheDocument();
        expect(screen.getByText('translated:pwa.update.description')).toBeInTheDocument();
        expect(pwaMocks.updateServiceWorker).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'translated:pwa.update.confirm' }));
        expect(pwaMocks.updateServiceWorker).toHaveBeenCalledWith(true);
    });

    it('allows the user to defer the update without reloading active work', () => {
        render(<InstallPrompt />);

        fireEvent.click(screen.getByRole('button', { name: 'translated:pwa.update.later' }));
        expect(pwaMocks.setNeedRefresh).toHaveBeenCalledWith(false);
        expect(pwaMocks.updateServiceWorker).not.toHaveBeenCalled();
    });

    it('ships localized update copy in Arabic and English', () => {
        expect(ar.pwa.update).toEqual({
            title: 'يتوفر إصدار جديد من DENTIX',
            description: 'حدّث عندما تنتهي من حفظ بياناتك الحالية',
            confirm: 'حدّث الآن',
            later: 'لاحقاً',
        });
        expect(en.pwa.update).toEqual({
            title: 'A new DENTIX version is available',
            description: 'Update after saving your current work',
            confirm: 'Update now',
            later: 'Later',
        });
    });
});
