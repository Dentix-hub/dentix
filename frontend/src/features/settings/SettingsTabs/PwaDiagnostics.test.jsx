import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ar from '../../../locales/ar/translation.json';
import en from '../../../locales/en/translation.json';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => `translated:${key}`,
    }),
}));

import PwaDiagnostics from './PwaDiagnostics';

describe('PwaDiagnostics support surface', () => {
    it('renders the diagnostic rows without exposing secrets or PHI', () => {
        render(<PwaDiagnostics />);

        expect(screen.getByText('translated:settings.pwa.build')).toBeInTheDocument();
        expect(screen.getByText('translated:settings.pwa.commit_sha')).toBeInTheDocument();
        expect(screen.getByText('translated:settings.pwa.service_worker')).toBeInTheDocument();
        expect(screen.getByText('translated:settings.pwa.connection')).toBeInTheDocument();
        expect(screen.getByText('translated:settings.pwa.notification_permission')).toBeInTheDocument();
    });

    it('ships localized diagnostics copy in Arabic and English', () => {
        for (const locale of [ar, en]) {
            expect(locale.settings.pwa.title).toBeTruthy();
            expect(locale.settings.pwa.build).toBeTruthy();
            expect(locale.settings.tabs.pwa).toBeTruthy();
            expect(locale.settings.headers.pwa).toBeTruthy();
        }
    });
});
