let lastSession = null;

export function setLastSession(payload) {
  lastSession = payload;
}

export function getLastSession() {
  return lastSession;
}

export function clearLastSession() {
  lastSession = null;
}
