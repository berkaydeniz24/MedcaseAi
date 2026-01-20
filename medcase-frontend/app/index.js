import { View, Text, StyleSheet, SafeAreaView, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { Colors } from "../src/theme/colors";
import { startDialogue } from "../src/api/endpoints";
import { setLastSession } from "../src/api/session_cache";
import { Ionicons } from "@expo/vector-icons";

export default function HomeScreen() {
  const router = useRouter();

  const handleQuickTraining = async () => {
    try {
      const res = await startDialogue();
      setLastSession(res);
      router.push(`/case/${res.case.id}?session_id=${res.session_id}`);
    } catch (e) {
      console.log("Quick training error:", e);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.welcome}>Welcome back,</Text>
          <Text style={styles.name}>Dr. Göktuğ Varan</Text>
          <Text style={styles.university}>Biruni University</Text>
        </View>

        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Ready for today's practice?</Text>
          <Text style={styles.infoSub}>Improve your clinical reasoning with AI-supported medical cases.</Text>
        </View>

        <Pressable style={styles.randomCard} onPress={handleQuickTraining}>
          <View style={styles.randomCardContent}>
            <View style={{ flex: 1 }}>
              <Text style={styles.randomTitle}>Quick Training</Text>
              <Text style={styles.randomSub}>Start a random case analysis now.</Text>
            </View>
            <View style={styles.iconCircle}>
              <Ionicons name="flash" size={28} color="white" />
            </View>
          </View>
        </Pressable>

        <View style={styles.statsOverview}>
            <View style={styles.miniStat}>
                <Ionicons name="checkmark-done" size={20} color={Colors.success} />
                <Text style={styles.statLabel}>Daily Goal: 3/5</Text>
            </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: 25, flex: 1, justifyContent: 'center' },
  header: { marginBottom: 40 },
  welcome: { fontSize: 18, color: Colors.textSub, fontWeight: "500" },
  name: { fontSize: 32, fontWeight: "800", color: Colors.textMain, marginTop: 4 },
  university: { fontSize: 14, color: Colors.accent, fontWeight: "600", marginTop: 4 },
  infoCard: { marginBottom: 30 },
  infoTitle: { fontSize: 20, fontWeight: "700", color: Colors.textMain },
  infoSub: { fontSize: 15, color: Colors.textSub, marginTop: 8, lineHeight: 22 },
  randomCard: { backgroundColor: Colors.accent, padding: 25, borderRadius: 30, elevation: 8, shadowColor: Colors.accent, shadowOpacity: 0.3, shadowRadius: 15 },
  randomCardContent: { flexDirection: "row", alignItems: "center" },
  randomTitle: { color: "white", fontSize: 22, fontWeight: "800" },
  randomSub: { color: "rgba(255,255,255,0.8)", fontSize: 14, marginTop: 4 },
  iconCircle: { width: 50, height: 50, borderRadius: 25, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center' },
  statsOverview: { marginTop: 30, alignItems: 'center' },
  miniStat: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: 'white', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12, borderWidth: 1, borderColor: '#EDF2F7' },
  statLabel: { fontSize: 14, fontWeight: "700", color: Colors.textMain }
});