import { useEffect, useState, useCallback } from "react";
import { View, Text, FlatList, StyleSheet, Pressable, ActivityIndicator, SafeAreaView, RefreshControl } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { getChatHistory } from "../src/api/endpoints";
import { Colors } from "../src/theme/colors";

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

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

  const renderItem = ({ item }) => (
    <Pressable 
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      onPress={() => handleContinueChat(item)}
    >
      <View style={styles.iconBox}>
        <Ionicons name="chatbubble-ellipses-outline" size={24} color={Colors.primary} />
      </View>
      <View style={styles.cardContent}>
        <Text style={styles.caseTitle} numberOfLines={1}>{item.case_title}</Text>
        <Text style={styles.lastMsg} numberOfLines={2}>
          {item.last_message.startsWith('[') ? "Case Analysis" : item.last_message}
        </Text>
        <Text style={styles.date}>{item.date}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color="#CBD5E1" />
    </Pressable>
  );

  if (loading) return <View style={styles.center}><ActivityIndicator color={Colors.primary} /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Chat History</Text>
      </View>

      {history.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="file-tray-outline" size={64} color="#CBD5E1" />
          <Text style={styles.emptyText}>No chat history yet.</Text>
          <Pressable style={styles.btnStart} onPress={() => router.push("/cases")}>
            <Text style={styles.btnStartText}>Start Solving Cases</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={history}
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
  caseTitle: { fontSize: 15, fontWeight: "700", color: "#1E293B", marginBottom: 4 },
  lastMsg: { fontSize: 13, color: "#64748B", lineHeight: 18 },
  date: { fontSize: 11, color: "#94A3B8", marginTop: 6, fontWeight: "500" },

  emptyState: { flex: 1, justifyContent: "center", alignItems: "center", padding: 40 },
  emptyText: { marginTop: 16, fontSize: 16, color: "#64748B", textAlign: "center" },
  btnStart: { marginTop: 20, backgroundColor: Colors.primary, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
  btnStartText: { color: "white", fontWeight: "700" }
});