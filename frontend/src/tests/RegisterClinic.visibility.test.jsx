import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RegisterClinic from '../pages/RegisterClinic';
import { registerClinic } from '../api';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key }) }));
vi.mock('../api', () => ({ registerClinic: vi.fn() }));

describe('registration password visibility', () => {
    it('reveals both fields without submitting', () => {
        const { container } = render(<MemoryRouter><RegisterClinic /></MemoryRouter>);
        expect(container.querySelectorAll('input[type="password"]')).toHaveLength(2);
        fireEvent.click(screen.getByRole('button', { name: 'auth.show_password' }));
        expect(screen.getByRole('button', { name: 'auth.hide_password' })).toHaveAttribute('aria-pressed', 'true');
        expect(container.querySelectorAll('input[type="password"]')).toHaveLength(0);
        expect(registerClinic).not.toHaveBeenCalled();
    });
});
