import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import ProtectedImage from './ProtectedImage';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key }) }));

describe('ProtectedImage', () => {
    it('loads protected thumbnails from same-origin and shows an accessible placeholder', () => {
        render(<ProtectedImage filePath="/api/v1/upload/drive/uuid/content" thumbnail alt="Synthetic" />);
        const image = screen.getByAltText('Synthetic');
        expect(image.getAttribute('src')).toBe('/api/v1/upload/drive/uuid/content?variant=thumbnail');
        fireEvent.error(image);
        expect(screen.getByRole('img', { name: 'backup.image_unavailable' })).toBeInTheDocument();
    });
});
