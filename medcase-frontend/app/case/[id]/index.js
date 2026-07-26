import { useEffect, useMemo, useState, useCallback } from "react";
import {
  View, Text, ScrollView, StyleSheet, Pressable,
  ActivityIndicator, SafeAreaView, StatusBar
} from "react-native";
import { useLocalSearchParams, useRouter, useFocusEffect } from "expo-router";
import { getCaseById, submitAnswer } from "../../../src/api/endpoints";
import { Colors } from "../../../src/theme/colors";
import { getLastSession } from "../../../src/api/session_cache";

// Durum seçenekleri
const STATUS_OPTIONS = [
  { id: 'To Solve', label: 'To Solve', color: '#64748B', bg: '#F1F5F9' },
  { id: 'In Progress', label: 'In Progress', color: '#854D0E', bg: '#FEF9C3' },
  { id: 'Solved', label: 'Solved', color: '#166534', bg: '#DCFCE7' }
];

export default function PatientRecordPage() {
  const params = useLocalSearchParams();
  const id = String(params.id);
  const sessionId = params.session_id ? String(params.session_id) : null;

  const router = useRouter();

  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentStatus, setCurrentStatus] = useState('To Solve');

  // MCQ states
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const cached = getLastSession();

  // Cache kontrolü
  const mcq = useMemo(() => {
    if (!sessionId) return null;
    if (!cached) return null;
    if (cached.session_id !== sessionId) return null;
    if (!cached.case || String(cached.case.id) !== id) return null;
    return cached.mcq || null;
  }, [sessionId, cached, id]);

  // 1. Vaka Detayını Çek
  useEffect(() => {
    getCaseById(String(id))
      .then((res) => {
        setCaseData(res);
        setCurrentStatus(res.status || 'To Solve');
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  // 2. EKRANI TEMİZLEME (KRİTİK BÖLÜM)
  // Session ID değiştiğinde seçimleri sıfırla.
  useEffect(() => {
    if (sessionId) {
      setSelectedIndex(null);
      setFeedback(null);
      setSubmitting(false);
    }
  }, [sessionId]); 

  const handleStatusChange = (newStatus) => {
    setCurrentStatus(newStatus);
  };

  const handleSubmitAnswer = async () => {
    if (!sessionId || selectedIndex === null || submitting) return;

    setSubmitting(true);
    try {
      const res = await submitAnswer(sessionId, selectedIndex, "explain", "beginner", "en");
      setFeedback({
        isCorrect: !!res.isCorrect,
        tutorAnswer: res?.tutor?.answer || "Feedback could not be retrieved."
      });
    } catch (e) {
      setFeedback({
        isCorrect: false,
        tutorAnswer: "A connection error occurred."
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <ActivityIndicator size="large" color={Colors.accent} style={{ flex: 1 }} />;
  if (!caseData) return <View style={styles.container}><Text>Case not found.</Text></View>;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>

        {/* Vaka Kimlik Kartı */}
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
            <Text style={styles.statusTitle}>CASE STATUS:</Text>
            <View style={styles.statusPicker}>
              {STATUS_OPTIONS.map((option) => (
                <Pressable
                  key={option.id}
                  onPress={() => handleStatusChange(option.id)}
                  style={[
                    styles.statusOption,
                    { backgroundColor: currentStatus === option.id ? option.bg : 'transparent' },
                    { borderColor: currentStatus === option.id ? option.color : '#E2E8F0' }
                  ]}
                >
                  <Text style={[
                    styles.statusOptionText,
                    { color: currentStatus === option.id ? option.color : '#94A3B8' }
                  ]}>
                    {option.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>

        {/* Klinik Rapor */}
        <Text style={styles.sectionTitle}>Clinical Presentation</Text>
        <View style={styles.mainInfoCard}>
          <Text style={styles.caseTitleText}>{caseData.title}</Text>
          <View style={styles.divider} />
          <Text style={styles.narrativeText}>{caseData.narrative || "Case details could not be loaded."}</Text>
        </View>

        {/* MCQ / Hızlı Antrenman */}
        {sessionId ? (
          <View style={styles.mcqCard}>
            <Text style={styles.mcqTitle}>Quick Practice</Text>

            {!mcq ? (
              <Text style={styles.mcqMuted}>
                Loading session data or not found...
              </Text>
            ) : (
              <>
                <Text style={styles.mcqQuestion}>{mcq.question}</Text>

                <View style={{ marginTop: 12 }}>
                  {mcq.options.map((opt, idx) => {
                    const active = selectedIndex === idx;
                    return (
                      <Pressable
                        key={idx}
                        onPress={() => setSelectedIndex(idx)}
                        style={[
                          styles.optionRow,
                          active && styles.optionRowActive
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

                {feedback && (
                  <View style={[
                    styles.feedbackBox,
                    feedback.isCorrect ? styles.feedbackCorrect : styles.feedbackWrong
                  ]}>
                    <Text style={styles.feedbackTitle}>
                      {feedback.isCorrect ? "Correct ✅" : "Incorrect ❌"}
                    </Text>
                    <Text style={styles.feedbackText}>{feedback.tutorAnswer}</Text>
                  </View>
                )}
              </>
            )}
          </View>
        ) : null}

      </ScrollView>

      <View style={styles.footer}>
        <Pressable
          style={styles.actionButton}
          onPress={() => router.push(`/case/${id}/chat`)}
        >
          <Text style={styles.actionButtonText}>Start Clinical Discussion</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { padding: 20, paddingBottom: 140 },

  idCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginBottom: 25, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  idHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 20 },
  patientAvatar: { width: 50, height: 50, borderRadius: 15, backgroundColor: '#E2E8F0', justifyContent: 'center', alignItems: 'center' },
  avatarText: { fontWeight: 'bold', color: Colors.textMain, fontSize: 12 },
  caseIdText: { fontSize: 13, color: Colors.textSub, fontWeight: '600' },
  specialtyText: { fontSize: 18, fontWeight: 'bold', color: Colors.textMain },

  statusSection: { borderTopWidth: 1, borderTopColor: '#F1F5F9', paddingTop: 15 },
  statusTitle: { fontSize: 10, fontWeight: '800', color: Colors.textSub, marginBottom: 10, letterSpacing: 1 },
  statusPicker: { flexDirection: 'row', gap: 8 },
  statusOption: { flex: 1, paddingVertical: 8, borderRadius: 10, borderWidth: 1, alignItems: 'center' },
  statusOptionText: { fontSize: 11, fontWeight: '700' },

  sectionTitle: { fontSize: 15, fontWeight: '800', color: Colors.textSub, marginBottom: 12, marginLeft: 5 },
  mainInfoCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginBottom: 15, borderWidth: 1, borderColor: '#EDF2F7' },
  caseTitleText: { fontSize: 20, fontWeight: '800', color: Colors.primary, marginBottom: 15 },
  divider: { height: 1, backgroundColor: '#EDF2F7', marginBottom: 15 },
  narrativeText: { fontSize: 16, color: '#4A5568', lineHeight: 26 },

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

  feedbackBox: { marginTop: 14, padding: 14, borderRadius: 18, borderWidth: 1 },
  feedbackCorrect: { borderColor: '#86EFAC', backgroundColor: '#F0FDF4' },
  feedbackWrong: { borderColor: '#FCA5A5', backgroundColor: '#FEF2F2' },
  feedbackTitle: { fontSize: 14, fontWeight: '900', marginBottom: 8, color: Colors.textMain },
  feedbackText: { fontSize: 14, lineHeight: 22, color: Colors.textMain },

  footer: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 20, backgroundColor: 'rgba(248, 250, 252, 0.9)' },
  actionButton: { backgroundColor: Colors.primary, paddingVertical: 18, borderRadius: 20, alignItems: 'center' },
  actionButtonText: { color: Colors.white, fontSize: 16, fontWeight: 'bold' }
});