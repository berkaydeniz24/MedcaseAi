import { apiGet, apiPost } from "./client";

// Cases
export const listCases = () => apiGet("/cases");
export const getCaseById = (id) => apiGet(`/cases/${id}`);

// Dialogue
export const startDialogue = () => apiGet("/dialogue/start");
export const chatDialogue = (dialogueId, message) =>
  apiPost(`/dialogue/${dialogueId}/chat`, { message });
