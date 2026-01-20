import { useEffect, useState, useMemo } from "react";
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Pressable,
} from "react-native";
import { useRouter } from "expo-router";
import { listCases, startDialogue } from "../src/api/endpoints";
import { CaseCard } from "../src/components/common/CaseCard";
import { Colors } from "../src/theme/colors";
import { setLastSession } from "../src/api/session_cache";

const CATEGORIES = [
  "Hepsi",
  "Kardiyoloji",
  "Nöroloji",
  "Genel Dahiliye / Diğer",
  "Dermatoloji",
  "Ortopedi & Travmatoloji",
];

// Durum etiketleri için yardımcı fonksiyon
const getStatusDetails = (status) => {
  switch (status) {
    case "Çözüldü":
      return { bg: "#DCFCE7", text: "#166534", label: "Tamamlandı" };
    case "Devam Ediyor":
      return { bg: "#FEF9C3", text: "#854D0E", label: "İşleniyor" };
    default:
      return { bg: "#F1F5F9", text: "#475569", label: "Çözülecek" };
  }
};

export default function HomePage() {
  const router = useRouter();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("Hepsi");
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let alive = true;

    setLoading(true);
    setLoadError(null);

    listCases()
      .then((res) => {
        if (!alive) return;

        console.log("listCases raw:", res);

        // Güvenlik: bazen backend {cases:[...]} gibi dönebilir
        const data = Array.isArray(res) ? res : (res?.cases || res?.items || []);

        const enrichedCases = data.map((c) => ({
          ...c,
          status: c.status || "Çözülecek",
        }));

        setCases(enrichedCases);
      })
      .catch((e) => {
        if (!alive) return;

        console.log("listCases error:", e?.message || e);
        setLoadError(e?.message || "Network/Fetch error");
        setCases([]);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const filteredCases = useMemo(() => {
    let result = cases;

    if (activeCategory !== "Hepsi") {
      result = result.filter((c) => c.specialty === activeCategory);
    }

    // Önce çözülecek olanları, sonra devam edenleri gösteren bir sıralama
    return result.sort((a, b) => (a.status === "Çözüldü" ? 1 : -1));
  }, [cases, activeCategory]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator
          size="large"
          color={Colors.accent}
          style={{ marginTop: 50 }}
        />
        <Text style={styles.loadingHint}>
          Backend’e bağlanılıyor... Eğer uzun sürerse IP / firewall kontrolü gerekir.
        </Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.welcome}>Merhaba, Dr. Göktuğ</Text>
        <Text style={styles.title}>Vaka Kütüphanesi</Text>

        {loadError ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorTitle}>Veri alınamadı</Text>
            <Text style={styles.errorText}>{String(loadError)}</Text>
          </View>
        ) : null}
      </View>

      <View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.categoryContainer}
        >
          {CATEGORIES.map((cat) => (
            <Pressable
              key={cat}
              onPress={() => setActiveCategory(cat)}
              style={[
                styles.catBadge,
                activeCategory === cat && styles.catBadgeActive,
              ]}
            >
              <Text
                style={[
                  styles.catText,
                  activeCategory === cat && styles.catTextActive,
                ]}
              >
                {cat}
              </Text>
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
              <CaseCard
                item={item}
                onPress={() => router.push(`/case/${item.id}`)}
              />
              <View style={[styles.statusTag, { backgroundColor: status.bg }]}>
                <Text style={[styles.statusTagText, { color: status.text }]}>
                  {status.label}
                </Text>
              </View>
            </View>
          );
        }}
        ListHeaderComponent={() => (
          <Pressable
            style={styles.randomCard}
            onPress={async () => {
              try {
                const res = await startDialogue(); // { session_id, case, mcq }
                console.log("startDialogue raw:", res);

                setLastSession(res);
                router.push(`/case/${res.case.id}?session_id=${res.session_id}`);
              } catch (e) {
                console.log("startDialogue error:", e?.message || e);
              }
            }}
          >
            <View style={styles.randomCardContent}>
              <View>
                <Text style={styles.randomTitle}>Hızlı Antrenman</Text>
                <Text style={styles.randomSub}>
                  Rastgele bir vaka ile yeteneklerini test et.
                </Text>
              </View>
              <Text style={{ fontSize: 30 }}>🎯</Text>
            </View>
          </Pressable>
        )}
        ListEmptyComponent={() => (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyTitle}>Hiç vaka gelmedi</Text>
            <Text style={styles.emptyText}>
              Eğer tarayıcıdan /cases çalışıyor ama burada boşsa, Expo fetch isteği
              backend’e ulaşamıyor olabilir (CORS değil, network/firewall/URL).
            </Text>
          </View>
        )}
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },

  header: { padding: 20 },
  welcome: { fontSize: 14, color: Colors.textSub, fontWeight: "500" },
  title: { fontSize: 28, fontWeight: "800", color: Colors.textMain },

  loadingHint: {
    marginTop: 12,
    textAlign: "center",
    color: Colors.textSub,
    paddingHorizontal: 20,
  },

  errorBox: {
    marginTop: 12,
    backgroundColor: "#FEF2F2",
    borderWidth: 1,
    borderColor: "#FCA5A5",
    borderRadius: 14,
    padding: 12,
  },
  errorTitle: { fontWeight: "900", color: "#991B1B", marginBottom: 4 },
  errorText: { color: "#991B1B" },

  categoryContainer: { paddingHorizontal: 20, paddingBottom: 15, gap: 10 },
  catBadge: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 12,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  catBadgeActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  catText: { color: Colors.textSub, fontWeight: "600" },
  catTextActive: { color: Colors.white },
  list: { paddingHorizontal: 20, paddingBottom: 40 },

  cardContainer: { position: "relative" },
  statusTag: {
    position: "absolute",
    top: 12,
    right: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    zIndex: 10,
  },
  statusTagText: {
    fontSize: 10,
    fontWeight: "800",
    textTransform: "uppercase",
  },

  randomCard: {
    backgroundColor: Colors.accent,
    padding: 20,
    borderRadius: 24,
    marginBottom: 25,
    shadowColor: Colors.accent,
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 5,
  },
  randomCardContent: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  randomTitle: { color: Colors.white, fontSize: 18, fontWeight: "bold" },
  randomSub: { color: "rgba(255,255,255,0.8)", fontSize: 13, marginTop: 4 },

  emptyBox: {
    padding: 16,
    backgroundColor: Colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },
  emptyTitle: { fontWeight: "900", marginBottom: 6, color: Colors.textMain },
  emptyText: { color: Colors.textSub, lineHeight: 20 },
});
