import { useEffect, useState, useMemo } from "react";
import { View, Text, FlatList, ActivityIndicator, StyleSheet, SafeAreaView, ScrollView, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { listCases, startDialogue } from "../src/api/endpoints";
import { CaseCard } from "../src/components/common/CaseCard";
import { Colors } from "../src/theme/colors";

const CATEGORIES = ["Hepsi", "Kardiyoloji", "Nöroloji", "Genel Dahiliye / Diğer", "Dermatoloji", "Ortopedi & Travmatoloji"];

// Durum etiketleri için yardımcı fonksiyon
const getStatusDetails = (status) => {
  switch (status) {
    case 'Çözüldü': 
      return { bg: '#DCFCE7', text: '#166534', label: 'Tamamlandı' };
    case 'Devam Ediyor': 
      return { bg: '#FEF9C3', text: '#854D0E', label: 'İşleniyor' };
    default: 
      return { bg: '#F1F5F9', text: '#475569', label: 'Çözülecek' };
  }
};

export default function HomePage() {
  const router = useRouter();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("Hepsi");

  useEffect(() => {
    // Backend'den gelen verilere 'status' simülasyonu ekliyoruz 
    // (Gerçek veride status varsa bu kısmı sadece setCases(res) yapabilirsin)
    listCases().then(res => {
      const enrichedCases = res.map(c => ({
        ...c,
        status: c.status || 'Çözülecek' // Varsayılan durum
      }));
      setCases(enrichedCases);
    }).finally(() => setLoading(false));
  }, []);

  const filteredCases = useMemo(() => {
    let result = cases;
    if (activeCategory !== "Hepsi") {
      result = result.filter(c => c.specialty === activeCategory);
    }
    // Önce çözülecek olanları, sonra devam edenleri gösteren bir sıralama
    return result.sort((a, b) => (a.status === 'Çözüldü' ? 1 : -1));
  }, [cases, activeCategory]);

  if (loading) return <ActivityIndicator size="large" color={Colors.accent} style={{ marginTop: 50 }} />;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.welcome}>Merhaba, Dr. Göktuğ</Text>
        <Text style={styles.title}>Vaka Kütüphanesi</Text>
      </View>

      <View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryContainer}>
          {CATEGORIES.map((cat) => (
            <Pressable 
              key={cat} 
              onPress={() => setActiveCategory(cat)}
              style={[styles.catBadge, activeCategory === cat && styles.catBadgeActive]}
            >
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
              {/* Vaka Kartı Üzerine Bindirilen Tag (Etiket) */}
              <View style={[styles.statusTag, { backgroundColor: status.bg }]}>
                <Text style={[styles.statusTagText, { color: status.text }]}>{status.label}</Text>
              </View>
            </View>
          );
        }}
        ListHeaderComponent={() => (
          <Pressable 
            style={styles.randomCard}
            onPress={async () => {
              const c = await startDialogue();
              router.push(`/case/${c.id}`);
            }}
          >
            <View style={styles.randomCardContent}>
              <View>
                <Text style={styles.randomTitle}>Hızlı Antrenman</Text>
                <Text style={styles.randomSub}>Rastgele bir vaka ile yeteneklerini test et.</Text>
              </View>
              <Text style={{fontSize: 30}}>🎯</Text>
            </View>
          </Pressable>
        )}
        contentContainerStyle={styles.list}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: { padding: 20 },
  welcome: { fontSize: 14, color: Colors.textSub, fontWeight: '500' },
  title: { fontSize: 28, fontWeight: '800', color: Colors.textMain },
  categoryContainer: { paddingHorizontal: 20, paddingBottom: 15, gap: 10 },
  catBadge: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12, backgroundColor: Colors.white, borderWidth: 1, borderColor: Colors.border },
  catBadgeActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  catText: { color: Colors.textSub, fontWeight: '600' },
  catTextActive: { color: Colors.white },
  list: { paddingHorizontal: 20, paddingBottom: 40 },
  
  cardContainer: { position: 'relative' },
  statusTag: { 
    position: 'absolute', 
    top: 12, 
    right: 12, 
    paddingHorizontal: 8, 
    paddingVertical: 4, 
    borderRadius: 6,
    zIndex: 10
  },
  statusTagText: { fontSize: 10, fontWeight: '800', textTransform: 'uppercase' },

  randomCard: { backgroundColor: Colors.accent, padding: 20, borderRadius: 24, marginBottom: 25, shadowColor: Colors.accent, shadowOpacity: 0.3, shadowRadius: 10, elevation: 5 },
  randomCardContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  randomTitle: { color: Colors.white, fontSize: 18, fontWeight: 'bold' },
  randomSub: { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 4 }
});