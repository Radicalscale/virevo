import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Safe fetch wrapper that handles response body consumption conflicts with rrweb-recorder
// The rrweb script intercepts fetch and can consume the response body before our code runs
// This wrapper uses XMLHttpRequest as a fallback which isn't intercepted by rrweb
const safeFetch = async (url, options = {}) => {
  // Try using native XMLHttpRequest which rrweb doesn't intercept
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(options.method || 'GET', url, true);
    
    // Set headers
    if (options.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });
    }
    
    // Enable cookies for cross-origin requests
    xhr.withCredentials = options.credentials === 'include';
    
    xhr.onload = function() {
      const responseText = xhr.responseText;
      resolve({
        ok: xhr.status >= 200 && xhr.status < 300,
        status: xhr.status,
        statusText: xhr.statusText,
        text: responseText,
        json: () => {
          try {
            return JSON.parse(responseText);
          } catch (e) {
            throw new Error(`Invalid JSON response: ${responseText}`);
          }
        }
      });
    };
    
    xhr.onerror = function() {
      reject(new Error('Network request failed'));
    };
    
    xhr.ontimeout = function() {
      reject(new Error('Request timeout'));
    };
    
    // Send request body if provided
    if (options.body) {
      xhr.send(options.body);
    } else {
      xhr.send();
    }
  });
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

  const checkAuth = useCallback(async () => {
    try {
      const response = await safeFetch(`${BACKEND_URL}/api/auth/me`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const userData = response.json();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    // Check if user is already logged in
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password, rememberMe = false) => {
    const response = await safeFetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });

    if (!response.ok) {
      let errorMessage = 'Login failed';
      try {
        const errorData = response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        errorMessage = response.text || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = response.json();
    setUser(data.user);
    return data;
  };

  const signup = async (email, password, rememberMe = false) => {
    const response = await safeFetch(`${BACKEND_URL}/api/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });

    if (!response.ok) {
      let errorMessage = 'Signup failed';
      try {
        const errorData = response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        errorMessage = response.text || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = response.json();
    setUser(data.user);
    return data;
  };

  const logout = async () => {
    try {
      await safeFetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      navigate('/login');
    }
  };

  const forgotPassword = async (email) => {
    const response = await safeFetch(`${BACKEND_URL}/api/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      let errorMessage = 'Failed to send reset email';
      try {
        const errorData = response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        errorMessage = response.text || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  };

  const resetPassword = async (token, newPassword) => {
    const response = await safeFetch(`${BACKEND_URL}/api/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token, new_password: newPassword }),
    });

    if (!response.ok) {
      let errorMessage = 'Failed to reset password';
      try {
        const errorData = response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        errorMessage = response.text || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  };

  const value = {
    user,
    loading,
    login,
    signup,
    logout,
    forgotPassword,
    resetPassword,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
