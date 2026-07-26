import { View, Text, StyleSheet, SafeAreaView, Pressable, Modal, ScrollView } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Colors } from "../src/theme/colors";
import { startDialogue, getUserStats } from "../src/api/endpoints";
import { setLastSession } from "../src/api/session_cache";
import { Ionicons } from "@expo/vector-icons";
import { useState, useCallback } from "react";

// id values match the backend's specialty strings exactly (see docs/dataset.md)
const CATEGORIES = [
  { id: "All", label: "General Practice", sub: "Random selection from all specialties" },
  { id: "Cardiology", label: "Cardiology", sub: "Heart & Vascular analysis" },
  { id: "Neurology", label: "Neurology", sub: "Focus on nervous system" },
  { id: "General Internal Medicine / Other", label: "Internal Medicine", sub: "General clinical diagnostics" },
  { id: "Dermatology", label: "Dermatology", sub: "Skin & Soft tissue cases" },
  { id: "Orthopedics & Traumatology", label: "Orthopedics", sub: "Musculoskeletal system" },
  { id: "Pulmonology", label: "Pulmonology", sub: "Respiratory & Lung focus" },
  { id: "Ophthalmology", label: "Ophthalmology", sub: "Visual & Eye pathologies" },
  { id: "Gastroenterology", label: "Gastroenterology", sub: "Digestive system clinicals" },
];

export default function HomeScreen() {
  const router = useRouter();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedCat, setSelectedCat] = useState(CATEGORIES[0]);
  const [stats, setStats] = useState({ total_correct: 0, total_wrong: 0 });

  useFocusEffect(
    useCallback(() => {
      getUserStats().then(setStats).catch(() => {});
    }, [])
  );

  const totalAnswers = stats.total_correct + stats.total_wrong;
  const accuracy = totalAnswers > 0 ? Math.round((stats.total_correct / totalAnswers) * 100) : 0;

  const handleQuickTraining = async () => {
    try {
      // API'ye seçili kategori ID'sini gönderiyoruz
      const specialtyParam = selectedCat.id === "All" ? null : selectedCat.id;
      const res = await startDialogue(specialtyParam);
      
      setLastSession(res);
      router.push(`/case/${res.case.id}?session_id=${res.session_id}`);
    } catch (e) {
      console.log("Quick training error:", e);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false} contentContainerStyle={styles.contentInner}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.welcome}>Welcome back,</Text>
          <Text style={styles.name}>Dr. John Doe</Text>
          <Text style={styles.university}>Biruni University</Text>
        </View>

        {/* Quick stats snapshot */}
        <View style={styles.statsRow}>
          <View style={styles.statChip}>
            <Text style={styles.statValue}>{stats.total_correct}</Text>
            <Text style={styles.statLabel}>Correct</Text>
          </View>
          <View style={styles.statChip}>
            <Text style={styles.statValue}>%{accuracy}</Text>
            <Text style={styles.statLabel}>Accuracy</Text>
          </View>
          <View style={styles.statChip}>
            <Text style={styles.statValue}>{totalAnswers}</Text>
            <Text style={styles.statLabel}>Attempts</Text>
          </View>
        </View>

        {/* Bilgi Kartı */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Practice Readiness</Text>
          <Text style={styles.infoSub}>
            Currently focused on {selectedCat.label.toLowerCase()}.
          </Text>
        </View>

        {/* Dinamik Quick Training Kartı */}
        <Pressable style={styles.randomCard} onPress={handleQuickTraining}>
          <View style={styles.randomCardContent}>
            <View style={{ flex: 1 }}>
              <Text style={styles.randomTitle}>
                {selectedCat.id === "All" ? "Quick Training" : `${selectedCat.label}`}
              </Text>
              <Text style={styles.randomSub}>{selectedCat.sub}</Text>
            </View>
            <View style={styles.iconCircle}>
              <Ionicons name="flash" size={28} color="white" />
            </View>
          </View>
        </Pressable>

        {/* Kategori Seçme Butonu (Daily Goal Yerine) */}
        <View style={styles.categoryPickerSection}>
          <Pressable style={styles.pickerButton} onPress={() => setIsModalVisible(true)}>
            <View style={styles.pickerIconBg}>
              <Ionicons name="layers-outline" size={20} color={Colors.accent} />
            </View>
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.pickerLabel}>Change Specialty</Text>
              <Text style={styles.pickerValue}>{selectedCat.label}</Text>
            </View>
            <Ionicons name="chevron-up" size={20} color={Colors.textSub} />
          </Pressable>
        </View>
      </ScrollView>

      {/* Yarı Modal Seçim Ekranı */}
      <Modal
        animationType="fade"
        transparent={true}
        visible={isModalVisible}
        onRequestClose={() => setIsModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <Pressable style={styles.modalCloser} onPress={() => setIsModalVisible(false)} />
          <View style={styles.modalContent}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Select Medical Specialty</Text>
            
            <ScrollView showsVerticalScrollIndicator={false}>
              {CATEGORIES.map((cat) => (
                <Pressable 
                  key={cat.id} 
                  style={[
                    styles.modalItem, 
                    selectedCat.id === cat.id && styles.modalItemActive
                  ]}
                  onPress={() => {
                    setSelectedCat(cat);
                    setIsModalVisible(false);
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={[
                      styles.modalItemLabel, 
                      selectedCat.id === cat.id && styles.modalItemLabelActive
                    ]}>
                      {cat.label}
                    </Text>
                    <Text style={styles.modalItemSub}>{cat.sub}</Text>
                  </View>
                  {selectedCat.id === cat.id && (
                    <Ionicons name="checkmark-circle" size={24} color={Colors.accent} />
                  )}
                </Pressable>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { flex: 1 },
  contentInner: { padding: 25, paddingTop: 15, paddingBottom: 40 },
  header: { marginBottom: 25 },
  welcome: { fontSize: 18, color: Colors.textSub, fontWeight: "500" },
  name: { fontSize: 32, fontWeight: "800", color: Colors.textMain, marginTop: 4 },
  university: { fontSize: 14, color: Colors.accent, fontWeight: "600", marginTop: 4 },

  statsRow: { flexDirection: 'row', gap: 12, marginBottom: 25 },
  statChip: { flex: 1, backgroundColor: Colors.card, borderRadius: 20, paddingVertical: 16, alignItems: 'center', borderWidth: 1, borderColor: '#EDF2F7', shadowColor: "#000", shadowOpacity: 0.02, shadowRadius: 10, elevation: 2 },
  statValue: { fontSize: 20, fontWeight: '800', color: Colors.textMain },
  statLabel: { fontSize: 11, fontWeight: '700', color: Colors.textSub, marginTop: 4, textTransform: 'uppercase', letterSpacing: 0.5 },

  infoCard: { marginBottom: 25 },
  infoTitle: { fontSize: 18, fontWeight: "700", color: Colors.textMain },
  infoSub: { fontSize: 14, color: Colors.textSub, marginTop: 6, lineHeight: 22 },

  randomCard: { backgroundColor: Colors.accent, padding: 25, borderRadius: 30, elevation: 8, shadowColor: Colors.accent, shadowOpacity: 0.3, shadowRadius: 15 },
  randomCardContent: { flexDirection: "row", alignItems: "center" },
  randomTitle: { color: "white", fontSize: 22, fontWeight: "800" },
  randomSub: { color: "rgba(255,255,255,0.8)", fontSize: 13, marginTop: 4 },
  iconCircle: { width: 50, height: 50, borderRadius: 25, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center' },

  categoryPickerSection: { marginTop: 25 },
  pickerButton: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: 'white', 
    padding: 15, 
    borderRadius: 24, 
    borderWidth: 1, 
    borderColor: '#EDF2F7',
    shadowColor: "#000",
    shadowOpacity: 0.02,
    shadowRadius: 10,
    elevation: 2 
  },
  pickerIconBg: { width: 40, height: 40, borderRadius: 12, backgroundColor: '#F8FAFC', justifyContent: 'center', alignItems: 'center' },
  pickerLabel: { fontSize: 11, fontWeight: '800', color: Colors.textSub, textTransform: 'uppercase', letterSpacing: 0.5 },
  pickerValue: { fontSize: 15, fontWeight: '700', color: Colors.textMain, marginTop: 2 },

  // Modal Tasarımı
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'flex-end' },
  modalCloser: { flex: 1 },
  modalContent: { backgroundColor: 'white', borderTopLeftRadius: 35, borderTopRightRadius: 35, padding: 25, maxHeight: '75%' },
  modalHandle: { width: 40, height: 4, backgroundColor: '#E2E8F0', borderRadius: 10, alignSelf: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: '800', color: Colors.textMain, marginBottom: 20, textAlign: 'center' },
  modalItem: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 20, marginBottom: 8, backgroundColor: '#F8FAFC' },
  modalItemActive: { backgroundColor: Colors.accentSoft, borderWidth: 1, borderColor: Colors.accent },
  modalItemLabel: { fontSize: 16, fontWeight: '700', color: Colors.textMain },
  modalItemLabelActive: { color: Colors.accent },
  modalItemSub: { fontSize: 12, color: Colors.textSub, marginTop: 2 }
});