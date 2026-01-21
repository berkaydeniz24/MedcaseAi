import { apiGet, apiPost } from "./client";

// Cases
export const listCases = () => apiGet("/cases");
export const getCaseById = (id) => apiGet(`/cases/${id}`);

// Dialogue
export const startDialogue = () => apiGet("/dialogue/start");

// ✅ CHAT: Varsayılan dil 'en' yapıldı, yapı aynı.
export const chatDialogue = (caseId, message, mode="hint", userLevel="beginner", language="en") =>
  apiPost(`/dialogue/${caseId}/chat`, { message, mode, userLevel, language });


// ✅ ANSWER: Varsayılan dil 'en' yapıldı.
export const submitAnswer = (
  sessionId,
  selectedIndex,
  mode = "explain",
  userLevel = "beginner",
  language = "en"
) => apiPost(`/dialogue/${sessionId}/answer`, { selectedIndex, mode, userLevel, language });

// Kullanıcının doğru/yanlış sayılarını çeker
export const getUserStats = () => apiGet("/user/stats");

// Hangi vakanın hangi durumda olduğunu (new, in_progress, solved) çeker
export const getCaseProgress = () => apiGet("/user/progress");