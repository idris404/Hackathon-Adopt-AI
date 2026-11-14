// Miroir de backend/app/constants/auth.py. En cas d'écart, le backend a raison.
// À la connexion, seule la longueur maximale est contrôlée : le minimum ne vaut qu'à la création.
export const PASSWORD_MAX_LENGTH = 256
// `detail` renvoyé en 400 : le même pour un email inconnu, un mauvais mot de passe ou un compte désactivé.
export const INVALID_CREDENTIALS_CODE = 'LOGIN_BAD_CREDENTIALS'

export const EMAIL_INVALID_MESSAGE = 'Saisissez une adresse email valide.'
export const PASSWORD_REQUIRED_MESSAGE = 'Saisissez votre mot de passe.'
export const PASSWORD_TOO_LONG_MESSAGE = `Le mot de passe ne peut pas dépasser ${PASSWORD_MAX_LENGTH} caractères.`
export const INVALID_CREDENTIALS_MESSAGE = 'Email ou mot de passe incorrect.'
export const LOGIN_ERROR_MESSAGE = 'Connexion impossible. Réessayez dans un instant.'
export const LOGOUT_ERROR_MESSAGE = 'Déconnexion impossible. Réessayez dans un instant.'
export const SESSION_CHECK_MESSAGE = 'Vérification de la session…'
export const SESSION_ERROR_MESSAGE = 'Impossible de vérifier votre session. Le serveur est peut-être injoignable.'
