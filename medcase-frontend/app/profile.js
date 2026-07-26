import { View, Text, StyleSheet, SafeAreaView, Pressable, TextInput, ScrollView, Alert, ActivityIndicator, Platform } from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../src/theme/colors";
import { useState, useCallback } from "react";
import { getUserProfile, updateUserProfile, resetUserData } from "../src/api/endpoints";

export default function ProfilePage() {
  const router = useRouter();

  const [profile, setProfile] = useState(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [savedJustNow, setSavedJustNow] = useState(false);

  const fetchProfile = useCallback(() => {
    setLoading(true);
    getUserProfile()
      .then((data) => {
        setProfile(data);
        setFullName(data.full_name);
        setEmail(data.email);
      })
      .catch((e) => console.error("Profile load error:", e))
      .finally(() => setLoading(false));
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchProfile();
    }, [fetchProfile])
  );

  const isDirty = profile && (fullName !== profile.full_name || email !== profile.email);

  const handleSave = async () => {
    if (!isDirty || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await updateUserProfile(fullName.trim(), email.trim());
      setProfile(updated);
      setFullName(updated.full_name);
      setEmail(updated.email);
      setSavedJustNow(true);
      setTimeout(() => setSavedJustNow(false), 2000);
    } catch (e) {
      setSaveError("Could not save changes. Check the email format and try again.");
    } finally {
      setSaving(false);
    }
  };

  const doReset = async () => {
    try {
      await resetUserData();
      if (Platform.OS === "web") {
        window.alert("All practice data has been reset.");
      } else {
        Alert.alert("Done", "All practice data has been reset.");
      }
    } catch (e) {
      if (Platform.OS === "web") {
        window.alert("Could not reset data. Please try again.");
      } else {
        Alert.alert("Error", "Could not reset data. Please try again.");
      }
    }
  };

  const handleResetData = () => {
    const message =
      "This permanently deletes every chat session, message, answer, and progress record. " +
      "Your profile (name/email) is not affected. This cannot be undone.";

    // Alert.alert's multi-button form is a native-only API -- react-native-web
    // does not implement the buttons/callback behavior, so on web it would
    // silently do nothing when tapped. window.confirm is the web equivalent.
    if (Platform.OS === "web") {
      if (window.confirm(`Reset all practice data?\n\n${message}`)) {
        doReset();
      }
      return;
    }

    Alert.alert("Reset all practice data?", message, [
      { text: "Cancel", style: "cancel" },
      { text: "Reset Data", style: "destructive", onPress: doReset },
    ]);
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { justifyContent: "center", alignItems: "center" }]}>
        <ActivityIndicator color={Colors.accent} />
      </SafeAreaView>
    );
  }

  const initials = fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("") || "?";

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile Settings</Text>
      </View>

        {/* Profil Fotoğrafı Bölümü */}
        <View style={styles.avatarSection}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>{initials}</Text>
            <Pressable style={styles.editBadge} disabled>
              <Ionicons name="camera" size={16} color="white" />
            </Pressable>
          </View>
          <Text style={styles.userName}>{fullName || "—"}</Text>
          <Text style={styles.userSub}>{profile?.department}</Text>
        </View>

        {/* Kişisel Bilgiler Formu */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PERSONAL INFORMATION</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Full Name</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="person-outline" size={20} color="#64748B" />
              <TextInput
                style={styles.input}
                value={fullName}
                onChangeText={setFullName}
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Email Address</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="mail-outline" size={20} color="#64748B" />
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>
          </View>
        </View>

        {/* Akademik Bilgiler Formu */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ACADEMIC INFORMATION</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>University</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="business-outline" size={20} color="#64748B" />
              <TextInput style={styles.input} value={profile?.university} editable={false} />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Student ID</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="card-outline" size={20} color="#64748B" />
              <TextInput style={styles.input} value={profile?.student_id} editable={false} />
            </View>
          </View>
        </View>

        {/* Uygulama Ayarları / Aksiyonlar */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ACCOUNT MANAGEMENT</Text>

          <View style={[styles.actionRow, styles.actionRowDisabled]}>
            <View style={styles.actionLeft}>
              <Ionicons name="lock-closed-outline" size={22} color="#CBD5E1" />
              <Text style={[styles.actionText, styles.actionTextDisabled]}>Change Password</Text>
            </View>
            <View style={styles.soonBadge}>
              <Text style={styles.soonBadgeText}>Coming soon</Text>
            </View>
          </View>

          <View style={[styles.actionRow, styles.actionRowDisabled]}>
            <View style={styles.actionLeft}>
              <Ionicons name="notifications-outline" size={22} color="#CBD5E1" />
              <Text style={[styles.actionText, styles.actionTextDisabled]}>Notification Settings</Text>
            </View>
            <View style={styles.soonBadge}>
              <Text style={styles.soonBadgeText}>Coming soon</Text>
            </View>
          </View>

          <Pressable style={[styles.actionRow, { borderBottomWidth: 0 }]} onPress={handleResetData}>
            <View style={styles.actionLeft}>
              <Ionicons name="trash-outline" size={22} color={Colors.danger} />
              <Text style={[styles.actionText, { color: Colors.danger }]}>Reset Data</Text>
            </View>
          </Pressable>
        </View>

        {saveError && <Text style={styles.errorText}>{saveError}</Text>}
        {savedJustNow && <Text style={styles.savedText}>Saved.</Text>}

        <Pressable
          style={[styles.saveBtn, (!isDirty || saving) && styles.saveBtnDisabled]}
          onPress={handleSave}
          disabled={!isDirty || saving}
        >
          {saving
            ? <ActivityIndicator color="white" />
            : <Text style={styles.saveBtnText}>{isDirty ? "Save Changes" : "Saved"}</Text>}
        </Pressable>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  header: { marginBottom: 10 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#1E293B' },
  scrollContent: { padding: 20 },

  avatarSection: { alignItems: 'center', marginBottom: 30 },
  avatarCircle: { width: 90, height: 90, borderRadius: 45, backgroundColor: Colors.accent, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  avatarText: { color: 'white', fontSize: 32, fontWeight: '800' },
  editBadge: { position: 'absolute', bottom: 0, right: 0, backgroundColor: '#1E293B', width: 28, height: 28, borderRadius: 14, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: 'white', opacity: 0.5 },
  userName: { fontSize: 20, fontWeight: '800', color: '#1E293B', marginTop: 15 },
  userSub: { fontSize: 13, color: '#64748B', marginTop: 4 },

  section: { backgroundColor: 'white', borderRadius: 24, padding: 20, marginBottom: 20, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  sectionLabel: { fontSize: 11, fontWeight: '800', color: '#94A3B8', letterSpacing: 1, marginBottom: 15 },

  inputGroup: { marginBottom: 15 },
  inputLabel: { fontSize: 12, fontWeight: '700', color: '#475569', marginBottom: 8, marginLeft: 4 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F8FAFC', borderRadius: 12, paddingHorizontal: 12, borderWidth: 1, borderColor: '#F1F5F9' },
  input: { flex: 1, paddingVertical: 12, marginLeft: 10, fontSize: 14, color: '#1E293B', fontWeight: '600' },

  actionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  actionRowDisabled: { opacity: 0.7 },
  actionLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  actionText: { fontSize: 14, fontWeight: '600', color: '#475569' },
  actionTextDisabled: { color: '#CBD5E1' },
  soonBadge: { backgroundColor: '#F1F5F9', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  soonBadgeText: { fontSize: 10, fontWeight: '800', color: '#94A3B8', textTransform: 'uppercase' },

  errorText: { color: Colors.danger, fontSize: 13, fontWeight: '600', textAlign: 'center', marginBottom: 10 },
  savedText: { color: Colors.success, fontSize: 13, fontWeight: '700', textAlign: 'center', marginBottom: 10 },

  saveBtn: { backgroundColor: Colors.accent, padding: 16, borderRadius: 16, alignItems: 'center', marginTop: 10 },
  saveBtnDisabled: { backgroundColor: '#CBD5E1' },
  saveBtnText: { color: 'white', fontWeight: '700', fontSize: 15 }
});
