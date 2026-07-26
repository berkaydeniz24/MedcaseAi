import { useState, useCallback, useMemo } from "react";
import { View, Text, StyleSheet, ScrollView, SafeAreaView, Dimensions, ActivityIndicator, RefreshControl } from "react-native";
import { useFocusEffect } from "expo-router"; // 👈 Navigasyon odağını yakalamak için
import { Colors } from "../src/theme/colors";
import { Ionicons } from "@expo/vector-icons";
import { getUserStats, getChatHistory } from "../src/api/endpoints";

const { width } = Dimensions.get('window');

export default function DetailedStatsPage() {
  const [stats, setStats] = useState({ total_correct: 0, total_wrong: 0, weekly_activity: [] });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const weeklyActivity = stats.weekly_activity || [];
  const maxActivity = Math.max(1, ...weeklyActivity.map((d) => d.count));

  // Branş bazlı deneme/doğruluk dökümü — /user/history'de zaten var olan
  // specialty + is_correct alanlarından istemci tarafında hesaplanıyor,
  // ayrı bir backend endpoint'ine gerek yok.
  const bySpecialty = useMemo(() => {
    const map = {};
    for (const item of history) {
      if (!map[item.specialty]) map[item.specialty] = { attempts: 0, correct: 0 };
      if (item.status === "completed") {
        map[item.specialty].attempts += 1;
        if (item.is_correct) map[item.specialty].correct += 1;
      }
    }
    return Object.entries(map)
      .filter(([, v]) => v.attempts > 0)
      .map(([specialty, v]) => ({
        specialty,
        attempts: v.attempts,
        accuracy: Math.round((v.correct / v.attempts) * 100),
      }))
      .sort((a, b) => b.attempts - a.attempts);
  }, [history]);

  // Veri çekme fonksiyonu
  const fetchStats = async () => {
    try {
      const [statsRes, historyRes] = await Promise.all([getUserStats(), getChatHistory()]);
      setStats(statsRes);
      setHistory(historyRes || []);
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
        <Text style={styles.headerTitle}>Clinical Metrics</Text>
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
            <Text style={styles.infoLabel}>Correct Diagnoses</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="pie-chart-outline" size={24} color={Colors.accent} />
            <Text style={styles.infoVal}>%{accuracy}</Text>
            <Text style={styles.infoLabel}>Accuracy Rate</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="layers-outline" size={24} color={Colors.warning} />
            <Text style={styles.infoVal}>{totalAnswers}</Text>
            <Text style={styles.infoLabel}>Total Attempts</Text>
          </View>
        </View>

        {/* 2. Haftalık Aktivite Grafiği (gerçek ChatSession verisi) */}
        <Text style={styles.sectionTitle}>WEEKLY CASE ACTIVITY</Text>
        <View style={styles.chartCard}>
          <View style={styles.barChartRow}>
            {weeklyActivity.map((day, idx) => {
              const isPeak = day.count > 0 && day.count === maxActivity;
              return (
                <View key={day.date || idx} style={styles.barWrapper}>
                  {day.count > 0 && <Text style={styles.barCount}>{day.count}</Text>}
                  <View
                    style={[
                      styles.bar,
                      {
                        height: Math.max(6, (day.count / maxActivity) * 100),
                        backgroundColor: isPeak ? Colors.accent : day.count > 0 ? Colors.accentSoft : '#EDF2F7',
                      },
                    ]}
                  />
                  <Text style={styles.barLabel}>{day.day_label}</Text>
                </View>
              );
            })}
          </View>
        </View>

        {/* 3. Branş Bazlı Döküm (gerçek /user/history verisinden hesaplanır) */}
        {bySpecialty.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>BY SPECIALTY</Text>
            <View style={styles.specialtyCard}>
              {bySpecialty.map((s, idx) => (
                <View key={s.specialty} style={[styles.specialtyRow, idx > 0 && styles.specialtyRowBorder]}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.specialtyName}>{s.specialty}</Text>
                    <Text style={styles.specialtyAttempts}>{s.attempts} attempt{s.attempts > 1 ? "s" : ""}</Text>
                  </View>
                  <View style={styles.specialtyTrack}>
                    <View style={[styles.specialtyFill, { width: `${s.accuracy}%` }]} />
                  </View>
                  <Text style={styles.specialtyAccuracy}>%{s.accuracy}</Text>
                </View>
              ))}
            </View>
          </>
        )}

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
  
  chartCard: { backgroundColor: 'white', padding: 20, borderRadius: 24, marginBottom: 25, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  barChartRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 120, paddingTop: 10 },
  barWrapper: { alignItems: 'center', width: (width - 120) / 7 },
  barCount: { fontSize: 10, fontWeight: '800', color: Colors.accentDark, marginBottom: 4 },
  bar: { width: 12, borderRadius: 6, marginBottom: 8 },
  barLabel: { fontSize: 10, fontWeight: '700', color: '#64748B' },

  specialtyCard: { backgroundColor: 'white', borderRadius: 24, marginBottom: 25, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, paddingHorizontal: 20 },
  specialtyRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, gap: 12 },
  specialtyRowBorder: { borderTopWidth: 1, borderTopColor: '#F1F5F9' },
  specialtyName: { fontSize: 14, fontWeight: '700', color: '#1E293B' },
  specialtyAttempts: { fontSize: 11, color: '#94A3B8', marginTop: 2, fontWeight: '600' },
  specialtyTrack: { width: 70, height: 6, borderRadius: 3, backgroundColor: '#F1F5F9', overflow: 'hidden' },
  specialtyFill: { height: '100%', backgroundColor: Colors.accent, borderRadius: 3 },
  specialtyAccuracy: { fontSize: 13, fontWeight: '800', color: Colors.textMain, width: 40, textAlign: 'right' },
});