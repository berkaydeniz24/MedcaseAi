import { View, Text, Pressable, StyleSheet } from "react-native";
import { Colors } from "../../theme/colors";

const getDifficultyStyles = (level) => {
switch (level) {
case 'Easy': return { bg: '#DCFCE7', text: '#166534' };
case 'Medium': return { bg: '#FEF9C3', text: '#854D0E' };
case 'Hard': return { bg: '#FEE2E2', text: '#991B1B' };
default: return { bg: '#F1F5F9', text: '#475569' };
}
};

export const CaseCard = ({ item, onPress }) => {
const diffStyle = getDifficultyStyles(item.difficulty);

return (
<Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}>
<Text style={styles.specialtyTopText}>
{String(item.specialty || "General")}
</Text>

<Text style={styles.patientTitle}>
{item.title.split(" - ")[0]}
</Text>

<View style={styles.divider} />

<Text numberOfLines={2} style={styles.summary}>
{String(item.summary || "Tap to view clinic details…")}
</Text>
<View style={[styles.difficultyBadge, { backgroundColor: diffStyle.bg }]}>
<Text style={[styles.difficultyText, { color: diffStyle.text }]}>
{item.difficulty || "Medium"}
</Text>
</View>
</Pressable>
);
};

const styles = StyleSheet.create({
card: { backgroundColor: Colors.card, padding: 18, borderRadius: 24, marginBottom: 12, borderWidth: 1, borderColor: '#EDF2F7', elevation: 2 },
specialtyTopText: { fontSize: 11, fontWeight: '800', color: Colors.accent, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4, marginRight: 60},
patientTitle: { fontSize: 18, fontWeight: '700', color: Colors.textMain, marginBottom: 8 },
divider: { height: 1, backgroundColor: '#F1F5F9', marginBottom: 10, width: '80%' },
summary: { fontSize: 13, color: Colors.textSub, lineHeight: 18 },
difficultyBadge: { alignSelf: 'flex-start', marginTop: 12, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
difficultyText: { fontSize: 10, fontWeight: '800' }
});