import { apiGet, apiPost } from "./client";

// Cases
export const listCases = () => apiGet("/cases");
export const getCaseById = (id) => apiGet(`/cases/${id}`);

// Dialogue
export const startDialogue = () => apiGet("/dialogue/start");

// ✅ GÜNCELLENDİ: İsmi 'sendChatMessage' oldu ve 'session_id' eklendi
export const sendChatMessage = (caseId, message, mode="hint", userLevel="beginner", language="en", session_id = null) =>
  apiPost(`/dialogue/${caseId}/chat`, { 
    message, 
    mode, 
    userLevel, 
    language,
    session_id // <-- Kritik ekleme: Backend'e hangi sohbette olduğumuzu söyler
  });

// ✅ ANSWER
export const submitAnswer = (
  sessionId,
  selectedIndex,
  mode = "explain",
  userLevel = "beginner",
  language = "en"
) => apiPost(`/dialogue/${sessionId}/answer`, { selectedIndex, mode, userLevel, language });

// User Stats & Progress
export const getUserStats = () => apiGet("/user/stats");
export const getCaseProgress = () => apiGet("/user/progress");
export const getChatHistory = () => apiGet("/user/history");

// Belirli bir oturumun mesajlarını çeker
export const getSessionMessages = (session_id) => apiGet(`/dialogue/history/${session_id}`);