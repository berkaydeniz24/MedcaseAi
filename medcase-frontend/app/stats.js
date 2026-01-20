import { View, Text, StyleSheet, ScrollView, SafeAreaView, Dimensions } from "react-native";
import { Colors } from "../src/theme/colors";
import { Ionicons } from "@expo/vector-icons";

const { width } = Dimensions.get('window');

export default function DetailedStatsPage() {
  // Simüle edilmiş haftalık veriler (Pazartesi - Pazar)
  const weeklyActivity = [2, 5, 8, 4, 10, 3, 1];
  const maxActivity = Math.max(...weeklyActivity);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Klinik Metrikler</Text>
        <Text style={styles.headerSub}>MedCase AI v1.2</Text>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        
        {/* 1. Üst Özet Kartları */}
        <View style={styles.statsGrid}>
          <View style={styles.infoCard}>
            <Ionicons name="time-outline" size={24} color={Colors.accent} />
            <Text style={styles.infoVal}>6.4 dk</Text>
            <Text style={styles.infoLabel}>Ort. Çözüm</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="medal-outline" size={24} color={Colors.success} />
            <Text style={styles.infoVal}>%92</Text>
            <Text style={styles.infoLabel}>Tanı İsabeti</Text>
          </View>
          <View style={styles.infoCard}>
            <Ionicons name="flash-outline" size={24} color={Colors.warning} />
            <Text style={styles.infoVal}>24</Text>
            <Text style={styles.infoLabel}>Toplam Puan</Text>
          </View>
        </View>

        {/* 2. Haftalık Aktivite Grafiği (Custom Bar Chart) */}
        <Text style={styles.sectionTitle}>HAFTALIK VAKA AKTİVİTESİ</Text>
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

        {/* 3. Zorluk Dağılımı ve Sayısal Veriler */}
        <Text style={styles.sectionTitle}>ZORLUK SEVİYESİ ANALİZİ</Text>
        <View style={styles.chartCard}>
          <View style={styles.distributionContainer}>
            <View style={[styles.distFill, { width: '32.5%', backgroundColor: Colors.success }]} />
            <View style={[styles.distFill, { width: '47.5%', backgroundColor: Colors.warning }]} />
            <View style={[styles.distFill, { width: '20%', backgroundColor: Colors.danger }]} />
          </View>
          <View style={styles.distLegend}>
            <View style={styles.legendItem}>
              <Text style={styles.legendNum}>65</Text>
              <Text style={styles.legendTxt}>Kolay</Text>
            </View>
            <View style={styles.legendItem}>
              <Text style={styles.legendNum}>95</Text>
              <Text style={styles.legendTxt}>Orta</Text>
            </View>
            <View style={styles.legendItem}>
              <Text style={styles.legendNum}>40</Text>
              <Text style={styles.legendTxt}>Zor</Text>
            </View>
          </View>
        </View>

        {/* 4. Branş Bazlı Uzmanlık Skoru */}
        <Text style={styles.sectionTitle}>BRANŞ YETKİNLİĞİ</Text>
        <View style={styles.specialtyCard}>
          {[
            { name: 'Kardiyoloji', score: 85, color: '#EF4444' },
            { name: 'Nöroloji', score: 72, color: '#6366F1' },
            { name: 'Dermatoloji', score: 40, color: '#F59E0B' },
            { name: 'Gastroenteroloji', score: 55, color: '#10B981' }
          ].map((item, index) => (
            <View key={index} style={styles.specRow}>
              <View style={styles.specInfo}>
                <Text style={styles.specName}>{item.name}</Text>
                <Text style={styles.specPerc}>%{item.score}</Text>
              </View>
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${item.score}%`, backgroundColor: item.color }]} />
              </View>
            </View>
          ))}
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

  distributionContainer: { height: 12, flexDirection: 'row', borderRadius: 6, overflow: 'hidden' },
  distFill: { height: '100%' },
  distLegend: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 20 },
  legendItem: { alignItems: 'center' },
  legendNum: { fontSize: 16, fontWeight: '800', color: '#1E293B' },
  legendTxt: { fontSize: 10, color: '#64748B', fontWeight: '600' },

  specialtyCard: { backgroundColor: 'white', borderRadius: 24, padding: 20 },
  specRow: { marginBottom: 18 },
  specInfo: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  specName: { fontSize: 13, fontWeight: '700', color: '#1E293B' },
  specPerc: { fontSize: 12, fontWeight: '800', color: '#64748B' },
  progressBg: { height: 6, backgroundColor: '#F1F5F9', borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 3 }
});