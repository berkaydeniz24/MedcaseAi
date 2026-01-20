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
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { chatDialogue, getCaseById } from "../../../src/api/endpoints";
import { Colors } from "../../../src/theme/colors";

const MODE_OPTIONS = [
  { id: "hint", label: "Hint", desc: "Yönlendirici ipuçları" },
  { id: "explain", label: "Explain", desc: "Neden-sonuç açıkla" },
  { id: "teach", label: "Teach", desc: "Mini ders gibi öğret" },
];

export default function CaseChatPage() {
  const { id } = useLocalSearchParams();

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [reportVisible, setReportVisible] = useState(false);
  const [isDiscussionClosed, setIsDiscussionClosed] = useState(false);
  const [caseData, setCaseData] = useState(null);

  // ✅ NEW: chat mode + user settings
  const [mode, setMode] = useState("hint"); // hint | explain | teach
  const [userLevel, setUserLevel] = useState("beginner"); // beginner | intermediate | advanced
  const [language, setLanguage] = useState("en"); // tr | en

  // Mesajları ve önerileri yöneten state
  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Dosyayı inceledim. Bu vaka hakkındaki analizini veya merak ettiğin tetkikleri paylaşabilirsin.",
    },
  ]);
  const [followups, setFollowups] = useState([]);
  const flatListRef = useRef(null);

  useEffect(() => {
    getCaseById(String(id)).then(setCaseData).catch(console.error);
  }, [id]);

  const send = async (textFromChip) => {
    if (isDiscussionClosed) return;
    const text = (textFromChip ?? input).trim();
    if (!text || busy) return;

    setMessages((p) => [...p, { role: "user", text }]);
    setInput("");
    setBusy(true);

    try {
      // ✅ UPDATED: mode gönderiyoruz
      const res = await chatDialogue(
        String(id),
        text,
        mode,
        userLevel,
        language,
      );

      const answerText =
        typeof res?.answer === "string"
          ? res.answer
          : JSON.stringify(res?.answer ?? "Analiz tamamlandı.");

      setMessages((p) => [...p, { role: "ai", text: answerText }]);
      setFollowups(res.followups || []);
    } catch (e) {
      setMessages((p) => [
        ...p,
        { role: "ai", text: "Bağlantı hatası oluştu." },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const closeDiscussion = () => {
    setIsDiscussionClosed(true);
    setFollowups([]);
  };

  const onChangeMode = (newMode) => {
    setMode(newMode);
    setFollowups([]); // mode değişince önceki followup'lar karışmasın
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={100}
    >
      {/* Aksiyon Barı */}
      <View style={styles.topActionHeader}>
        <Pressable
          style={styles.viewReportBtn}
          onPress={() => setReportVisible(true)}
        >
          <Text style={styles.viewReportText}>📄 Rapor</Text>
        </Pressable>

        {!isDiscussionClosed ? (
          <Pressable
            style={styles.closeDiscussionBtn}
            onPress={closeDiscussion}
          >
            <Text style={styles.closeDiscussionText}>Tartışmayı Bitir</Text>
          </Pressable>
        ) : (
          <View style={styles.closedBadge}>
            <Text style={styles.closedBadgeText}>Tartışma Tamamlandı</Text>
          </View>
        )}
      </View>

      {/* ✅ NEW: Mode Seçici */}
      <View style={styles.modeBar}>
        {MODE_OPTIONS.map((m) => {
          const active = mode === m.id;
          return (
            <Pressable
              key={m.id}
              onPress={() => onChangeMode(m.id)}
              style={[styles.modeChip, active && styles.modeChipActive]}
              disabled={busy}
            >
              <Text
                style={[
                  styles.modeChipText,
                  active && styles.modeChipTextActive,
                ]}
              >
                {m.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <Text style={styles.modeHintText}>
        Mod:{" "}
        <Text style={{ fontWeight: "800" }}>
          {MODE_OPTIONS.find((x) => x.id === mode)?.desc}
        </Text>
      </Text>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(_, i) => String(i)}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
        contentContainerStyle={styles.chatPadding}
        renderItem={({ item }) => (
          <View
            style={[
              styles.bubble,
              item.role === "user" ? styles.userBubble : styles.aiBubble,
            ]}
          >
            <Text
              style={[
                styles.msgText,
                item.role === "user" ? styles.userText : styles.aiText,
              ]}
            >
              {item.text}
            </Text>
          </View>
        )}
        ListFooterComponent={() =>
          followups.length > 0 &&
          !busy && (
            <View style={styles.suggestionArea}>
              <Text style={styles.suggestionTitle}>Önerilen Sorular:</Text>
              {followups.map((f, i) => (
                <Pressable
                  key={i}
                  onPress={() => send(f)}
                  style={styles.verticalChip}
                >
                  <Text style={styles.chipText}>{f}</Text>
                  <Text style={styles.chipArrow}>→</Text>
                </Pressable>
              ))}
            </View>
          )
        }
      />

      {/* Giriş Alanı */}
      {!isDiscussionClosed ? (
        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            placeholder="Analizini yaz..."
            value={input}
            onChangeText={setInput}
            multiline
            editable={!busy}
          />
          <Pressable
            onPress={() => send()}
            style={[styles.sendBtn, !input.trim() && { opacity: 0.5 }]}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.sendText}>Gönder</Text>
            )}
          </Pressable>
        </View>
      ) : (
        <View style={styles.discussionClosedFooter}>
          <Text style={styles.closedInfoText}>
            Bu klinik tartışma sonlandırılmıştır.
          </Text>
        </View>
      )}

      {/* Rapor Modalı */}
      <Modal visible={reportVisible} animationType="fade" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Klinik Dosya</Text>
              <Pressable onPress={() => setReportVisible(false)} hitSlop={20}>
                <Text style={styles.closeModalBtn}>Kapat</Text>
              </Pressable>
            </View>
            <ScrollView>
              <Text style={styles.reportText}>{caseData?.narrative}</Text>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },

  topActionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 12,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  viewReportBtn: {
    backgroundColor: "#F1F5F9",
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 10,
  },
  viewReportText: { color: Colors.accent, fontWeight: "700" },
  closeDiscussionBtn: {
    backgroundColor: "#FEE2E2",
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 10,
  },
  closeDiscussionText: { color: Colors.danger, fontWeight: "700" },
  closedBadge: {
    backgroundColor: "#E2E8F0",
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 10,
  },
  closedBadgeText: { color: Colors.textSub, fontWeight: "700" },

  // ✅ NEW mode bar
  modeBar: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 6,
    backgroundColor: Colors.background,
  },
  modeChip: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.white,
    alignItems: "center",
  },
  modeChipActive: {
    borderColor: Colors.primary,
    backgroundColor: "rgba(59, 130, 246, 0.08)",
  },
  modeChipText: { color: Colors.textSub, fontWeight: "800", fontSize: 12 },
  modeChipTextActive: { color: Colors.primary },

  modeHintText: {
    paddingHorizontal: 14,
    paddingBottom: 8,
    color: Colors.textSub,
    fontSize: 12,
  },

  chatPadding: { padding: 16 },
  bubble: { padding: 14, borderRadius: 20, marginBottom: 12, maxWidth: "85%" },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: Colors.primary,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    alignSelf: "flex-start",
    backgroundColor: Colors.white,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  msgText: { fontSize: 15, lineHeight: 22 },
  userText: { color: Colors.white },
  aiText: { color: Colors.textMain },

  suggestionArea: { marginTop: 10, marginBottom: 20 },
  suggestionTitle: {
    fontSize: 13,
    fontWeight: "800",
    color: Colors.textSub,
    marginBottom: 10,
    marginLeft: 5,
  },
  verticalChip: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: Colors.white,
    padding: 15,
    borderRadius: 15,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
  },
  chipText: {
    color: Colors.textMain,
    fontSize: 14,
    fontWeight: "500",
    flex: 1,
  },
  chipArrow: { color: Colors.accent, fontWeight: "bold", marginLeft: 10 },

  inputWrapper: {
    flexDirection: "row",
    padding: 16,
    backgroundColor: Colors.white,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    alignItems: "center",
    gap: 10,
  },
  input: {
    flex: 1,
    backgroundColor: Colors.background,
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    maxHeight: 100,
  },
  sendBtn: {
    backgroundColor: Colors.accent,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  sendText: { color: "#fff", fontWeight: "bold" },

  discussionClosedFooter: {
    padding: 25,
    backgroundColor: "#F1F5F9",
    alignItems: "center",
  },
  closedInfoText: {
    color: Colors.textSub,
    fontWeight: "600",
    fontStyle: "italic",
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    padding: 20,
  },
  modalContent: {
    backgroundColor: Colors.white,
    borderRadius: 25,
    padding: 20,
    maxHeight: "80%",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 15,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
  },
  modalTitle: { fontSize: 18, fontWeight: "bold" },
  closeModalBtn: { color: Colors.danger, fontWeight: "bold" },
  reportText: { fontSize: 15, lineHeight: 24, color: "#334155" },
});
