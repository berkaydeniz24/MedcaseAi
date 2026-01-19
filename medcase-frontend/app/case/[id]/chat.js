import { useState, useRef, useEffect } from "react";
import { 
  View, Text, TextInput, Pressable, FlatList, 
  KeyboardAvoidingView, Platform, ActivityIndicator, 
  StyleSheet, Modal, ScrollView 
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { chatDialogue, getCaseById } from "../../../src/api/endpoints";
import { Colors } from "../../../src/theme/colors";

export default function CaseChatPage() {
  const { id } = useLocalSearchParams();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [reportVisible, setReportVisible] = useState(false);
  const [isDiscussionClosed, setIsDiscussionClosed] = useState(false);
  const [caseData, setCaseData] = useState(null);
  
  // Mesajları ve önerileri yöneten state
  const [messages, setMessages] = useState([
    { role: "ai", text: "Dosyayı inceledim. Bu vaka hakkındaki analizini veya merak ettiğin tetkikleri paylaşabilirsin." }
  ]);
  const [followups, setFollowups] = useState([]);
  const flatListRef = useRef(null);

  useEffect(() => {
    getCaseById(String(id)).then(setCaseData).catch(console.error);
  }, [id]);

  const send = async (textFromChip) => {
    if (isDiscussionClosed) return; // Tartışma kapalıysa mesaj gönderilemez
    const text = (textFromChip ?? input).trim();
    if (!text || busy) return;

    setMessages(p => [...p, { role: "user", text }]);
    setInput("");
    setBusy(true);

    try {
      const res = await chatDialogue(String(id), text);
      setMessages(p => [...p, { role: "ai", text: res.answer || "Analiz tamamlandı." }]);
      setFollowups(res.followups || []);
    } catch (e) {
      setMessages(p => [...p, { role: "ai", text: "Bağlantı hatası oluştu." }]);
    } finally {
      setBusy(false);
    }
  };

  const closeDiscussion = () => {
    setIsDiscussionClosed(true);
    setFollowups([]); // Tartışma kapanınca önerileri temizle
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === "ios" ? "padding" : undefined} 
      keyboardVerticalOffset={100}
    >
      {/* Aksiyon Barı */}
      <View style={styles.topActionHeader}>
        <Pressable style={styles.viewReportBtn} onPress={() => setReportVisible(true)}>
          <Text style={styles.viewReportText}>📄 Rapor</Text>
        </Pressable>
        
        {!isDiscussionClosed ? (
          <Pressable style={styles.closeDiscussionBtn} onPress={closeDiscussion}>
            <Text style={styles.closeDiscussionText}>Tartışmayı Bitir</Text>
          </Pressable>
        ) : (
          <View style={styles.closedBadge}>
            <Text style={styles.closedBadgeText}>Tartışma Tamamlandı</Text>
          </View>
        )}
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(_, i) => String(i)}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd()}
        contentContainerStyle={styles.chatPadding}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === 'user' ? styles.userBubble : styles.aiBubble]}>
            <Text style={[styles.msgText, item.role === 'user' ? styles.userText : styles.aiText]}>
              {item.text}
            </Text>
          </View>
        )}
        ListFooterComponent={() => (
          /* Önerilen Sorular - Alt Alta Liste */
          followups.length > 0 && !busy && (
            <View style={styles.suggestionArea}>
              <Text style={styles.suggestionTitle}>Önerilen Sorular:</Text>
              {followups.map((f, i) => (
                <Pressable key={i} onPress={() => send(f)} style={styles.verticalChip}>
                  <Text style={styles.chipText}>{f}</Text>
                  <Text style={styles.chipArrow}>→</Text>
                </Pressable>
              ))}
            </View>
          )
        )}
      />

      {/* Giriş Alanı - Tartışma durumuna göre değişir */}
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
          <Pressable onPress={() => send()} style={[styles.sendBtn, !input.trim() && { opacity: 0.5 }]}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.sendText}>Gönder</Text>}
          </Pressable>
        </View>
      ) : (
        <View style={styles.discussionClosedFooter}>
          <Text style={styles.closedInfoText}>Bu klinik tartışma sonlandırılmıştır.</Text>
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
            <ScrollView><Text style={styles.reportText}>{caseData?.narrative}</Text></ScrollView>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  topActionHeader: { flexDirection: 'row', justifyContent: 'space-between', padding: 12, backgroundColor: Colors.white, borderBottomWidth: 1, borderBottomColor: Colors.border },
  viewReportBtn: { backgroundColor: '#F1F5F9', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  viewReportText: { color: Colors.accent, fontWeight: '700' },
  closeDiscussionBtn: { backgroundColor: '#FEE2E2', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  closeDiscussionText: { color: Colors.danger, fontWeight: '700' },
  closedBadge: { backgroundColor: '#E2E8F0', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 10 },
  closedBadgeText: { color: Colors.textSub, fontWeight: '700' },
  
  chatPadding: { padding: 16 },
  bubble: { padding: 14, borderRadius: 20, marginBottom: 12, maxWidth: '85%' },
  userBubble: { alignSelf: 'flex-end', backgroundColor: Colors.primary, borderBottomRightRadius: 4 },
  aiBubble: { alignSelf: 'flex-start', backgroundColor: Colors.white, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.border },
  msgText: { fontSize: 15, lineHeight: 22 },
  userText: { color: Colors.white },
  aiText: { color: Colors.textMain },

  suggestionArea: { marginTop: 10, marginBottom: 20 },
  suggestionTitle: { fontSize: 13, fontWeight: '800', color: Colors.textSub, marginBottom: 10, marginLeft: 5 },
  verticalChip: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    backgroundColor: Colors.white, 
    padding: 15, 
    borderRadius: 15, 
    marginBottom: 8, 
    borderWidth: 1, 
    borderColor: Colors.border,
    alignItems: 'center'
  },
  chipText: { color: Colors.textMain, fontSize: 14, fontWeight: '500', flex: 1 },
  chipArrow: { color: Colors.accent, fontWeight: 'bold', marginLeft: 10 },

  inputWrapper: { flexDirection: 'row', padding: 16, backgroundColor: Colors.white, borderTopWidth: 1, borderTopColor: Colors.border, alignItems: 'center', gap: 10 },
  input: { flex: 1, backgroundColor: Colors.background, borderRadius: 20, paddingHorizontal: 15, paddingVertical: 10, maxHeight: 100 },
  sendBtn: { backgroundColor: Colors.accent, paddingHorizontal: 20, paddingVertical: 10, borderRadius: 20 },
  sendText: { color: '#fff', fontWeight: 'bold' },
  
  discussionClosedFooter: { padding: 25, backgroundColor: '#F1F5F9', alignItems: 'center' },
  closedInfoText: { color: Colors.textSub, fontWeight: '600', fontStyle: 'italic' },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: Colors.white, borderRadius: 25, padding: 20, maxHeight: '80%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 15, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: '#eee' },
  modalTitle: { fontSize: 18, fontWeight: 'bold' },
  closeModalBtn: { color: Colors.danger, fontWeight: 'bold' },
  reportText: { fontSize: 15, lineHeight: 24, color: '#334155' }
});