import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useUIStore = create(
    persist(
        (set) => ({
            darkMode: false,
            sidebarOpen: false,

            toggleDarkMode: () => set((state) => {
                const newMode = !state.darkMode;
                if (newMode) {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                }
                return { darkMode: newMode };
            }),

            setDarkMode: (isDark) => set(() => {
                if (isDark) {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                }
                return { darkMode: isDark };
            }),

            toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
            setSidebarOpen: (isOpen) => set({ sidebarOpen: isOpen }),
        }),
        {
            name: 'ui-storage', // unique name
            partialize: (state) => ({ darkMode: state.darkMode }), // Only persist dark mode
        }
    )
);
