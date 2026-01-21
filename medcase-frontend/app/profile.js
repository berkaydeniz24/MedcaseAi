import { View, Text, StyleSheet, SafeAreaView, Pressable, TextInput, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../src/theme/colors";
import { useState } from "react";

export default function ProfilePage() {
  const router = useRouter();

  // Kullanıcı verileri (İleride SQLite veya Auth sisteminden gelecek)
  const [userInfo, setUserInfo] = useState({
    fullName: "John Doe",
    email: "john.doe@email.com",
    university: "Biruni University",
    department: "Medicine",
    studentId: "123456789"
  });

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
        <Text style={styles.headerTitle}>Profil Ayarları</Text>
      </View>

        {/* Profil Fotoğrafı Bölümü */}
        <View style={styles.avatarSection}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>JD</Text>
            <Pressable style={styles.editBadge}>
              <Ionicons name="camera" size={16} color="white" />
            </Pressable>
          </View>
          <Text style={styles.userName}>{userInfo.fullName}</Text>
          <Text style={styles.userSub}>{userInfo.department}</Text>
        </View>

        {/* Kişisel Bilgiler Formu */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>KİŞİSEL BİLGİLER</Text>
          
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Ad Soyad</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="person-outline" size={20} color="#64748B" />
              <TextInput 
                style={styles.input} 
                value={userInfo.fullName} 
                onChangeText={(txt) => setUserInfo({...userInfo, fullName: txt})}
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>E-Posta Adresi</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="mail-outline" size={20} color="#64748B" />
              <TextInput 
                style={styles.input} 
                value={userInfo.email}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>
          </View>
        </View>

        {/* Akademik Bilgiler Formu */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>AKADEMİK BİLGİLER</Text>
          
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Üniversite</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="business-outline" size={20} color="#64748B" />
              <TextInput style={styles.input} value={userInfo.university} editable={false} />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>Öğrenci No</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="card-outline" size={20} color="#64748B" />
              <TextInput style={styles.input} value={userInfo.studentId} editable={false} />
            </View>
          </View>
        </View>

        {/* Uygulama Ayarları / Aksiyonlar */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>HESAP YÖNETİMİ</Text>
          
          <Pressable style={styles.actionRow}>
            <View style={styles.actionLeft}>
              <Ionicons name="lock-closed-outline" size={22} color="#475569" />
              <Text style={styles.actionText}>Şifre Değiştir</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#CBD5E1" />
          </Pressable>

          <Pressable style={styles.actionRow}>
            <View style={styles.actionLeft}>
              <Ionicons name="notifications-outline" size={22} color="#475569" />
              <Text style={styles.actionText}>Bildirim Ayarları</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#CBD5E1" />
          </Pressable>

          <Pressable style={[styles.actionRow, { borderBottomWidth: 0 }]}>
            <View style={styles.actionLeft}>
              <Ionicons name="trash-outline" size={22} color={Colors.danger} />
              <Text style={[styles.actionText, { color: Colors.danger }]}>Verileri Sıfırla</Text>
            </View>
          </Pressable>
        </View>

        <Pressable style={styles.saveBtn}>
          <Text style={styles.saveBtnText}>Değişiklikleri Kaydet</Text>
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
  editBadge: { position: 'absolute', bottom: 0, right: 0, backgroundColor: '#1E293B', width: 28, height: 28, borderRadius: 14, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: 'white' },
  userName: { fontSize: 20, fontWeight: '800', color: '#1E293B', marginTop: 15 },
  userSub: { fontSize: 13, color: '#64748B', marginTop: 4 },

  section: { backgroundColor: 'white', borderRadius: 24, padding: 20, marginBottom: 20, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  sectionLabel: { fontSize: 11, fontWeight: '800', color: '#94A3B8', letterSpacing: 1, marginBottom: 15 },
  
  inputGroup: { marginBottom: 15 },
  inputLabel: { fontSize: 12, fontWeight: '700', color: '#475569', marginBottom: 8, marginLeft: 4 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F8FAFC', borderRadius: 12, paddingHorizontal: 12, borderWidth: 1, borderColor: '#F1F5F9' },
  input: { flex: 1, paddingVertical: 12, marginLeft: 10, fontSize: 14, color: '#1E293B', fontWeight: '600' },

  actionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  actionLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  actionText: { fontSize: 14, fontWeight: '600', color: '#475569' },

  saveBtn: { backgroundColor: Colors.accent, padding: 16, borderRadius: 16, alignItems: 'center', marginTop: 10 },
  saveBtnText: { color: 'white', fontWeight: '700', fontSize: 15 }
});