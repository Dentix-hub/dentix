export const LEGACY_IMAGE_CACHE = 'images-cache';

export async function deleteLegacyImageCache(cacheStorage = globalThis.caches) {
    if (!cacheStorage || typeof cacheStorage.delete !== 'function') return false;

    try {
        return await cacheStorage.delete(LEGACY_IMAGE_CACHE);
    } catch {
        return false;
    }
}
