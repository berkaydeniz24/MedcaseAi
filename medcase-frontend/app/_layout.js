import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: "#F8FAFC" },
        headerTitleStyle: { fontWeight: "800", color: "#111827" },
        headerShadowVisible: false,
        headerTintColor: "#007AFF",
      }}
    >
      <Stack.Screen name="index" options={{ title: "MedCaseAI Dashboard" }} />
      <Stack.Screen name="case/[id]/index" options={{ title: "Patient Record" }} />
      <Stack.Screen name="case/[id]/chat" options={{ title: "Clinical Discussion" }} />
    </Stack>
  );
}