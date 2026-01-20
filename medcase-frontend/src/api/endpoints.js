import { apiGet, apiPost } from "./client";

// Cases
export const listCases = () => apiGet("/cases");
export const getCaseById = (id) => apiGet(`/cases/${id}`);

// Dialogue
export const startDialogue = () => apiGet("/dialogue/start");

// ✅ CHAT: artık mode/userLevel/language gönderiyoruz
export const chatDialogue = (caseId, message, mode="hint", userLevel="beginner", language="tr") =>
  apiPost(`/dialogue/${caseId}/chat`, { message, mode, userLevel, language });


// ✅ ANSWER: zaten doğru
export const submitAnswer = (
  sessionId,
  selectedIndex,
  mode = "explain",
  userLevel = "beginner",
  language = "en"
) => apiPost(`/dialogue/${sessionId}/answer`, { selectedIndex, mode, userLevel, language });
