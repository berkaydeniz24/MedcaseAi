import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "MedCaseAI" }} />
      <Stack.Screen name="case/[id]/index" options={{ title: "Case Detail" }} />
      <Stack.Screen name="case/[id]/chat" options={{ title: "Case Chat" }} />
    </Stack>
  );
}
