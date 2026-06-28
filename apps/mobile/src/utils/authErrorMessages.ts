import { ApiError } from '../services/api';

const MIN_PASSWORD_LENGTH = 8;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const loginValidationMessage = (email: string, password: string) => {
  if (!email.trim()) {
    return 'Enter your email address.';
  }

  if (!EMAIL_PATTERN.test(email.trim())) {
    return 'Enter a valid email address.';
  }

  if (!password) {
    return 'Enter your password.';
  }

  return null;
};

export const signupValidationMessage = (
  fullName: string,
  email: string,
  password: string
) => {
  if (fullName.trim().length < 2) {
    return 'Enter your full name.';
  }

  if (!email.trim()) {
    return 'Enter your email address.';
  }

  if (!EMAIL_PATTERN.test(email.trim())) {
    return 'Enter a valid email address.';
  }

  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }

  return null;
};

export const loginErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Email or password is incorrect.';
    }

    if (error.status === 403) {
      return 'This account is inactive. Contact support for help.';
    }

    if (error.status === 422) {
      return 'Check your email and password, then try again.';
    }
  }

  return connectionErrorMessage(error, 'Could not sign in. Try again.');
};

export const signupErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 409) {
      return 'An account with this email already exists. Sign in or reset your password.';
    }

    if (error.status === 422) {
      return 'Check your name, email, and password, then try again.';
    }
  }

  return connectionErrorMessage(error, 'Could not create account. Try again.');
};

const connectionErrorMessage = (error: unknown, fallbackMessage: string) => {
  if (error instanceof TypeError) {
    return 'Could not reach the server. Check your connection and try again.';
  }

  return fallbackMessage;
};
