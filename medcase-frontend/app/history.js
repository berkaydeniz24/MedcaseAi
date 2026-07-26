import { useEffect, useState, useCallback, useMemo } from "react";
import { View, Text, FlatList, StyleSheet, Pressable, ActivityIndicator, SafeAreaView, RefreshControl } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { getChatHistory } from "../src/api/endpoints";
import { Colors } from "../src/theme/colors";
import { getStatusDetails } from "../src/utils/caseStatus";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "in_progress", label: "In Progress" },
  { id: "completed", label: "Completed" },
];

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeFilter, setActiveFilter] = useState("all");

  // Verileri çekme fonksiyonu
  const fetchHistory = async () => {
    try {
      const res = await getChatHistory();
      setHistory(res || []);
    } catch (e) {
      console.error("Geçmiş yüklenemedi:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Sayfa her odaklandığında listeyi yenile
  useFocusEffect(
    useCallback(() => {
      fetchHistory();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchHistory();
  };

  // Sohbete Devam Etme Fonksiyonu
  const handleContinueChat = (item) => {
    // Chat sayfasına hem vaka ID'sini hem de Session ID'yi gönderiyoruz
    router.push({
      pathname: `/case/${item.case_id}/chat`,
      params: { session_id: item.session_id } // <-- Kritik nokta burası
    });
  };

  const filteredHistory = useMemo(() => {
    if (activeFilter === "all") return history;
    return history.filter((item) => item.status === activeFilter);
  }, [history, activeFilter]);

  const renderItem = ({ item }) => {
    const status = getStatusDetails(item.status);
    return (
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={() => handleContinueChat(item)}
      >
        <View style={styles.iconBox}>
          <Ionicons name="chatbubble-ellipses-outline" size={24} color={Colors.primary} />
        </View>
        <View style={styles.cardContent}>
          <View style={styles.titleRow}>
            <Text style={styles.caseTitle} numberOfLines={1}>{item.case_title}</Text>
            <View style={[styles.statusBadge, { backgroundColor: status.bg }]}>
              <Text style={[styles.statusBadgeText, { color: status.text }]}>{status.label}</Text>
            </View>
          </View>
          <Text style={styles.lastMsg} numberOfLines={2}>
            {item.last_message.startsWith('[') ? "Case Analysis" : item.last_message}
          </Text>
          <View style={styles.metaRow}>
            <Text style={styles.date}>{item.date}</Text>
            {item.status === "completed" && item.is_correct !== null && (
              <Text style={[styles.metaChip, item.is_correct ? styles.metaChipCorrect : styles.metaChipWrong]}>
                {item.is_correct ? "Correct" : "Incorrect"}
              </Text>
            )}
            {item.hints_used > 0 && (
              <Text style={styles.metaChip}>{item.hints_used} hint{item.hints_used > 1 ? "s" : ""}</Text>
            )}
          </View>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#CBD5E1" />
      </Pressable>
    );
  };

  if (loading) return <View style={styles.center}><ActivityIndicator color={Colors.primary} /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Chat History</Text>
      </View>

      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <Pressable
            key={f.id}
            onPress={() => setActiveFilter(f.id)}
            style={[styles.filterChip, activeFilter === f.id && styles.filterChipActive]}
          >
            <Text style={[styles.filterChipText, activeFilter === f.id && styles.filterChipTextActive]}>
              {f.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {filteredHistory.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="file-tray-outline" size={64} color="#CBD5E1" />
          <Text style={styles.emptyText}>
            {history.length === 0 ? "No chat history yet." : "No cases in this filter yet."}
          </Text>
          <Pressable style={styles.btnStart} onPress={() => router.push("/cases")}>
            <Text style={styles.btnStartText}>Start Solving Cases</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={filteredHistory}
          keyExtractor={(item) => item.session_id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { padding: 20, backgroundColor: "white", borderBottomWidth: 1, borderBottomColor: "#F1F5F9" },
  headerTitle: { fontSize: 22, fontWeight: "800", color: "#1E293B" },

  filterRow: { flexDirection: "row", gap: 10, paddingHorizontal: 20, paddingTop: 16, paddingBottom: 4, backgroundColor: "white" },
  filterChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, backgroundColor: "#F1F5F9", borderWidth: 1, borderColor: "#F1F5F9" },
  filterChipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  filterChipText: { color: Colors.textSub, fontWeight: "700", fontSize: 13 },
  filterChipTextActive: { color: "white" },

  list: { padding: 20 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#F1F5F9",
    // Shadow
    shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 8, elevation: 2
  },
  cardPressed: { backgroundColor: "#F1F5F9" },
  
  iconBox: {
    width: 48, height: 48, borderRadius: 12,
    backgroundColor: Colors.accentSoft, justifyContent: "center", alignItems: "center",
    marginRight: 16
  },
  cardContent: { flex: 1 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  caseTitle: { flex: 1, fontSize: 15, fontWeight: "700", color: "#1E293B" },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  statusBadgeText: { fontSize: 9, fontWeight: "800", textTransform: "uppercase" },
  lastMsg: { fontSize: 13, color: "#64748B", lineHeight: 18 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 6 },
  date: { fontSize: 11, color: "#94A3B8", fontWeight: "500" },
  metaChip: { fontSize: 11, fontWeight: "700", color: Colors.textSub },
  metaChipCorrect: { color: "#166534" },
  metaChipWrong: { color: "#991B1B" },

  emptyState: { flex: 1, justifyContent: "center", alignItems: "center", padding: 40 },
  emptyText: { marginTop: 16, fontSize: 16, color: "#64748B", textAlign: "center" },
  btnStart: { marginTop: 20, backgroundColor: Colors.primary, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
  btnStartText: { color: "white", fontWeight: "700" }
});