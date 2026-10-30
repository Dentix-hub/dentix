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

    it('renders pending status placeholder when storageStatus is pending without rendering broken img', () => {
        render(<ProtectedImage filePath="/api/v1/upload/drive/uuid/content" storageStatus="pending" alt="Synthetic" />);
        expect(screen.queryByAltText('Synthetic')).not.toBeInTheDocument();
        expect(screen.getByRole('status', { name: 'backup.image_pending' })).toBeInTheDocument();
    });

    it('recovers from pending to ready at unchanged file path and renders img', () => {
        const { rerender } = render(
            <ProtectedImage filePath="/api/v1/upload/drive/uuid/content" storageStatus="pending" alt="Synthetic" />
        );
        expect(screen.getByRole('status', { name: 'backup.image_pending' })).toBeInTheDocument();

        // Worker completes upload, status updates to ready with identical filePath
        rerender(
            <ProtectedImage filePath="/api/v1/upload/drive/uuid/content" storageStatus="ready" alt="Synthetic" />
        );
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        const image = screen.getByAltText('Synthetic');
        expect(image).toBeInTheDocument();
    });

    it('recovers from error state when retry button is clicked', () => {
        render(<ProtectedImage filePath="/api/v1/upload/drive/uuid/content" alt="Synthetic" />);
        const image = screen.getByAltText('Synthetic');
        fireEvent.error(image);

        const retryBtn = screen.getByRole('button', { name: 'common.retry' });
        expect(retryBtn).toBeInTheDocument();

        fireEvent.click(retryBtn);
        expect(screen.queryByRole('img', { name: 'backup.image_unavailable' })).not.toBeInTheDocument();
        expect(screen.getByAltText('Synthetic')).toBeInTheDocument();
    });

    it('recovers from error state when retryGeneration changes', () => {
        const { rerender } = render(
            <ProtectedImage filePath="/api/v1/upload/drive/uuid/content" retryGeneration={0} alt="Synthetic" />
        );
        const image = screen.getByAltText('Synthetic');
        fireEvent.error(image);
        expect(screen.getByRole('img', { name: 'backup.image_unavailable' })).toBeInTheDocument();

        // Manual refresh clicked in parent
        rerender(
            <ProtectedImage filePath="/api/v1/upload/drive/uuid/content" retryGeneration={1} alt="Synthetic" />
        );
        expect(screen.queryByRole('img', { name: 'backup.image_unavailable' })).not.toBeInTheDocument();
        expect(screen.getByAltText('Synthetic')).toBeInTheDocument();
    });
});
