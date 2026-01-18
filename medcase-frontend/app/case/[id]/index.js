import { useEffect, useState } from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { getCaseById } from "../../../src/api/endpoints";

export default function CaseDetailPage() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getCaseById(String(id))
      .then(setCaseData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <ActivityIndicator style={{ marginTop: 40 }} />;

  if (error) {
    return (
      <View style={{ padding: 20 }}>
        <Text style={{ color: "red" }}>{error}</Text>
      </View>
    );
  }

  if (!caseData) {
    return (
      <View style={{ padding: 20 }}>
        <Text>Case not found.</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 14, gap: 10 }}>
      <Text style={{ fontSize: 18, fontWeight: "800" }}>
        {caseData.title ?? `Case ${id}`}
      </Text>

      {(caseData.specialty || caseData.difficulty) && (
        <Text style={{ color: "#374151" }}>
          {caseData.specialty ?? "General"} • {caseData.difficulty ?? "N/A"}
        </Text>
      )}

      {!!caseData.narrative && (
        <Text style={{ color: "#111827", lineHeight: 20 }}>
          {caseData.narrative}
        </Text>
      )}

      <Pressable
        onPress={() => router.push(`/case/${id}/chat`)}
        style={{
          backgroundColor: "#111827",
          padding: 12,
          borderRadius: 12,
          marginTop: 10,
        }}
      >
        <Text style={{ color: "white", textAlign: "center" }}>
          Open Chat
        </Text>
      </Pressable>
    </ScrollView>
  );
}
