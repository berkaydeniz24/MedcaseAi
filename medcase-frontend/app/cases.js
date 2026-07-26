import { useEffect, useState, useMemo } from "react";
import { View, Text, FlatList, ActivityIndicator, StyleSheet, SafeAreaView, ScrollView, Pressable } from "react-native";
import { useRouter } from "expo-router";
// 👇 getCaseProgress'i ekledik
import { listCases, getCaseProgress } from "../src/api/endpoints";
import { CaseCard } from "../src/components/common/CaseCard";
import { Colors } from "../src/theme/colors";

const CATEGORIES = ["All", "Cardiology", "Neurology", "General Internal Medicine / Other", "Dermatology", "Orthopedics & Traumatology", "Pulmonology", "Ophthalmology", "Gastroenterology"];

const getStatusDetails = (status) => {
  // Backend'den gelen status kodları: 'solved', 'in_progress', 'new'
  switch (status) {
    case "solved": return { bg: "#DCFCE7", text: "#166534", label: "Completed" };
    case "in_progress": return { bg: "#FEF9C3", text: "#854D0E", label: "In Progress" };
    default: return { bg: "#F1F5F9", text: "#475569", label: "To Solve" };
  }
};

export default function CasesScreen() {
  const router = useRouter();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("All");

  useEffect(() => {
    fetchData();
  }, []);

  // ✅ Hem vaka listesini hem de kullanıcının ilerlemesini paralel çekiyoruz
  const fetchData = async () => {
    try {
      setLoading(true);
      const [casesRes, progressRes] = await Promise.all([
        listCases(),
        getCaseProgress()
      ]);

      const casesData = Array.isArray(casesRes) ? casesRes : (casesRes?.cases || []);
      const progressList = progressRes || [];

      // Vaka listesi ile DB'den gelen durumları birleştiriyoruz
      const mergedData = casesData.map(c => {
        // Bu vaka için DB'de bir kayıt var mı?
        const foundProgress = progressList.find(p => p.case_id === String(c.id));
        return {
          ...c,
          // Varsa DB'deki durumu, yoksa 'new' (Çözülecek)
          status: foundProgress ? foundProgress.status : "new"
        };
      });

      setCases(mergedData);
    } catch (e) {
      console.error("Veri çekme hatası:", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredCases = useMemo(() => {
    let result = activeCategory === "All" ? cases : cases.filter(c => c.specialty === activeCategory);
    // Çözülenleri en alta at, devam edenleri en üste çıkar
    return result.sort((a, b) => {
      if (a.status === 'in_progress') return -1;
      if (b.status === 'in_progress') return 1;
      if (a.status === 'solved') return 1;
      if (b.status === 'solved') return -1;
      return 0;
    });
  }, [cases, activeCategory]);

  if (loading) return <ActivityIndicator size="large" color={Colors.accent} style={{ flex: 1 }} />;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Case Library</Text>
      </View>
      
      {/* Kategori Filtreleri (Aynı Kalıyor) */}
      <View style={{ marginBottom: 15 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryContainer}>
          {CATEGORIES.map((cat) => (
            <Pressable key={cat} onPress={() => setActiveCategory(cat)} style={[styles.catBadge, activeCategory === cat && styles.catBadgeActive]}>
              <Text style={[styles.catText, activeCategory === cat && styles.catTextActive]}>{cat}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>

      <FlatList
        data={filteredCases}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => {
          const status = getStatusDetails(item.status);
          return (
            <View style={styles.cardContainer}>
              <CaseCard item={item} onPress={() => router.push(`/case/${item.id}`)} />
              <View style={[styles.statusTag, { backgroundColor: status.bg }]}>
                <Text style={[styles.statusTagText, { color: status.text }]}>{status.label}</Text>
              </View>
            </View>
          );
        }}
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}
// styles aynı kalabilir...
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: { padding: 20, paddingTop: 10 },
  title: { fontSize: 28, fontWeight: "800", color: Colors.textMain },
  categoryContainer: { paddingHorizontal: 20, gap: 10 },
  catBadge: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12, backgroundColor: "white", borderWidth: 1, borderColor: "#EDF2F7" },
  catBadgeActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  catText: { color: Colors.textSub, fontWeight: "600" },
  catTextActive: { color: "white" },
  list: { paddingHorizontal: 20, paddingBottom: 40 },
  cardContainer: { position: "relative", marginBottom: 10 },
  statusTag: { position: "absolute", top: 12, right: 12, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  statusTagText: { fontSize: 10, fontWeight: "800", textTransform: "uppercase" }
});