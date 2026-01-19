import { useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, Pressable, ActivityIndicator, SafeAreaView, StatusBar, Alert } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { getCaseById } from "../../../src/api/endpoints"; 
import { Colors } from "../../../src/theme/colors";

// Durum seçenekleri ve renkleri
const STATUS_OPTIONS = [
  { id: 'Çözülecek', label: 'Çözülecek', color: '#64748B', bg: '#F1F5F9' },
  { id: 'Devam Ediyor', label: 'Devam Ediyor', color: '#854D0E', bg: '#FEF9C3' },
  { id: 'Çözüldü', label: 'Çözüldü', color: '#166534', bg: '#DCFCE7' }
];

export default function PatientRecordPage() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentStatus, setCurrentStatus] = useState('Çözülecek');

  useEffect(() => {
    getCaseById(String(id))
      .then((res) => {
        setCaseData(res);
        setCurrentStatus(res.status || 'Çözülecek');
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  // Durumu güncelleme fonksiyonu
  const handleStatusChange = (newStatus) => {
    setCurrentStatus(newStatus);
    // Burada backend entegrasyonu yapılacak (Örn: updateCaseStatus(id, newStatus))
    // Şimdilik sadece kullanıcıya geri bildirim veriyoruz
    console.log(`Vaka ${id} durumu ${newStatus} olarak güncellendi.`);
  };

  if (loading) return <ActivityIndicator size="large" color={Colors.accent} style={{ flex: 1 }} />;
  if (!caseData) return <View style={styles.container}><Text>Vaka bulunamadı.</Text></View>;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        
        {/* Vaka Kimlik Kartı ve Durum Değiştirici */}
        <View style={styles.idCard}>
          <View style={styles.idHeader}>
            <View style={styles.patientAvatar}>
              <Text style={styles.avatarText}>P-{id.slice(-2)}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.caseIdText}>Vaka Dosyası</Text>
              <Text style={styles.specialtyText}>{caseData.specialty || "Genel Tıp"}</Text>
            </View>
          </View>

          <View style={styles.statusSection}>
            <Text style={styles.statusTitle}>VAKA DURUMU:</Text>
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

        {/* Klinik Rapor (Eski Kart Yapısı) */}
        <Text style={styles.sectionTitle}>Klinik Tablo</Text>
        <View style={styles.mainInfoCard}>
          <Text style={styles.caseTitleText}>{caseData.title}</Text>
          <View style={styles.divider} />
          <Text style={styles.narrativeText}>{caseData.narrative || "Vaka detayı yüklenemedi."}</Text>
        </View>

      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <Pressable 
          style={styles.actionButton} 
          onPress={() => router.push(`/case/${id}/chat`)}
        >
          <Text style={styles.actionButtonText}>Klinik Tartışmayı Başlat</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { padding: 20, paddingBottom: 100 },
  
  idCard: { backgroundColor: Colors.white, borderRadius: 24, padding: 20, marginBottom: 25, shadowColor: "#000", shadowOpacity: 0.04, shadowRadius: 10, elevation: 2 },
  idHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 20 },
  patientAvatar: { width: 50, height: 50, borderRadius: 15, backgroundColor: '#E2E8F0', justifyContent: 'center', alignItems: 'center' },
  avatarText: { fontWeight: 'bold', color: Colors.textMain, fontSize: 12 },
  caseIdText: { fontSize: 13, color: Colors.textSub, fontWeight: '600' },
  specialtyText: { fontSize: 18, fontWeight: 'bold', color: Colors.textMain },

  // Status Picker Stilleri
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

  footer: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 20, backgroundColor: 'rgba(248, 250, 252, 0.9)' },
  actionButton: { backgroundColor: Colors.primary, paddingVertical: 18, borderRadius: 20, alignItems: 'center' },
  actionButtonText: { color: Colors.white, fontSize: 16, fontWeight: 'bold' }
});