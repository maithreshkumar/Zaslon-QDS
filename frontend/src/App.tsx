import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { AlicePortalPage } from './pages/alice/AlicePortalPage';
import { EveLabPage } from './pages/eve/EveLabPage';
import { BobPortalPage } from './pages/bob/BobPortalPage';
import { ResearchDiagnosticsPage } from './pages/research/ResearchDiagnosticsPage';

export const App: React.FC = () => {
  const port = window.location.port;

  const getRootPortal = () => {
    if (port === '5173') {
      return (
        <ProtectedRoute allowedRoles={['ALICE']}>
          <AlicePortalPage />
        </ProtectedRoute>
      );
    }
    if (port === '5174') {
      return (
        <ProtectedRoute allowedRoles={['EVE']}>
          <EveLabPage />
        </ProtectedRoute>
      );
    }
    if (port === '5175') {
      return (
        <ProtectedRoute allowedRoles={['BOB']}>
          <BobPortalPage />
        </ProtectedRoute>
      );
    }
    return <LandingPage />;
  };

  const isPortLocked = port === '5173' || port === '5174' || port === '5175';

  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Port-Aware Root Portal */}
          <Route path="/" element={getRootPortal()} />
          <Route path="/login" element={isPortLocked ? <Navigate to="/" replace /> : <LoginPage />} />
          <Route path="/register" element={isPortLocked ? <Navigate to="/" replace /> : <RegisterPage />} />

          {/* Role-Specific Isolated Portals */}
          <Route
            path="/alice"
            element={
              <ProtectedRoute allowedRoles={['ALICE']}>
                <AlicePortalPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/eve"
            element={
              <ProtectedRoute allowedRoles={['EVE']}>
                <EveLabPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/bob"
            element={
              <ProtectedRoute allowedRoles={['BOB']}>
                <BobPortalPage />
              </ProtectedRoute>
            }
          />

          {/* Research & System Diagnostics */}
          <Route
            path="/research"
            element={
              <ProtectedRoute allowedRoles={['ALICE', 'EVE', 'BOB', 'ADMIN']}>
                <ResearchDiagnosticsPage />
              </ProtectedRoute>
            }
          />

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
