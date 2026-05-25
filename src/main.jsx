import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FluentProvider, webLightTheme } from '@fluentui/react-components';
import { ToastProvider } from './components/ui/ToastProvider';
import { AuthProvider } from './auth/AuthProvider';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { AgentsList } from './pages/agents/AgentsList';
import { AgentDetail } from './pages/agents/AgentDetail';
import { ConnectionsPage } from './pages/connections/ConnectionsPage';
import { CloudPage } from './pages/cloud/CloudPage';
import { MLPage } from './pages/ml/MLPage';
import { AlertsPage } from './pages/alerts/AlertsPage';
import { UsersPage } from './pages/users/UsersPage';
import { InfraPage } from './pages/infra/InfraPage';
import { SettingsPage } from './pages/settings/SettingsPage';
import { NotFound } from './pages/NotFound';
import './index.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Configure client routes
const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        path: '',
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'agents',
        element: <AgentsList />,
      },
      {
        path: 'agents/:id',
        element: <AgentDetail />,
      },
      {
        path: 'connections',
        element: <ConnectionsPage />,
      },
      {
        path: 'cloud',
        element: <CloudPage />,
      },
      {
        path: 'infra',
        element: <InfraPage />,
      },
      {
        path: 'ml',
        element: <MLPage />,
      },
      {
        path: 'alerts',
        element: <AlertsPage />,
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute adminOnly>
            <UsersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('app')).render(
  <React.StrictMode>
    <FluentProvider theme={webLightTheme} className="min-h-screen bg-brand-bg flex flex-col">
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AuthProvider>
            <RouterProvider router={router} />
          </AuthProvider>
        </ToastProvider>
      </QueryClientProvider>
    </FluentProvider>
  </React.StrictMode>
);
