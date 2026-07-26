import { useEffect, useState } from "react";
import {
  View, Text, Image, ScrollView, StyleSheet, Pressable,
  ActivityIndicator, SafeAreaView, StatusBar
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { getCaseById, getCaseProgress, startDialogue, submitAnswer } from "../../../src/api/endpoints";
import { Colors } from "../../../src/theme/colors";
import { getLastSession, setLastSession } from "../../../src/api/session_cache";
import { getStatusDetails, getDifficultyDetails } from "../../../src/utils/caseStatus";

// Video-roadmap "aşamalı vaka sunumu": 4 stages, not the video's 7
// (Presentation/History/Examination/Tests collapse into one — the case
// narrative isn't pre-split into those sections in the data, see
// docs/session_log_2026-07-26.md's staged-presentation planning note for
// why). Diagnosis/Management stay locked until the MCQ is submitted,
// matching the existing Socratic design elsewhere in the app.
const STAGES = ["Presentation", "Your Assessment", "Diagnosis & Reasoning", "Management"];

export default function PatientRecordPage() {
  const params = useLocalSearchParams();
  const id = String(params.id);
  const urlSessionId = params.session_id ? String(params.session_id) : null;

  const router = useRouter();

  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [caseStatus, setCaseStatus] = useState("new");
  const [imageFailed, setImageFailed] = useState(false);

  const [currentStep, setCurrentStep] = useState(0);

  // { session_id, mcq: {question, options} | null }. Seeded from the
  // session_id URL param (Home's Quick Training/Continue/Daily flows) if
  // present; otherwise created on demand when the student advances past
  // step 1 — this is what lets a case opened cold from the Cases Library
  // (no session_id today) get an assessment step at all.
  const [activeSession, setActiveSession] = useState(null);
  const [startingSession, setStartingSession] = useState(false);
  const [startError, setStartError] = useState(null);

  const [selectedIndex, setSelectedIndex] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null); // {isCorrect, tutorAnswer, correctIndex}

  // 1. Vaka Detayını ve gerçek ilerleme durumunu çek
  useEffect(() => {
    setLoading(true);
    setImageFailed(false);
    setCurrentStep(0);
    Promise.all([getCaseById(String(id)), getCaseProgress()])
      .then(([caseRes, progressRes]) => {
        setCaseData(caseRes);
        const found = (progressRes || []).find((p) => p.case_id === String(id));
        setCaseStatus(found ? found.status : "new");
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  // 2. Var olan oturumu (varsa) cache'den yükle; session_id değişince
  // seçim/feedback state'ini sıfırla.
  useEffect(() => {
    setSelectedIndex(null);
    setFeedback(null);
    setSubmitting(false);
    setStartError(null);

    if (!urlSessionId) {
      setActiveSession(null);
      return;
    }
    const cached = getLastSession();
    if (cached && cached.session_id === urlSessionId && cached.case && String(cached.case.id) === id) {
      setActiveSession({ session_id: urlSessionId, mcq: cached.mcq || null });
    } else {
      // session_id URL'de var ama cache boş (ör. sayfa yenilendi) — mcq
      // bilinmiyor, aynı önceki davranış gibi bir "yükleniyor" mesajı gösterilir.
      setActiveSession({ session_id: urlSessionId, mcq: null });
    }
  }, [urlSessionId, id]);

  const handleContinueFromPresentation = async () => {
    if (activeSession) {
      setCurrentStep(1);
      return;
    }
    setStartingSession(true);
    setStartError(null);
    try {
      const res = await startDialogue(null, id);
      setLastSession(res);
      setActiveSession({ session_id: res.session_id, mcq: res.mcq });
      setCurrentStep(1);
    } catch (e) {
      setStartError("Could not start this case's assessment. Please try again.");
    } finally {
      setStartingSession(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeSession?.session_id || selectedIndex === null || submitting) return;
    setSubmitting(true);
    try {
      const res = await submitAnswer(activeSession.session_id, selectedIndex, "explain", "beginner", "en");
      setFeedback({
        isCorrect: !!res.isCorrect,
        tutorAnswer: res?.tutor?.answer || "Feedback could not be retrieved.",
        correctIndex: res.correctIndex,
      });
      setCurrentStep(2);
    } catch (e) {
      setFeedback({ isCorrect: false, tutorAnswer: "A connection error occurred. Please try again." });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <ActivityIndicator size="large" color={Colors.accent} style={{ flex: 1 }} />;
  if (!caseData) return <View style={styles.container}><Text>Case not found.</Text></View>;

  const statusDetails = getStatusDetails(caseStatus);
  const difficultyDetails = getDifficultyDetails(caseData.difficulty);
  const chiefComplaint = caseData.rubric?.chief_complaint?.trim();
  const ddxTop = (caseData.rubric?.ddx_top || []).filter(Boolean);
  const managementList = (caseData.rubric?.management_initial || []).filter(Boolean);
  const pitfallsList = (caseData.rubric?.pitfalls || []).filter(Boolean);

  const goToChat = () =>
    router.push({
      pathname: `/case/${id}/chat`,
      params: activeSession?.session_id ? { session_id: activeSession.session_id } : {},
    });

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* İlerleme çubuğu — video-roadmap "Progress: 3/7 steps" karşılığı */}
      <View style={styles.progressWrap}>
        <View style={styles.progressBarRow}>
          {STAGES.map((_, i) => (
            <View
              key={i}
              style={[styles.progressSegment, i <= currentStep && styles.progressSegmentActive]}
            />
          ))}
        </View>
        <Text style={styles.progressLabel}>
          Step {currentStep + 1}/{STAGES.length} · {STAGES[currentStep]}
        </Text>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

        {/* Vaka Kimlik Kartı — her adımda görünür, bağlam kaybolmasın */}
        <View style={styles.idCard}>
          <View style={styles.idHeader}>
            <View style={styles.patientAvatar}>
              <Text style={styles.avatarText}>P-{id.slice(-2)}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.caseIdText}>Case File</Text>
              <Text style={styles.specialtyText}>{caseData.specialty || "General Medicine"}</Text>
            </View>
          </View>

          <View style={styles.statusSection}>
            <Text style={styles.statusTitle}>CASE STATUS</Text>
            <View style={styles.badgeRow}>
              <View style={[styles.readOnlyBadge, { backgroundColor: statusDetails.bg }]}>
                <Text style={[styles.readOnlyBadgeText, { color: statusDetails.text }]}>{statusDetails.label}</Text>
              </View>
              <View style={[styles.readOnlyBadge, { backgroundColor: difficultyDetails.bg }]}>
                <Text style={[styles.readOnlyBadgeText, { color: difficultyDetails.text }]}>
                  {caseData.difficulty || "Intermediate"}
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* ---------- STEP 0: PRESENTATION ---------- */}
        {currentStep === 0 && (
          <>
            {chiefComplaint ? (
              <View style={styles.chiefComplaintCard}>
                <Text style={styles.chiefComplaintLabel}>CHIEF COMPLAINT</Text>
                <Text style={styles.chiefComplaintText}>{chiefComplaint}</Text>
              </View>
            ) : null}

            {caseData.image && !imageFailed ? (
              <Image
                source={{ uri: caseData.image }}
                style={styles.caseImage}
                resizeMode="contain"
                onError={() => setImageFailed(true)}
              />
            ) : null}

            <Text style={styles.sectionTitle}>Clinical Presentation</Text>
            <View style={styles.mainInfoCard}>
              <Text style={styles.caseTitleText}>{caseData.title}</Text>
              <View style={styles.divider} />
              <Text style={styles.narrativeText}>{caseData.narrative || "Case details could not be loaded."}</Text>
            </View>

            {startError ? <Text style={styles.errorText}>{startError}</Text> : null}

            <Pressable
              style={[styles.continueBtn, startingSession && { opacity: 0.7 }]}
              onPress={handleContinueFromPresentation}
              disabled={startingSession}
            >
              {startingSession
                ? <ActivityIndicator color="white" />
                : <Text style={styles.continueBtnText}>Continue to Assessment →</Text>}
            </Pressable>
          </>
        )}

        {/* ---------- STEP 1: YOUR ASSESSMENT ---------- */}
        {currentStep === 1 && (
          <View style={styles.mcqCard}>
            <Text style={styles.mcqTitle}>Your Assessment</Text>

            {!activeSession?.mcq ? (
              <Text style={styles.mcqMuted}>Loading session data or not found...</Text>
            ) : (
              <>
                <Text style={styles.mcqQuestion}>{activeSession.mcq.question}</Text>

                <View style={{ marginTop: 12 }}>
                  {activeSession.mcq.options.map((opt, idx) => {
                    const active = selectedIndex === idx;
                    return (
                      <Pressable
                        key={idx}
                        onPress={() => !feedback && setSelectedIndex(idx)}
                        disabled={!!feedback}
                        style={[
                          styles.optionRow,
                          active && styles.optionRowActive,
                          feedback && { opacity: 0.6 }
                        ]}
                      >
                        <Text style={[styles.optionLetter, active && styles.optionLetterActive]}>
                          {String.fromCharCode(65 + idx)}
                        </Text>
                        <Text style={[styles.optionText, active && styles.optionTextActive]}>
                          {opt}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                {!feedback && (
                  <Pressable
                    onPress={handleSubmitAnswer}
                    disabled={selectedIndex === null || submitting}
                    style={[
                      styles.submitBtn,
                      (selectedIndex === null || submitting) && { opacity: 0.6 }
                    ]}
                  >
                    <Text style={styles.submitBtnText}>
                      {submitting ? "Evaluating..." : "Submit Answer"}
                    </Text>
                  </Pressable>
                )}

                {feedback && (
                  <Pressable style={styles.continueBtn} onPress={() => setCurrentStep(2)}>
                    <Text style={styles.continueBtnText}>See Diagnosis & Reasoning →</Text>
                  </Pressable>
                )}
              </>
            )}

            <Pressable style={styles.backBtn} onPress={() => setCurrentStep(0)}>
              <Text style={styles.backBtnText}>← Back to Presentation</Text>
            </Pressable>
          </View>
        )}

        {/* ---------- STEP 2: DIAGNOSIS & REASONING ---------- */}
        {currentStep === 2 && feedback && (
          <>
            <View style={[styles.diagnosisCard, feedback.isCorrect ? styles.feedbackCorrect : styles.feedbackWrong]}>
              <Text style={styles.diagnosisTitle}>
                {feedback.isCorrect ? "Correct ✅" : "Not quite ❌"}
              </Text>
              {activeSession?.mcq && feedback.correctIndex != null && (
                <Text style={styles.correctAnswerText}>
                  Correct answer: {String.fromCharCode(65 + feedback.correctIndex)}) {activeSession.mcq.options[feedback.correctIndex]}
                </Text>
              )}
              <Text style={styles.diagnosisExplanation}>{feedback.tutorAnswer}</Text>
            </View>

            {ddxTop.length > 0 && (
              <View style={styles.listCard}>
                <Text style={styles.listLabel}>OTHER DIAGNOSES CONSIDERED</Text>
                {ddxTop.map((d, i) => (
                  <Text key={i} style={styles.listItem}>• {d}</Text>
                ))}
              </View>
            )}

            <Pressable style={styles.continueBtn} onPress={() => setCurrentStep(3)}>
              <Text style={styles.continueBtnText}>Continue to Management →</Text>
            </Pressable>
            <Pressable style={styles.backBtn} onPress={() => setCurrentStep(1)}>
              <Text style={styles.backBtnText}>← Back to Assessment</Text>
            </Pressable>
          </>
        )}

        {/* ---------- STEP 3: MANAGEMENT & TEACHING POINTS ---------- */}
        {currentStep === 3 && (
          <>
            {managementList.length > 0 && (
              <View style={styles.listCard}>
                <Text style={styles.listLabel}>INITIAL MANAGEMENT</Text>
                {managementList.map((m, i) => (
                  <Text key={i} style={styles.listItem}>• {m}</Text>
                ))}
              </View>
            )}

            {pitfallsList.length > 0 && (
              <View style={styles.listCard}>
                <Text style={styles.listLabel}>COMMON PITFALLS</Text>
                {pitfallsList.map((p, i) => (
                  <Text key={i} style={styles.listItem}>• {p}</Text>
                ))}
              </View>
            )}

            {managementList.length === 0 && pitfallsList.length === 0 && (
              <View style={styles.mainInfoCard}>
                <Text style={styles.narrativeText}>
                  Detailed management notes aren't available yet for this case — continue the
                  discussion in chat to explore management and next steps with your tutor.
                </Text>
              </View>
            )}

            <Pressable style={styles.continueBtn} onPress={goToChat}>
              <Text style={styles.continueBtnText}>Start Clinical Discussion →</Text>
            </Pressable>
            <Pressable style={styles.backBtn} onPress={() => setCurrentStep(2)}>
              <Text style={styles.backBtnText}>← Back to Diagnosis</Text>
            </Pressable>
          </>
        )}

      </ScrollView>

      <View style={styles.footer}>
        <Pressable style={styles.actionButton} onPress={goToChat}>
          <Text style={styles.actionButtonText}>Start Clinical Discussion</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { padding: 20, paddingBottom: 140 },

  progressWrap: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 10, backgroundColor: Colors.background },
  progressBarRow: { flexDirection: 'row', gap: 6, marginBottom: 8 },
  progressSegment: { flex: 1, height: 5, borderRadius: 3, backgroundColor: '#E2E8F0' },
  progressSegmentActive: { backgroundColor: Colors.accent },
  progressLabel: { fontSize: 11, fontWeight: '800', color: Colors.textSub, letterSpacing: 0.5, textTransform: 'uppercase' },

  idCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginBottom: 25, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  idHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 20 },
  patientAvatar: { width: 50, height: 50, borderRadius: 15, backgroundColor: '#E2E8F0', justifyContent: 'center', alignItems: 'center' },
  avatarText: { fontWeight: 'bold', color: Colors.textMain, fontSize: 12 },
  caseIdText: { fontSize: 13, color: Colors.textSub, fontWeight: '600' },
  specialtyText: { fontSize: 18, fontWeight: 'bold', color: Colors.textMain },

  statusSection: { borderTopWidth: 1, borderTopColor: '#F1F5F9', paddingTop: 15 },
  statusTitle: { fontSize: 10, fontWeight: '800', color: Colors.textSub, marginBottom: 10, letterSpacing: 1 },
  badgeRow: { flexDirection: 'row', gap: 8 },
  readOnlyBadge: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10 },
  readOnlyBadgeText: { fontSize: 12, fontWeight: '800' },

  chiefComplaintCard: { backgroundColor: Colors.accentSoft, borderRadius: 18, padding: 16, marginBottom: 15, borderWidth: 1, borderColor: Colors.accentSoftBorder },
  chiefComplaintLabel: { fontSize: 10, fontWeight: '800', color: Colors.accentDark, letterSpacing: 1, marginBottom: 6 },
  chiefComplaintText: { fontSize: 15, fontWeight: '700', color: Colors.textMain, lineHeight: 22 },

  caseImage: { width: '100%', height: 220, borderRadius: 18, marginBottom: 15, backgroundColor: '#EDF2F7' },

  sectionTitle: { fontSize: 15, fontWeight: '800', color: Colors.textSub, marginBottom: 12, marginLeft: 5 },
  mainInfoCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginBottom: 15, borderWidth: 1, borderColor: '#EDF2F7' },
  caseTitleText: { fontSize: 20, fontWeight: '800', color: Colors.primary, marginBottom: 15 },
  divider: { height: 1, backgroundColor: '#EDF2F7', marginBottom: 15 },
  narrativeText: { fontSize: 16, color: '#4A5568', lineHeight: 26 },

  errorText: { color: Colors.danger, fontSize: 13, fontWeight: '600', textAlign: 'center', marginBottom: 10 },

  continueBtn: { backgroundColor: Colors.accent, paddingVertical: 16, borderRadius: 18, alignItems: 'center', marginTop: 10 },
  continueBtnText: { color: 'white', fontSize: 15, fontWeight: '800' },
  backBtn: { paddingVertical: 14, alignItems: 'center', marginTop: 6 },
  backBtnText: { color: Colors.textSub, fontSize: 13, fontWeight: '700' },

  // MCQ styles
  mcqCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginTop: 10, borderWidth: 1, borderColor: '#EDF2F7' },
  mcqTitle: { fontSize: 14, fontWeight: '900', color: Colors.textSub, marginBottom: 10, letterSpacing: 0.5 },
  mcqMuted: { fontSize: 14, color: Colors.textSub, lineHeight: 22 },
  mcqQuestion: { fontSize: 16, fontWeight: '800', color: Colors.textMain, lineHeight: 24 },

  optionRow: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'flex-start',
    padding: 14,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 10,
    backgroundColor: '#F8FAFC'
  },
  optionRowActive: {
    borderColor: Colors.primary,
    backgroundColor: 'rgba(59, 130, 246, 0.08)'
  },
  optionLetter: {
    width: 26,
    height: 26,
    borderRadius: 8,
    textAlign: 'center',
    lineHeight: 26,
    fontWeight: '900',
    color: Colors.textSub,
    backgroundColor: '#E2E8F0'
  },
  optionLetterActive: {
    color: Colors.white,
    backgroundColor: Colors.primary
  },
  optionText: { flex: 1, fontSize: 14, color: Colors.textMain, lineHeight: 20, fontWeight: '600' },
  optionTextActive: { color: Colors.textMain },

  submitBtn: { backgroundColor: Colors.primary, paddingVertical: 14, borderRadius: 18, alignItems: 'center', marginTop: 8 },
  submitBtnText: { color: Colors.white, fontSize: 15, fontWeight: '900' },

  diagnosisCard: { marginBottom: 15, padding: 18, borderRadius: 20, borderWidth: 1 },
  feedbackCorrect: { borderColor: '#86EFAC', backgroundColor: '#F0FDF4' },
  feedbackWrong: { borderColor: '#FCA5A5', backgroundColor: '#FEF2F2' },
  diagnosisTitle: { fontSize: 16, fontWeight: '900', marginBottom: 8, color: Colors.textMain },
  correctAnswerText: { fontSize: 14, fontWeight: '800', color: Colors.textMain, marginBottom: 10, lineHeight: 20 },
  diagnosisExplanation: { fontSize: 14, lineHeight: 22, color: Colors.textMain },

  listCard: { backgroundColor: Colors.white, borderRadius: 20, padding: 18, marginBottom: 15, borderWidth: 1, borderColor: '#EDF2F7' },
  listLabel: { fontSize: 10, fontWeight: '800', color: Colors.textSub, letterSpacing: 1, marginBottom: 10 },
  listItem: { fontSize: 14, color: Colors.textMain, lineHeight: 22 },

  footer: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 20, backgroundColor: 'rgba(248, 250, 252, 0.9)' },
  actionButton: { backgroundColor: Colors.primary, paddingVertical: 18, borderRadius: 20, alignItems: 'center' },
  actionButtonText: { color: Colors.white, fontSize: 16, fontWeight: 'bold' }
});
