import { View, Text, Pressable, StyleSheet } from "react-native";
import { Colors } from "../../theme/colors";

export const CaseCard = ({ item, onPress }) => (
  <Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && { opacity: 0.8 }]}>
    <View style={styles.headerRow}>
      <View style={[styles.badge, { backgroundColor: item.difficulty === 'Zor' ? '#FEE2E2' : '#DCFCE7' }]}>
        <Text style={[styles.badgeText, { color: item.difficulty === 'Zor' ? Colors.danger : Colors.success }]}>
          {String(item.difficulty || "Orta")}
        </Text>
      </View>
      <Text style={styles.specialty}>{String(item.specialty || "Genel")}</Text>
    </View>
    <Text style={styles.title}>{String(item.title || "Adsız Vaka")}</Text>
    <Text numberOfLines={2} style={styles.summary}>{String(item.summary || "Detaylar için tıklayın...")}</Text>
  </Pressable>
);

const styles = StyleSheet.create({
  card: { backgroundColor: Colors.card, padding: 16, borderRadius: 20, marginBottom: 12, borderWidth: 1, borderColor: '#E2E8F0' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  badge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  badgeText: { fontSize: 11, fontWeight: '800', textTransform: 'uppercase' },
  specialty: { fontSize: 12, color: Colors.accent, fontWeight: '600' },
  title: { fontSize: 17, fontWeight: '700', color: Colors.textMain },
  summary: { fontSize: 13, color: Colors.textSub, marginTop: 6, lineHeight: 18 }
});