export const LEGACY_IMAGE_CACHE = 'images-cache';

export async function deleteLegacyImageCache(cacheStorage = globalThis.caches, timeoutMs = 1500) {
    if (!cacheStorage || typeof cacheStorage.delete !== 'function') return false;

    try {
        const deletePromise = cacheStorage.delete(LEGACY_IMAGE_CACHE);
        const timeoutPromise = new Promise((resolve) => setTimeout(() => resolve(false), timeoutMs));
        return await Promise.race([deletePromise, timeoutPromise]);
    } catch {
        return false;
    }
}
