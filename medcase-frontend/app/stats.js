import { useState, useCallback } from "react";
import { View, Text, StyleSheet, ScrollView, SafeAreaView, Dimensions, ActivityIndicator, RefreshControl } from "react-native";
import { useFocusEffect } from "expo-router"; // 👈 Navigasyon odağını yakalamak için
import { Colors } from "../src/theme/colors";
import { Ionicons } from "@expo/vector-icons";
import { getUserStats } from "../src/api/endpoints";

const { width } = Dimensions.get('window');

export default function DetailedStatsPage() {
  const [stats, setStats] = useState({ total_correct: 0, total_wrong: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Simüle edilmiş grafik verileri
  const weeklyActivity = [2, 5, 8, 4, 10, 3, 1];
  const maxActivity = Math.max(...weeklyActivity);

  // Veri çekme fonksiyonu
  const fetchStats = async () => {
    try {
      const res = await getUserStats();
      setStats(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ✅ DÜZELTME: useEffect yerine useFocusEffect
  // Sayfa her odaklandığında (tab değişimi dahil) veriyi yeniler.
  useFocusEffect(
    useCallback(() => {
      // İlk açılışta loading gösterelim, sonrakilerde sessizce güncellesin
      fetchStats();
    }, [])
  );

  // Manuel yenileme (Ekranı aşağı çekince)
  const onRefresh = () => {
    setRefreshing(true);
    fetchStats();
  };

  // Hesaplamalar
  const totalAnswers = stats.total_correct + stats.total_wrong;
  const accuracy = totalAnswers > 0 
    ? Math.round((stats.total_correct / totalAnswers) * 100) 
    : 0;

  if (loading) return <View style={{flex:1, justifyContent:'center'}}><ActivityIndicator color={Colors.primary} /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Klinik Metrikler</Text>
        <Text style={styles.headerSub}>MedCase AI v1.2</Text>
      </View>

      <ScrollView 
        showsVerticalScrollIndicator={false} 
        contentContainerStyle={styles.scrollContent}
        // 👇 Pull to Refresh Eklendi
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Colors.primary]} />
        }
      >
        
        {/* 1. Üst Özet Kartları (GERÇEK VERİ) */}
        <View style={styles.statsGrid}>
          <View style={styles.infoCard}>
            <Ionicons name="checkmark-circle-outline" size={24} color={Colors.success} />
            <Text style={styles.infoVal}>{stats.total_correct}</Text>
            <Text style={styles.infoLabel}>Doğru Tanı</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="pie-chart-outline" size={24} color={Colors.accent} />
            <Text style={styles.infoVal}>%{accuracy}</Text>
            <Text style={styles.infoLabel}>Başarı Oranı</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="layers-outline" size={24} color={Colors.warning} />
            <Text style={styles.infoVal}>{totalAnswers}</Text>
            <Text style={styles.infoLabel}>Toplam Deneme</Text>
          </View>
        </View>

        {/* 2. Haftalık Aktivite Grafiği (Placeholder) */}
        <Text style={styles.sectionTitle}>HAFTALIK VAKA AKTİVİTESİ (Simülasyon)</Text>
        <View style={styles.chartCard}>
          <View style={styles.barChartRow}>
            {weeklyActivity.map((val, idx) => (
              <View key={idx} style={styles.barWrapper}>
                <View style={[styles.bar, { height: (val / maxActivity) * 100, backgroundColor: val === maxActivity ? Colors.accent : '#E2E8F0' }]} />
                <Text style={styles.barLabel}>{['P', 'S', 'Ç', 'P', 'C', 'Ct', 'Pz'][idx]}</Text>
              </View>
            ))}
          </View>
        </View>
        
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  header: { padding: 20, backgroundColor: 'white', borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  headerTitle: { fontSize: 22, fontWeight: '800', color: '#1E293B' },
  headerSub: { fontSize: 12, color: '#64748B', marginTop: 4 },
  
  scrollContent: { padding: 20 },
  
  statsGrid: { flexDirection: 'row', gap: 12, marginBottom: 25 },
  infoCard: { flex: 1, backgroundColor: 'white', padding: 15, borderRadius: 20, alignItems: 'center', elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  infoVal: { fontSize: 16, fontWeight: '800', color: '#1E293B', marginTop: 8 },
  infoLabel: { fontSize: 10, color: '#94A3B8', fontWeight: '600', marginTop: 2 },

  sectionTitle: { fontSize: 11, fontWeight: '800', color: '#94A3B8', letterSpacing: 1.5, marginBottom: 15, marginLeft: 5 },
  
  chartCard: { backgroundColor: 'white', padding: 20, borderRadius: 24, marginBottom: 25, elevation: 2 },
  barChartRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 120, paddingTop: 10 },
  barWrapper: { alignItems: 'center', width: (width - 120) / 7 },
  bar: { width: 12, borderRadius: 6, marginBottom: 8 },
  barLabel: { fontSize: 10, fontWeight: '700', color: '#64748B' },
});