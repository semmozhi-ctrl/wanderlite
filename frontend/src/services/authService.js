import api, { apiHelpers } from './api';

/**
 * Authentication Service
 * Handles login, signup, logout, and user session management
 */

const AUTH_ENDPOINTS = {
  LOGIN: '/api/auth/login',
  SIGNUP: '/api/auth/signup',
  ME: '/api/auth/me',
  LOGOUT: '/api/auth/logout',
};

// Token management
const TOKEN_KEY = 'token';
const USER_KEY = 'user';

export const authService = {
  /**
   * Login user with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<{success: boolean, user?: object, error?: string}>}
   */
  login: async (email, password) => {
    // Client-side validation
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return { success: false, error: 'Please enter a valid email address' };
    }
    
    if (!password || password.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters' };
    }
    
    try {
      console.debug('[Auth] Posting to', AUTH_ENDPOINTS.LOGIN, 'with email', email);
      const response = await api.post(AUTH_ENDPOINTS.LOGIN, { email, password });
      console.debug('[Auth] Login response:', response.data);
      
      // Store token (support both access_token and token field names)
      const token = response.data.access_token || response.data.token;
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
        
        // Set authorization header for future requests
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Try to fetch user details
        try {
          const userResponse = await api.get(AUTH_ENDPOINTS.ME);
          const user = userResponse.data;
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          return { success: true, user, token };
        } catch (error) {
          // If /me fails, create minimal user object
          const user = { email };
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          return { success: true, user, token };
        }
      }
      
      return { success: false, error: 'Login failed - no token received' };
    } catch (error) {
      return { 
        success: false, 
        error: error.data?.detail || error.message || 'Login failed. Please check your credentials.' 
      };
    }
  },
  
  /**
   * Register new user
   * @param {string} email - User email
   * @param {string} username - Username
   * @param {string} password - User password
   * @returns {Promise<{success: boolean, user?: object, error?: string}>}
   */
  signup: async (email, username, password) => {
    // Client-side validation
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return { success: false, error: 'Please enter a valid email address' };
    }
    
    if (!username || username.length < 2) {
      return { success: false, error: 'Username must be at least 2 characters' };
    }
    
    if (!password || password.length < 6) {
      return { success: false, error: 'Password must be at least 6 characters' };
    }
    
    try {
      const response = await api.post(AUTH_ENDPOINTS.SIGNUP, { email, username, password });
      
      // Store token
      const token = response.data.access_token;
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
        
        // Set authorization header
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Try to fetch user details
        try {
          const userResponse = await api.get(AUTH_ENDPOINTS.ME);
          const user = userResponse.data;
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          return { success: true, user, token };
        } catch (error) {
          // If /me fails, create user object from signup data
          const user = { email, username };
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          return { success: true, user, token };
        }
      }
      
      return { success: false, error: 'Signup failed - no token received' };
    } catch (error) {
      return { 
        success: false, 
        error: error.data?.detail || error.message || 'Signup failed. Please try again.' 
      };
    }
  },
  
  /**
   * Logout current user
   */
  logout: () => {
    // Clear token and user data
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    
    // Remove authorization header
    delete api.defaults.headers.common['Authorization'];
    
    // Optional: Call backend logout endpoint if it exists
    // This is useful for invalidating tokens on the server
    /* try {
      await api.post(AUTH_ENDPOINTS.LOGOUT);
    } catch (error) {
      console.error('Logout API call failed:', error);
    } */
  },
  
  /**
   * Get current user from localStorage
   * @returns {object|null}
   */
  getCurrentUser: () => {
    try {
      const userStr = localStorage.getItem(USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  },
  
  /**
   * Get current auth token
   * @returns {string|null}
   */
  getToken: () => {
    return localStorage.getItem(TOKEN_KEY);
  },
  
  /**
   * Check if user is authenticated
   * @returns {boolean}
   */
  isAuthenticated: () => {
    return !!localStorage.getItem(TOKEN_KEY);
  },
  
  /**
   * Fetch current user details from server
   * @returns {Promise<{success: boolean, user?: object, error?: string}>}
   */
  fetchCurrentUser: async () => {
    try {
      const response = await api.get(AUTH_ENDPOINTS.ME);
      const user = response.data;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return { success: true, user };
    } catch (error) {
      // If fetch fails with 401, clear auth data
      if (error.status === 401) {
        authService.logout();
      }
      return { 
        success: false, 
        error: error.message || 'Failed to fetch user details' 
      };
    }
  },
  
  /**
   * Refresh token (placeholder for future implementation)
   * This would be useful with refresh tokens
   */
  refreshToken: async () => {
    // TODO: Implement refresh token logic if using refresh tokens
    console.warn('Refresh token not implemented');
    return { success: false, error: 'Refresh token not implemented' };
  },
};

// Alternative: Cookie-based authentication
// If you want to use httpOnly cookies instead of localStorage:
/*
export const authServiceWithCookies = {
  login: async (email, password) => {
    try {
      // Set withCredentials to true to send cookies
      const response = await api.post(AUTH_ENDPOINTS.LOGIN, 
        { email, password }, 
        { withCredentials: true }
      );
      
      // Token will be stored in httpOnly cookie by the server
      // No need to manually store it
      
      const user = response.data.user;
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return { success: true, user };
    } catch (error) {
      return { 
        success: false, 
        error: error.data?.detail || 'Login failed' 
      };
    }
  },
  
  logout: async () => {
    try {
      await api.post(AUTH_ENDPOINTS.LOGOUT, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      localStorage.removeItem(USER_KEY);
    }
  },
  
  // ... other methods adapted for cookie-based auth
};
*/

export default authService;
