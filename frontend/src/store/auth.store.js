import { create } from 'zustand';

export const useAuthStore = create((set) => ({
    user: null,
    isAuthLoading: true,
    isAuthenticated: false,
    is2faPending: false,
    tempToken: null,

    // Actions
    setUser: (userData) => set({
        user: userData,
        isAuthenticated: !!userData,
        isAuthLoading: false,
        is2faPending: false,
        tempToken: null
    }),
    setLoading: (isLoading) => set({ isAuthLoading: isLoading }),
    set2faPending: (isPending, tempToken = null) => set({
        is2faPending: isPending,
        tempToken,
        isAuthLoading: false
    }),
    clearAuth: () => set({
        user: null,
        isAuthenticated: false,
        isAuthLoading: false,
        is2faPending: false,
        tempToken: null
    })
}));

export default useAuthStore;
