export type UserType = 'recruiter' | 'candidate' | 'hiring_manager' | 'team_lead' | 'hr' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  userType: UserType;
  role: string;
  firstName?: string;
  lastName?: string;
  organizationId?: string;
  organizationName?: string;
}

export interface AuthToken {
  token: string;
  user: User;
  expiresAt: number; // epoch ms
}

const LOCAL_STORAGE_KEY = 'intervuai_auth_token';

export function getStoredAuthToken(): AuthToken | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthToken;
    if (!parsed || typeof parsed !== 'object') return null;
    if (parsed.expiresAt && Date.now() > parsed.expiresAt) {
      window.localStorage.removeItem(LOCAL_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveAuthToken(authToken: AuthToken): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(authToken));
}

export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(LOCAL_STORAGE_KEY);
}

export async function mockLogin(usernameOrEmail: string, password: string): Promise<AuthToken | null> {
  try {
    const { apiClient } = await import('./api');
    const response = await apiClient.login({
      email: usernameOrEmail,
      password: password,
    });

    if (!response.success) {
      return null;
    }

    // Extract user info from the response
    const userData = response.data.user;
    const user: User = {
      id: userData.id,
      name: `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || userData.email,
      email: userData.email,
      userType: userData.role as UserType,
      role: userData.role,
      firstName: userData.first_name,
      lastName: userData.last_name,
      organizationId: userData.organization_id,
    };

    return {
      token: response.data.access_token,
      user,
      expiresAt: Date.now() + (response.data.expires_in * 1000), // Convert seconds to milliseconds
    };
  } catch (error) {
    console.error('Login error:', error);
    return null;
  }
}

export interface SignupData {
  // Required
  fullName: string;
  email: string;
  password: string;
  userType: UserType;
  companyName: string;
  // Optional
  companyDomain?: string;
  role?: 'recruiter' | 'hiring_manager' | 'team_lead' | 'hr' | 'admin';
  interviewType?: 'behavioral' | 'technical' | 'coding' | 'system_design';
  jobRoleName?: string;
}

export async function realRegister(userData: SignupData): Promise<{ success: boolean; error?: string }> {
  try {
    const { apiClient } = await import('./api');

    // Split fullName into first_name and last_name
    const nameParts = userData.fullName.trim().split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';

    const response = await apiClient.signup({
      company_name: userData.companyName,
      company_domain: userData.companyDomain,
      email: userData.email,
      password: userData.password,
      first_name: firstName,
      last_name: lastName,
      role: userData.role || 'recruiter',
      interview_type: userData.interviewType,
      job_role_name: userData.jobRoleName,
    });

    if (!response.success) {
      return { success: false, error: 'Registration failed' };
    }

    return { success: true };
  } catch (error: any) {
    console.error('Registration error:', error);
    // Try to extract error message from response
    const errorMessage = error?.message || 'Registration failed. Please try again.';
    return { success: false, error: errorMessage };
  }
}

// Keep for backwards compatibility - redirects to realRegister
export async function mockRegister(userData: { fullName: string; email: string; password: string; userType: UserType; companyName?: string; role?: 'recruiter' | 'hiring_manager' | 'team_lead' | 'hr' | 'admin' }): Promise<AuthToken> {
  // If companyName is provided, use realRegister
  if (userData.companyName) {
    const result = await realRegister({
      ...userData,
      companyName: userData.companyName,
    });
    if (!result.success) {
      throw new Error(result.error);
    }
  }

  // Return a temporary token (user will need to login after registration)
  const user: User = {
    id: Math.random().toString(36).slice(2),
    name: userData.fullName,
    email: userData.email,
    userType: userData.userType,
    role: userData.role || 'recruiter',
  };
  return createAuthToken(user);
}

function createAuthToken(user: User): AuthToken {
  const expiresAt = Date.now() + 1000 * 60 * 60 * 24; // 24h
  const token = btoa(`${user.id}:${user.email}:${expiresAt}`);
  return { token, user, expiresAt };
}

export function getCurrentJWTToken(): string | null {
  const stored = getStoredAuthToken();
  return stored?.token ?? null;
}



