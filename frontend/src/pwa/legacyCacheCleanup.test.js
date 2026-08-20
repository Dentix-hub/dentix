import { describe, expect, it, vi } from 'vitest';
import { deleteLegacyImageCache, LEGACY_IMAGE_CACHE } from './legacyCacheCleanup';

describe('deleteLegacyImageCache', () => {
    it('deletes only the legacy image cache and remains safe when repeated', async () => {
        const cacheStorage = {
            delete: vi.fn()
                .mockResolvedValueOnce(true)
                .mockResolvedValueOnce(false),
        };

        await expect(deleteLegacyImageCache(cacheStorage)).resolves.toBe(true);
        await expect(deleteLegacyImageCache(cacheStorage)).resolves.toBe(false);
        expect(cacheStorage.delete).toHaveBeenNthCalledWith(1, LEGACY_IMAGE_CACHE);
        expect(cacheStorage.delete).toHaveBeenNthCalledWith(2, LEGACY_IMAGE_CACHE);
    });

    it('does not interrupt startup when Cache Storage is unavailable or rejects', async () => {
        await expect(deleteLegacyImageCache(null)).resolves.toBe(false);

        const unavailableCacheStorage = {
            delete: vi.fn().mockRejectedValue(new Error('Cache Storage unavailable')),
        };
        await expect(deleteLegacyImageCache(unavailableCacheStorage)).resolves.toBe(false);
    });
});
