import { apiGet, apiPost, apiPut } from "./client";

// Cases
export const listCases = () => apiGet("/cases");
export const getCaseById = (id) => apiGet(`/cases/${id}`);
export const getDailyCase = () => apiGet("/cases/daily");

// Dialogue
export const startDialogue = (specialty = null, caseId = null) => {
  const params = new URLSearchParams();
  // caseId (ör. Günün Vakası) belirtilmişse specialty yok sayılır — backend
  // ile aynı öncelik kuralı.
  if (caseId) params.set("case_id", caseId);
  else if (specialty) params.set("specialty", specialty);
  const qs = params.toString();
  return apiGet(qs ? `/dialogue/start?${qs}` : "/dialogue/start");
};

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

// Profile
export const getUserProfile = () => apiGet("/user/profile");
export const updateUserProfile = (fullName, email) =>
  apiPut("/user/profile", { full_name: fullName, email });
export const resetUserData = () => apiPost("/user/reset", {});

// Belirli bir oturumun mesajlarını çeker
export const getSessionMessages = (session_id) => apiGet(`/dialogue/history/${session_id}`);