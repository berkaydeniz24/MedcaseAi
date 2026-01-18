import { useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  Pressable,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { listCases, startDialogue } from "../src/api/endpoints";

export default function HomePage() {
  const router = useRouter();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    listCases()
      .then(setCases)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ActivityIndicator style={{ marginTop: 40 }} />;

  if (error) {
    return (
      <View style={{ padding: 20, gap: 10 }}>
        <Text style={{ color: "red" }}>{error}</Text>
        <Text style={{ color: "#6b7280" }}>
          IP doğru mu? (192.168.1.102) Backend açık mı? (/docs açılıyor mu?)
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, padding: 12 }}>
      <Pressable
        onPress={async () => {
          const c = await startDialogue();
          router.push(`/case/${c.id}`);
        }}
        style={{
          backgroundColor: "#111827",
          padding: 14,
          borderRadius: 12,
          marginBottom: 12,
        }}
      >
        <Text style={{ color: "white", textAlign: "center" }}>
          Start Random Case
        </Text>
      </Pressable>

      <FlatList
        data={cases}
        keyExtractor={(item, idx) => String(item.id ?? idx)}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => router.push(`/case/${item.id}`)}
            style={{
              padding: 14,
              borderRadius: 14,
              borderWidth: 1,
              borderColor: "#e5e7eb",
              marginBottom: 10,
              backgroundColor: "white",
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: "700" }}>
              {item.title ?? `Case ${item.id}`}
            </Text>

            {(item.specialty || item.difficulty) && (
              <Text style={{ marginTop: 4, color: "#374151" }}>
                {item.specialty ?? "General"} • {item.difficulty ?? "N/A"}
              </Text>
            )}

            {!!item.summary && (
              <Text style={{ marginTop: 6, color: "#6b7280" }}>
                {item.summary}
              </Text>
            )}
          </Pressable>
        )}
      />
    </View>
  );
}
