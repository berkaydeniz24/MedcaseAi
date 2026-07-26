// Shared case/session status -> {bg, text, label} mapping. Backend status
// values are 'solved' | 'in_progress' | 'new' (CaseProgress) or
// 'completed' | 'in_progress' (ChatSession) — both map through here so
// cases.js, history.js, and case/[id]/index.js render identical badges
// instead of three copies of the same switch statement.
export const getStatusDetails = (status) => {
  switch (status) {
    case "solved":
    case "completed":
      return { bg: "#DCFCE7", text: "#166534", label: "Completed" };
    case "in_progress":
      return { bg: "#FEF9C3", text: "#854D0E", label: "In Progress" };
    default:
      return { bg: "#F1F5F9", text: "#475569", label: "To Solve" };
  }
};

// Real backend values are 'Beginner' | 'Intermediate' | 'Advanced'
// (medcase-backend/enrichment/schemas.py) — not 'Easy'/'Medium'/'Hard'.
export const getDifficultyDetails = (level) => {
  switch (level) {
    case "Beginner":
      return { bg: "#DCFCE7", text: "#166534" };
    case "Intermediate":
      return { bg: "#FEF9C3", text: "#854D0E" };
    case "Advanced":
      return { bg: "#FEE2E2", text: "#991B1B" };
    default:
      return { bg: "#F1F5F9", text: "#475569" };
  }
};
