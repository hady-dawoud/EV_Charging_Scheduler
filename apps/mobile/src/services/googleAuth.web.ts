import { GOOGLE_WEB_CLIENT_ID } from '../config/google';

type GoogleCredentialResponse = {
  credential?: string;
};

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: {
          initialize: (config: {
            client_id: string;
            callback: (response: GoogleCredentialResponse) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
            ux_mode?: 'popup' | 'redirect';
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, unknown>
          ) => void;
        };
      };
    };
  }
}

const GOOGLE_SCRIPT_ID = 'google-identity-services-script';
const GOOGLE_MODAL_ID = 'google-signin-modal';
const GOOGLE_BUTTON_ID = 'google-signin-button';

const loadGoogleIdentityScript = async () => {
  if (window.google?.accounts?.id) {
    return;
  }

  const existingScript = document.getElementById(GOOGLE_SCRIPT_ID);

  if (existingScript) {
    await new Promise<void>((resolve, reject) => {
      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener(
        'error',
        () => reject(new Error('Google script failed to load.')),
        { once: true }
      );
    });
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.id = GOOGLE_SCRIPT_ID;
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Google script failed to load.'));
    document.head.appendChild(script);
  });
};

const removeGoogleModal = () => {
  document.getElementById(GOOGLE_MODAL_ID)?.remove();
};

const createGoogleModal = (onCancel: () => void) => {
  removeGoogleModal();

  const overlay = document.createElement('div');
  overlay.id = GOOGLE_MODAL_ID;
  overlay.style.position = 'fixed';
  overlay.style.inset = '0';
  overlay.style.zIndex = '99999';
  overlay.style.background = 'rgba(0,0,0,0.72)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.padding = '24px';

  const card = document.createElement('div');
  card.style.width = 'min(360px, 100%)';
  card.style.border = '1px solid rgba(255,255,255,0.14)';
  card.style.borderRadius = '20px';
  card.style.background = '#101214';
  card.style.padding = '24px';
  card.style.boxShadow = '0 24px 80px rgba(0,0,0,0.45)';
  card.style.textAlign = 'center';

  const title = document.createElement('div');
  title.textContent = 'Continue with Google';
  title.style.color = '#ffffff';
  title.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, sans-serif';
  title.style.fontSize = '18px';
  title.style.fontWeight = '700';
  title.style.marginBottom = '8px';

  const subtitle = document.createElement('div');
  subtitle.textContent = 'Use the secure Google button below to sign in.';
  subtitle.style.color = '#9ca3af';
  subtitle.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, sans-serif';
  subtitle.style.fontSize = '13px';
  subtitle.style.marginBottom = '20px';

  const buttonHost = document.createElement('div');
  buttonHost.id = GOOGLE_BUTTON_ID;
  buttonHost.style.display = 'flex';
  buttonHost.style.justifyContent = 'center';
  buttonHost.style.marginBottom = '18px';

  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.textContent = 'Cancel';
  cancel.style.border = '1px solid rgba(255,255,255,0.14)';
  cancel.style.borderRadius = '12px';
  cancel.style.background = 'rgba(255,255,255,0.04)';
  cancel.style.color = '#e5e7eb';
  cancel.style.padding = '10px 16px';
  cancel.style.cursor = 'pointer';
  cancel.onclick = onCancel;

  card.appendChild(title);
  card.appendChild(subtitle);
  card.appendChild(buttonHost);
  card.appendChild(cancel);
  overlay.appendChild(card);
  document.body.appendChild(overlay);

  return buttonHost;
};

export const signInWithGoogle = async (): Promise<string> => {
  await loadGoogleIdentityScript();

  if (!window.google?.accounts?.id) {
    throw new Error('Google Identity Services is unavailable.');
  }

  return new Promise<string>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      removeGoogleModal();
      reject(new Error('Google sign-in timed out.'));
    }, 120000);

    const finish = (idToken: string) => {
      window.clearTimeout(timeout);
      removeGoogleModal();
      resolve(idToken);
    };

    const fail = (error: Error) => {
      window.clearTimeout(timeout);
      removeGoogleModal();
      reject(error);
    };

    const buttonHost = createGoogleModal(() => {
      fail(new Error('Google sign-in was cancelled.'));
    });

    window.google?.accounts?.id?.initialize({
      client_id: GOOGLE_WEB_CLIENT_ID,
      ux_mode: 'popup',
      auto_select: false,
      cancel_on_tap_outside: false,
      callback: (response) => {
        if (response.credential) {
          finish(response.credential);
          return;
        }

        fail(new Error('Google did not return an ID token.'));
      },
    });

    window.google?.accounts?.id?.renderButton(buttonHost, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      shape: 'pill',
      width: 280,
    });
  });
};
