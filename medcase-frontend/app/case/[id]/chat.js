import { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  StyleSheet,
  Modal,
  ScrollView,
  SafeAreaView,
  Dimensions,
  Keyboard,
  Alert
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import Markdown from 'react-native-markdown-display'; 
import { Ionicons } from "@expo/vector-icons";

// API Fonksiyonları
import { sendChatMessage, getSessionMessages, getCaseById } from "../../../src/api/endpoints";
import { Colors } from "../../../src/theme/colors";

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// --- RENK VE EMOJİ KONFİGÜRASYONU ---
const MODE_CONFIG = {
  hint: {
    id: "hint",
    label: "Hint",
    desc: "Get a guiding clue",
    emoji: "💡",
    colors: { main: "#F59E0B", bg: "#FFFBEB", border: "#FCD34D", dark: "#B45309", btnBg: "#FEF3C7" }
  },
  explain: {
    id: "explain",
    label: "Explain",
    desc: "Understand the logic",
    emoji: "📖",
    colors: { main: "#0D9488", bg: "#F0FDFA", border: "#5EEAD4", dark: "#115E59", btnBg: "#CCFBF1" }
  },
  teach: {
    id: "teach",
    label: "Teach",
    desc: "Deep dive lesson",
    emoji: "🎓",
    colors: { main: "#8B5CF6", bg: "#F3E8FF", border: "#C4B5FD", dark: "#6D28D9", btnBg: "#EDE9FE" }
  }
};

const MODE_OPTIONS = [MODE_CONFIG.hint, MODE_CONFIG.explain, MODE_CONFIG.teach];

export default function CaseChatPage() {
  const { id, session_id } = useLocalSearchParams(); 
  const router = useRouter();

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false); 
  const [reportVisible, setReportVisible] = useState(false);
  const [isDiscussionClosed, setIsDiscussionClosed] = useState(false);
  const [caseData, setCaseData] = useState(null);

  // Session Yönetimi
  const [currentSessionId, setCurrentSessionId] = useState(session_id || null);

  // Ayarlar
  const [mode, setMode] = useState("hint"); 
  const [userLevel, setUserLevel] = useState("beginner"); 
  const [language, setLanguage] = useState("en"); 

  const [messages, setMessages] = useState([]);
  const [followups, setFollowups] = useState([]);
  const flatListRef = useRef(null);

  useEffect(() => {
    // Vaka verisini çek
    if (id) {
      getCaseById(String(id)).then(setCaseData).catch(err => console.error("Case Load Error:", err));
    }

    // --- BAŞLANGIÇ AYARLARI ---
    const initChat = async () => {
      setMessages([]); // Ekranı temizle
      setFollowups([]);
      setIsDiscussionClosed(false);

      if (session_id) {
        // Geçmişten geldiysek yükle
        setCurrentSessionId(session_id);
        await loadHistory(session_id);
      } else {
        // Yeni vakaysa varsayılan mesajı koy
        setCurrentSessionId(null);
        setMessages([
          {
            role: "ai",
            text: "I have reviewed the file. You can share your analysis or ask about specific tests.",
            mode: "neutral"
          },
        ]);
      }
    };

    initChat();

    // Klavye açılınca listeyi aşağı kaydır
    const keyboardDidShowListener = Keyboard.addListener('keyboardDidShow', () => {
        flatListRef.current?.scrollToEnd({ animated: true });
    });

    return () => {
      keyboardDidShowListener.remove();
    };
  }, [id, session_id]);

  // ✅ DÜZELTME: GEÇMİŞ MESAJLARI TARİHE GÖRE SIRALA
  const loadHistory = async (sessId) => {
    setLoadingHistory(true);
    try {
      const historyData = await getSessionMessages(sessId);
      if (historyData && Array.isArray(historyData)) {
        
        const formatted = historyData.map(msg => ({
          role: msg.role === 'user' ? 'user' : 'ai',
          text: msg.content,
          mode: 'neutral',
          createdAt: msg.timestamp // Sıralama için tarihi alıyoruz
        }))
        // Eskiden -> Yeniye sırala (Önce User, Sonra AI)
        .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
        
        setMessages(formatted);
      }
    } catch (e) {
      console.error("History load error:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const send = async (textFromChip) => {
    if (isDiscussionClosed) return;
    const text = (textFromChip ?? input).trim();
    if (!text || busy) return;

    // Kullanıcı mesajını ekle
    setMessages((p) => [...p, { role: "user", text }]);
    setInput("");
    setBusy(true);

    const currentMode = mode; 

    try {
      // Backend isteği
      const res = await sendChatMessage(
        String(id),
        text,
        currentMode,
        userLevel,
        language,
        currentSessionId
      );

      // Session ID güncelle (İlk mesajsa)
      if (res.session_id && !currentSessionId) {
        setCurrentSessionId(res.session_id);
      }

      const answerText = typeof res?.answer === "string" 
          ? res.answer 
          : JSON.stringify(res?.answer ?? "Analysis complete.");

      // AI Cevabını ekle
      setMessages((p) => [...p, { role: "ai", text: answerText, mode: currentMode }]);
      setFollowups(res.followups || []);
      
    } catch (e) {
      console.error("Chat Error:", e);
      setMessages((p) => [
        ...p,
        { role: "ai", text: "Connection error occurred. Please try again.", mode: "neutral" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const closeDiscussion = () => {
    setIsDiscussionClosed(true);
    setFollowups([]);
  };

  // Video roadmap item 6 ("Simülasyondan çıkış onayı"). Every message is
  // already persisted to the backend as it's sent (dbs.add_message per
  // turn) — there's nothing to actually lose here, so this is a
  // reassurance/intentionality prompt, not a data-loss warning, and only
  // shown once the student has actually engaged with the case.
  const handleExitPress = () => {
    if (messages.length <= 1) {
      router.back();
      return;
    }

    const title = "Exit this case?";
    const message = "Your progress is saved automatically — you can continue this case later from History.";

    // Alert.alert's multi-button form is native-only; react-native-web
    // doesn't implement it (same gap fixed in app/profile.js's Reset Data).
    if (Platform.OS === "web") {
      if (window.confirm(`${title}\n\n${message}`)) {
        router.back();
      }
      return;
    }

    Alert.alert(title, message, [
      { text: "Continue Case", style: "cancel" },
      { text: "Exit", style: "destructive", onPress: () => router.back() },
    ]);
  };

  const onChangeMode = (newMode) => {
    setMode(newMode);
    setFollowups([]);
  };

  const renderMessageContent = (item) => {
    if (item.role === 'ai') {
      return (
        <View style={{ width: '100%' }}>
          <Markdown style={markdownStyles}>
            {item.text}
          </Markdown>
        </View>
      );
    }
    return <Text style={styles.userText}>{item.text}</Text>;
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
            <Ionicons name="arrow-back" size={24} color="#333" onPress={handleExitPress} />
            <Text style={styles.headerTitle}>Case {id ? id.slice(-5) : ""}</Text>
            <View style={{ width: 24 }} />
      </View>

      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 100 : 0}
      >
        <View style={styles.topActionHeader}>
          <Pressable style={styles.viewReportBtn} onPress={() => setReportVisible(true)}>
            <Text style={styles.viewReportText}>📄 Report</Text>
          </Pressable>

          {!isDiscussionClosed ? (
            <Pressable style={styles.closeDiscussionBtn} onPress={closeDiscussion}>
              <Text style={styles.closeDiscussionText}>End Discussion</Text>
            </Pressable>
          ) : (
            <View style={styles.closedBadge}>
              <Text style={styles.closedBadgeText}>Completed</Text>
            </View>
          )}
        </View>

        <View style={styles.modeBar}>
          {MODE_OPTIONS.map((m) => {
            const active = mode === m.id;
            return (
              <Pressable
                key={m.id}
                onPress={() => onChangeMode(m.id)}
                style={({ pressed }) => [
                  styles.modeChip,
                  { 
                    backgroundColor: active ? m.colors.btnBg : Colors.white,
                    borderColor: active ? m.colors.main : Colors.border,
                    opacity: pressed ? 0.8 : 1,
                    transform: [{ scale: pressed ? 0.98 : 1 }]
                  }
                ]}
                disabled={busy}
              >
                <Text style={{ fontSize: 16 }}>{m.emoji}</Text>
                <Text style={[ styles.modeChipText, { color: active ? m.colors.dark : Colors.textSub } ]}>
                  {m.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        
        <Text style={styles.modeHintText}>
          Mode: <Text style={{ fontWeight: "800", color: MODE_CONFIG[mode].colors.dark }}>{MODE_CONFIG[mode].desc}</Text>
        </Text>

        {loadingHistory ? (
            <View style={{flex:1, justifyContent:'center', alignItems:'center'}}>
                <ActivityIndicator size="large" color={Colors.primary} />
                <Text style={{marginTop:10, color:Colors.textSub}}>Loading chat history...</Text>
            </View>
        ) : (
            <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(_, i) => String(i)}
            contentContainerStyle={styles.chatPadding}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            onLayout={() => flatListRef.current?.scrollToEnd({ animated: true })}
            keyboardDismissMode="on-drag"
            renderItem={({ item }) => {
                const isUser = item.role === "user";
                let bubbleStyle = styles.aiBubble;
                if (!isUser && item.mode && MODE_CONFIG[item.mode]) {
                    const conf = MODE_CONFIG[item.mode].colors;
                    bubbleStyle = { ...styles.aiBubble, backgroundColor: conf.bg, borderColor: conf.border };
                }
                return (
                <View style={[ styles.bubble, isUser ? styles.userBubble : bubbleStyle ]}>
                    {renderMessageContent(item)}
                </View>
                );
            }}
            ListFooterComponent={() =>
                followups.length > 0 && !busy && (
                <View style={styles.suggestionArea}>
                    <Text style={styles.suggestionTitle}>Suggested Questions:</Text>
                    {followups.map((f, i) => (
                    <Pressable key={i} onPress={() => send(f)} style={styles.verticalChip}>
                        <Text style={styles.chipText}>{f}</Text>
                        <Text style={styles.chipArrow}>→</Text>
                    </Pressable>
                    ))}
                </View>
                )
            }
            />
        )}

        {!isDiscussionClosed ? (
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="Type your analysis..."
              value={input}
              onChangeText={setInput}
              multiline
              editable={!busy}
            />
            <Pressable
              onPress={() => send()}
              style={[ styles.sendBtn, !input.trim() && { opacity: 0.5 }, { backgroundColor: MODE_CONFIG[mode].colors.main } ]}
            >
              {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.sendText}>Send</Text>}
            </Pressable>
          </View>
        ) : (
          <View style={styles.discussionClosedFooter}>
            <Text style={styles.closedInfoText}>This discussion has ended.</Text>
          </View>
        )}

        <Modal visible={reportVisible} animationType="fade" transparent={true}>
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Clinical File</Text>
                <Pressable onPress={() => setReportVisible(false)} hitSlop={20}>
                  <Text style={styles.closeModalBtn}>Close</Text>
                </Pressable>
              </View>
              <ScrollView>
                <Text style={styles.reportText}>{caseData?.narrative}</Text>
                {caseData?.source?.citation_text && (
                  <View style={styles.sourceBox}>
                    <Text style={styles.sourceLabel}>SOURCE</Text>
                    <Text style={styles.sourceText}>{caseData.source.citation_text}</Text>
                    {caseData.source.license_name && (
                      <Text style={styles.sourceLicense}>License: {caseData.source.license_name}</Text>
                    )}
                  </View>
                )}
              </ScrollView>
            </View>
          </View>
        </Modal>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// Styles (Aynen korundu)
const markdownStyles = {
  body: { fontSize: 15, lineHeight: 24, color: Colors.textMain, width: '100%' },
  paragraph: { flexWrap: 'wrap', marginBottom: 10, width: '100%' },
  list_item: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 6, width: '100%' },
  bullet_list: { marginBottom: 10, width: '100%' },
  heading1: { color: Colors.primary, fontWeight: 'bold', fontSize: 17, marginTop: 10 },
  heading2: { color: Colors.textMain, fontWeight: 'bold', fontSize: 16, marginTop: 8 },
  strong: { fontWeight: 'bold', color: '#000' },
};

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.white },
  container: { flex: 1, backgroundColor: Colors.background },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, backgroundColor: 'white', borderBottomWidth: 1, borderBottomColor: '#E2E8F0' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: '#1E293B' },
  topActionHeader: { flexDirection: "row", justifyContent: "space-between", padding: 12, backgroundColor: Colors.white, borderBottomWidth: 1, borderBottomColor: Colors.border },
  viewReportBtn: { backgroundColor: "#F1F5F9", paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  viewReportText: { color: Colors.accent, fontWeight: "700" },
  closeDiscussionBtn: { backgroundColor: "#FEE2E2", paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  closeDiscussionText: { color: Colors.danger, fontWeight: "700" },
  closedBadge: { backgroundColor: "#E2E8F0", paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  closedBadgeText: { color: Colors.textSub, fontWeight: "700" },
  modeBar: { flexDirection: "row", gap: 8, paddingHorizontal: 12, paddingTop: 12, paddingBottom: 6, backgroundColor: Colors.background },
  modeChip: { flex: 1, flexDirection: 'row', gap: 6, paddingVertical: 10, borderRadius: 14, borderWidth: 1, borderColor: Colors.border, backgroundColor: Colors.white, alignItems: "center", justifyContent: 'center' },
  modeChipText: { fontWeight: "800", fontSize: 13 },
  modeHintText: { paddingHorizontal: 14, paddingBottom: 8, color: Colors.textSub, fontSize: 12, fontStyle: 'italic' },
  chatPadding: { padding: 16, paddingBottom: 20 },
  bubble: { padding: 14, borderRadius: 20, marginBottom: 12 },
  userBubble: { alignSelf: "flex-end", backgroundColor: Colors.primary, borderBottomRightRadius: 4, maxWidth: "85%" },
  aiBubble: { alignSelf: "flex-start", backgroundColor: Colors.white, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.border, minWidth: SCREEN_WIDTH * 0.75, maxWidth: SCREEN_WIDTH * 0.90 },
  userText: { color: Colors.white, fontSize: 15 },
  suggestionArea: { marginTop: 10, marginBottom: 20 },
  suggestionTitle: { fontSize: 13, fontWeight: "800", color: Colors.textSub, marginBottom: 10, marginLeft: 5 },
  verticalChip: { flexDirection: "row", justifyContent: "space-between", backgroundColor: Colors.white, padding: 15, borderRadius: 15, marginBottom: 8, borderWidth: 1, borderColor: Colors.border, alignItems: "center" },
  chipText: { color: Colors.textMain, fontSize: 14, fontWeight: "500", flex: 1 },
  chipArrow: { color: Colors.accent, fontWeight: "bold", marginLeft: 10 },
  inputWrapper: { flexDirection: "row", padding: 16, backgroundColor: Colors.white, borderTopWidth: 1, borderTopColor: Colors.border, alignItems: "center", gap: 10 },
  input: { flex: 1, backgroundColor: Colors.background, borderRadius: 20, paddingHorizontal: 15, paddingVertical: 10, maxHeight: 100 },
  sendBtn: { paddingHorizontal: 20, paddingVertical: 10, borderRadius: 20 },
  sendText: { color: "#fff", fontWeight: "bold" },
  discussionClosedFooter: { padding: 25, backgroundColor: "#F1F5F9", alignItems: "center" },
  closedInfoText: { color: Colors.textSub, fontWeight: "600", fontStyle: "italic" },
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "center", padding: 20 },
  modalContent: { backgroundColor: Colors.white, borderRadius: 25, padding: 20, maxHeight: "80%" },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 15, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: "#eee" },
  modalTitle: { fontSize: 18, fontWeight: "bold" },
  closeModalBtn: { color: Colors.danger, fontWeight: "bold" },
  reportText: { fontSize: 15, lineHeight: 24, color: "#334155" },
  sourceBox: { marginTop: 20, paddingTop: 16, borderTopWidth: 1, borderTopColor: Colors.border },
  sourceLabel: { fontSize: 10, fontWeight: "800", color: Colors.textSub, letterSpacing: 1, marginBottom: 6 },
  sourceText: { fontSize: 12, lineHeight: 18, color: Colors.textSub },
  sourceLicense: { fontSize: 12, fontWeight: "700", color: Colors.accent, marginTop: 6 },
});