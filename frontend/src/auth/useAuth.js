import { createContext, useContext } from 'react';

// Create the context
const AuthContext = createContext(null);

// Named export for the hook
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};

export default AuthContext;
