import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { useContext } from 'react';
import ProtectedRoute from '@/auth/ProtectedRoute';
import AuthContext from '@/auth/useAuth';

describe('ProtectedRoute', () => {
    function renderWithAuth(authValue, ui) {
        const MockAuthProvider = ({ children }) => (
            <AuthContext.Provider value={authValue}>
                {children}
            </AuthContext.Provider>
        );

        return render(
            <MemoryRouter>
                <MockAuthProvider>
                    <Routes>
                        <Route path="/" element={ui} />
                        <Route path="/login" element={<div>Login Page</div>} />
                        <Route path="/unauthorized" element={<div>Unauthorized</div>} />
                    </Routes>
                </MockAuthProvider>
            </MemoryRouter>
        );
    }

    it('redirects to / when not authenticated', () => {
        renderWithAuth(
            { user: null, loading: false, isAuthenticated: false },
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Login Page')).toBeInTheDocument();
        expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('shows content when authenticated', () => {
        renderWithAuth(
            { user: { role: 'admin' }, loading: false, isAuthenticated: true },
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('redirects to /unauthorized when role not allowed', () => {
        renderWithAuth(
            { user: { role: 'doctor' }, loading: false, isAuthenticated: true },
            <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                <div>Admin Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Unauthorized')).toBeInTheDocument();
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
    });

    it('shows content when role is allowed', () => {
        renderWithAuth(
            { user: { role: 'admin' }, loading: false, isAuthenticated: true },
            <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
                <div>Admin Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Admin Content')).toBeInTheDocument();
    });

    it('shows loading state while auth is loading', () => {
        renderWithAuth(
            { user: null, loading: true, isAuthenticated: false },
            <ProtectedRoute>
                <div>Protected Content</div>
            </ProtectedRoute>
        );

        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
});

describe('AuthContext', () => {
    it('provides auth context to children', () => {
        const TestConsumer = () => {
            const auth = useContext(AuthContext);
            return <div data-testid="auth-data">{JSON.stringify(auth)}</div>;
        };

        render(
            <MemoryRouter>
                <AuthContext.Provider value={{ user: { role: 'admin' }, loading: false, isAuthenticated: true }}>
                    <TestConsumer />
                </AuthContext.Provider>
            </MemoryRouter>
        );

        const authData = JSON.parse(screen.getByTestId('auth-data').textContent);
        expect(authData.isAuthenticated).toBe(true);
        expect(authData.user.role).toBe('admin');
    });
});

