# User Onboarding Dashboard Guide

This guide shows how to create a complete user onboarding dashboard for your voice authentication system.

## 🎯 Dashboard Overview

The dashboard provides:
- **User Registration & Management**
- **Voice Enrollment Tracking** 
- **Authentication History**
- **System Analytics**
- **Real-time Monitoring**

## 🏗️ Architecture Options

### Option 1: Next.js + Tailwind Dashboard (Recommended)

```bash
# Create new Next.js project
npx create-next-app@latest voice-auth-dashboard --typescript --tailwind --eslint
cd voice-auth-dashboard

# Install additional dependencies
npm install @headlessui/react @heroicons/react recharts date-fns uuid
npm install -D @types/uuid
```

### Option 2: React + Material-UI Dashboard

```bash
# Create React app
npx create-react-app voice-auth-dashboard --template typescript
cd voice-auth-dashboard

# Install Material-UI and dependencies
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material @mui/x-charts
npm install axios react-router-dom
```

## 📁 Project Structure

```
voice-auth-dashboard/
├── src/
│   ├── components/
│   │   ├── Dashboard/
│   │   ├── Users/
│   │   ├── Analytics/
│   │   └── Auth/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── utils/
├── public/
└── docs/
```

## 🔧 Core Components Implementation

### 1. API Service Layer

```typescript
// src/services/voiceAuthApi.ts
import axios from 'axios';

const API_BASE_URL = 'https://voiceauth-production.up.railway.app/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for correlation IDs
api.interceptors.request.use((config) => {
  config.headers['X-Call-ID'] = `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  return config;
});

export interface User {
  id: string;
  phone: string;
  enrolledAt: string;
  lastVerified?: string;
  verificationCount: number;
  status: 'enrolled' | 'pending' | 'disabled';
}

export interface EnrollmentRequest {
  userId: string;
  phone: string;
  audioUrl: string;
}

export interface VerificationRequest {
  userId: string;
  listenUrl: string;
}

export interface AuthAttempt {
  id: number;
  success: boolean;
  score?: number;
  createdAt: string;
}

export const voiceAuthApi = {
  // User enrollment
  enrollUser: async (data: EnrollmentRequest) => {
    const response = await api.post('/enroll-user', data);
    return response.data;
  },

  // User verification
  verifyUser: async (data: VerificationRequest) => {
    const response = await api.post('/verify-password', data);
    return response.data;
  },

  // Get user auth history
  getUserAuthHistory: async (userId: string, limit: number = 10) => {
    const response = await api.get(`/users/${userId}/auth-history?limit=${limit}`);
    return response.data;
  },

  // Health check
  getHealthStatus: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // Custom endpoints for dashboard (you'll need to implement these)
  getUsers: async (page: number = 1, limit: number = 20) => {
    // This would be a custom endpoint you add to your service
    const response = await api.get(`/users?page=${page}&limit=${limit}`);
    return response.data;
  },

  getAnalytics: async (timeRange: string = '7d') => {
    // Custom analytics endpoint
    const response = await api.get(`/analytics?range=${timeRange}`);
    return response.data;
  },
};
```

### 2. User Management Dashboard

```typescript
// src/components/Dashboard/UserManagement.tsx
import React, { useState, useEffect } from 'react';
import { User, voiceAuthApi } from '../../services/voiceAuthApi';

interface UserManagementProps {}

const UserManagement: React.FC<UserManagementProps> = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showEnrollModal, setShowEnrollModal] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await voiceAuthApi.getUsers();
      setUsers(response.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEnrollUser = async (userId: string, phone: string, audioUrl: string) => {
    try {
      await voiceAuthApi.enrollUser({ userId, phone, audioUrl });
      await loadUsers(); // Refresh list
      setShowEnrollModal(false);
    } catch (error) {
      console.error('Enrollment failed:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow-lg rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
        <button
          onClick={() => setShowEnrollModal(true)}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Enroll New User
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Phone
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Enrolled At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Verifications
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {user.id.substring(0, 8)}...
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.phone}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    user.status === 'enrolled' 
                      ? 'bg-green-100 text-green-800'
                      : user.status === 'pending'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {user.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(user.enrolledAt).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {user.verificationCount}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => setSelectedUser(user)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    View Details
                  </button>
                  <button className="text-red-600 hover:text-red-900">
                    Disable
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Enrollment Modal */}
      {showEnrollModal && (
        <EnrollmentModal
          onClose={() => setShowEnrollModal(false)}
          onEnroll={handleEnrollUser}
        />
      )}

      {/* User Details Modal */}
      {selectedUser && (
        <UserDetailsModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </div>
  );
};
```

### 3. Analytics Dashboard

```typescript
// src/components/Dashboard/Analytics.tsx
import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';

interface AnalyticsData {
  enrollments: { date: string; count: number }[];
  verifications: { date: string; successful: number; failed: number }[];
  userStatus: { status: string; count: number; color: string }[];
  recentActivity: any[];
}

const Analytics: React.FC = () => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [timeRange, setTimeRange] = useState('7d');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [timeRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      // Mock data - replace with actual API call
      const mockData: AnalyticsData = {
        enrollments: [
          { date: '2024-01-01', count: 12 },
          { date: '2024-01-02', count: 19 },
          { date: '2024-01-03', count: 15 },
          { date: '2024-01-04', count: 25 },
          { date: '2024-01-05', count: 22 },
          { date: '2024-01-06', count: 18 },
          { date: '2024-01-07', count: 28 },
        ],
        verifications: [
          { date: '2024-01-01', successful: 45, failed: 5 },
          { date: '2024-01-02', successful: 52, failed: 8 },
          { date: '2024-01-03', successful: 48, failed: 3 },
          { date: '2024-01-04', successful: 61, failed: 9 },
          { date: '2024-01-05', successful: 55, failed: 6 },
          { date: '2024-01-06', successful: 43, failed: 4 },
          { date: '2024-01-07', successful: 67, failed: 7 },
        ],
        userStatus: [
          { status: 'Enrolled', count: 245, color: '#10B981' },
          { status: 'Pending', count: 23, color: '#F59E0B' },
          { status: 'Disabled', count: 8, color: '#EF4444' },
        ],
        recentActivity: []
      };
      setAnalyticsData(mockData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h2>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2"
        >
          <option value="1d">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Users</p>
              <p className="text-2xl font-semibold text-gray-900">276</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Success Rate</p>
              <p className="text-2xl font-semibold text-gray-900">94.2%</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Today's Verifications</p>
              <p className="text-2xl font-semibold text-gray-900">67</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Avg Response Time</p>
              <p className="text-2xl font-semibold text-gray-900">2.3s</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Enrollment Trend */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Daily Enrollments</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analyticsData?.enrollments}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Verification Success/Failure */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Verification Results</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analyticsData?.verifications}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="successful" fill="#10B981" />
              <Bar dataKey="failed" fill="#EF4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* User Status Distribution */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">User Status Distribution</h3>
        <div className="flex items-center justify-center">
          <ResponsiveContainer width={400} height={300}>
            <PieChart>
              <Pie
                data={analyticsData?.userStatus}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ status, count }) => `${status}: ${count}`}
              >
                {analyticsData?.userStatus.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
```

### 4. Real-time Monitoring

```typescript
// src/components/Dashboard/RealTimeMonitor.tsx
import React, { useState, useEffect } from 'react';
import { voiceAuthApi } from '../../services/voiceAuthApi';

interface SystemHealth {
  status: string;
  components: {
    database: { status: string; details: string };
    embedding_service: { status: string; details: any };
  };
  timestamp: string;
}

const RealTimeMonitor: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Check health every 30 seconds
    const healthInterval = setInterval(checkHealth, 30000);
    checkHealth(); // Initial check

    return () => clearInterval(healthInterval);
  }, []);

  const checkHealth = async () => {
    try {
      const healthData = await voiceAuthApi.getHealthStatus();
      setHealth(healthData);
      setIsConnected(true);
    } catch (error) {
      console.error('Health check failed:', error);
      setIsConnected(false);
    }
  };

  return (
    <div className="bg-white shadow-lg rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">System Monitor</h2>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* System Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="border rounded-lg p-4">
          <h3 className="font-medium text-gray-900">Overall Status</h3>
          <div className="mt-2">
            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              health?.status === 'healthy' 
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {health?.status || 'Unknown'}
            </span>
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <h3 className="font-medium text-gray-900">Database</h3>
          <div className="mt-2">
            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              health?.components?.database?.status === 'healthy'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {health?.components?.database?.status || 'Unknown'}
            </span>
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <h3 className="font-medium text-gray-900">AI Model</h3>
          <div className="mt-2">
            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              health?.components?.embedding_service?.status === 'healthy'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {health?.components?.embedding_service?.status || 'Unknown'}
            </span>
          </div>
        </div>
      </div>

      {/* Recent Activity Log */}
      <div className="border rounded-lg">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h3 className="font-medium text-gray-900">Recent Activity</h3>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {logs.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              No recent activity
            </div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="px-4 py-3 border-b border-gray-100 last:border-b-0">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm text-gray-900">{log.message}</p>
                    <p className="text-xs text-gray-500">{log.timestamp}</p>
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    log.level === 'error' 
                      ? 'bg-red-100 text-red-800'
                      : log.level === 'warning'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {log.level}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default RealTimeMonitor;
```

## 🚀 Deployment Instructions

### 1. Deploy Dashboard to Vercel

```bash
# Build and deploy
npm run build
npx vercel --prod

# Or using Vercel CLI
vercel init
vercel --prod
```

### 2. Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=https://voiceauth-production.up.railway.app/api/v1
NEXT_PUBLIC_VAPI_PUBLIC_KEY=your-vapi-public-key
VAPI_PRIVATE_KEY=your-vapi-private-key
```

### 3. Custom Domain Setup

1. **Add domain** in Vercel dashboard
2. **Configure DNS** to point to Vercel
3. **SSL Certificate** automatically provisioned

## 📱 Mobile Dashboard (Optional)

### React Native Expo Setup

```bash
npx create-expo-app VoiceAuthDashboard --template
cd VoiceAuthDashboard

# Install dependencies
npx expo install expo-av expo-permissions
npm install @react-navigation/native @react-navigation/stack
npm install react-native-chart-kit react-native-svg
```

## 🔐 Authentication & Security

### Admin Authentication

```typescript
// src/hooks/useAuth.ts
import { useState, useEffect } from 'react';

interface User {
  id: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('auth_token');
    if (token) {
      validateToken(token);
    } else {
      setLoading(false);
    }
  }, []);

  const validateToken = async (token: string) => {
    try {
      // Validate token with your auth service
      const response = await fetch('/api/auth/validate', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        localStorage.removeItem('auth_token');
      }
    } catch (error) {
      console.error('Token validation failed:', error);
      localStorage.removeItem('auth_token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (response.ok) {
      const { token, user } = await response.json();
      localStorage.setItem('auth_token', token);
      setUser(user);
      return true;
    }
    return false;
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
  };

  return { user, loading, login, logout };
};
```

## 📊 Key Dashboard Features

### ✅ Implemented Features
- **User Management** - View, enroll, disable users
- **Real-time Analytics** - Charts, metrics, trends  
- **System Monitoring** - Health checks, logs
- **Authentication History** - Per-user verification logs
- **Responsive Design** - Mobile-friendly interface

### 🔄 Advanced Features (Optional)
- **Bulk User Operations** - CSV import/export
- **Advanced Filtering** - Search, sort, filter users
- **Webhook Management** - Configure VAPI webhooks
- **Audit Logs** - Track admin actions
- **API Key Management** - Rotate service keys
- **Alerting System** - Email/SMS notifications

Your voice authentication dashboard is now ready for production use! 🎉