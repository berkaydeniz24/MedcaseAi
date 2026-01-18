import { useMemo, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { chatDialogue } from "../../../src/api/endpoints";

export default function CaseChatPage() {
  const { id } = useLocalSearchParams(); // burada id = CASE ID olacak

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const [messages, setMessages] = useState([
    { role: "ai", text: "Hi! Ask me your first question about this case." },
  ]);

  const [followups, setFollowups] = useState([]);

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy]);

  const send = async (textFromChip) => {
    const text = (textFromChip ?? input).trim();
    if (!text || busy) return;

    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setBusy(true);
    setFollowups([]);

    try {
      const res = await chatDialogue(String(id), text); // backend /dialogue/{id}/chat case id ile çalışıyorsa OK
      const answer = res?.answer ?? "No answer returned.";
      const fu = Array.isArray(res?.followups) ? res.followups : [];
      setMessages((prev) => [...prev, { role: "ai", text: answer }]);
      setFollowups(fu);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "ai", text: `Error: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <FlatList
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 12, paddingBottom: 16 }}
        data={messages}
        keyExtractor={(_, idx) => String(idx)}
        renderItem={({ item }) => (
          <View
            style={{
              alignSelf: item.role === "user" ? "flex-end" : "flex-start",
              backgroundColor: item.role === "user" ? "#111827" : "#f3f4f6",
              paddingVertical: 10,
              paddingHorizontal: 12,
              borderRadius: 14,
              marginBottom: 8,
              maxWidth: "85%",
            }}
          >
            <Text style={{ color: item.role === "user" ? "white" : "#111827" }}>
              {item.text}
            </Text>
          </View>
        )}
      />

      {followups.length > 0 && (
        <View style={{ paddingHorizontal: 12, paddingBottom: 10 }}>
          <Text style={{ color: "#6b7280", marginBottom: 6 }}>Suggestions</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {followups.slice(0, 6).map((f, idx) => (
              <Pressable
                key={idx}
                onPress={() => send(f)}
                style={{
                  paddingVertical: 8,
                  paddingHorizontal: 10,
                  borderRadius: 999,
                  backgroundColor: "#e5e7eb",
                }}
                disabled={busy}
              >
                <Text style={{ color: "#111827" }}>{f}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      <View
        style={{
          flexDirection: "row",
          gap: 8,
          padding: 12,
          borderTopWidth: 1,
          borderTopColor: "#e5e7eb",
          alignItems: "center",
        }}
      >
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder={busy ? "Thinking..." : "Type a message"}
          editable={!busy}
          style={{
            flex: 1,
            borderWidth: 1,
            borderColor: "#e5e7eb",
            borderRadius: 14,
            paddingHorizontal: 12,
            paddingVertical: 10,
            backgroundColor: "white",
          }}
        />

        <Pressable
          onPress={() => send()}
          disabled={!canSend}
          style={{
            paddingHorizontal: 14,
            paddingVertical: 10,
            borderRadius: 14,
            backgroundColor: canSend ? "#111827" : "#9ca3af",
          }}
        >
          {busy ? <ActivityIndicator /> : <Text style={{ color: "white" }}>Send</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
