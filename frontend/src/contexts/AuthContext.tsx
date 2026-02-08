'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, UserType, AuthToken, getStoredAuthToken, saveAuthToken, clearAuthToken, mockLogin, realRegister, SignupData, getCurrentJWTToken } from '@/lib/auth';

interface RegisterData {
  fullName: string;
  email: string;
  password: string;
  userType: UserType;
  companyName: string;
  companyDomain?: string;
  role?: 'recruiter' | 'hiring_manager' | 'team_lead' | 'hr';
  interviewType?: 'behavioral' | 'technical' | 'coding' | 'system_design';
  jobRoleName?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (userData: RegisterData) => Promise<{ success: boolean; error?: string; message?: string }>;
  logout: () => void;
  updateUser: (updates: Partial<User>) => void;
  getToken: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedAuth = getStoredAuthToken();
        if (storedAuth) {
          setUser(storedAuth.user);
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (usernameOrEmail: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      setIsLoading(true);
      const authToken = await mockLogin(usernameOrEmail, password);
      
      if (!authToken) {
        return { success: false, error: 'Invalid username/email or password' };
      }

      // Save to localStorage
      saveAuthToken(authToken);
      setUser(authToken.user);
      
      return { success: true };
    } catch (error) {
      return { success: false, error: 'Login failed. Please try again.' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearAuthToken();
    setUser(null);
  };

  const register = async (userData: RegisterData): Promise<{ success: boolean; error?: string; message?: string }> => {
    try {
      setIsLoading(true);

      // Call real registration API
      const result = await realRegister({
        fullName: userData.fullName,
        email: userData.email,
        password: userData.password,
        userType: userData.userType,
        companyName: userData.companyName,
        companyDomain: userData.companyDomain,
        role: userData.role,
        interviewType: userData.interviewType,
        jobRoleName: userData.jobRoleName,
      });

      if (!result.success) {
        return { success: false, error: result.error || 'Registration failed' };
      }

      // Auto-login after successful registration
      const loginResult = await login(userData.email, userData.password);
      if (!loginResult.success) {
        // Registration succeeded but login failed - still consider it a success
        // User will need to login manually
        return { success: true, message: result.message };
      }

      return { success: true, message: result.message };
    } catch (error: any) {
      const errorMessage = error?.message || 'Registration failed. Please try again.';
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  const updateUser = (updates: Partial<User>) => {
    if (!user) return;
    
    const updatedUser = { ...user, ...updates };
    setUser(updatedUser);
    
    // Update stored auth token
    const storedAuth = getStoredAuthToken();
    if (storedAuth) {
      const updatedAuth: AuthToken = {
        ...storedAuth,
        user: updatedUser
      };
      saveAuthToken(updatedAuth);
    }
  };

  const getToken = () => {
    return getCurrentJWTToken();
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updateUser,
    getToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Hook for protecting routes
export function useRequireAuth() {
  const { user, isLoading } = useAuth();
  
  useEffect(() => {
    if (!isLoading && !user) {
      // Redirect to login if not authenticated
      window.location.href = '/login';
    }
  }, [user, isLoading]);

  return { user, isLoading };
}
