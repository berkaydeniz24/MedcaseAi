import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../src/theme/colors";

export default function RootLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors.accent,
        tabBarInactiveTintColor: "#94A3B8",
        tabBarStyle: { height: 65, paddingBottom: 10, backgroundColor: 'white' },
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Ana Sayfa",
          tabBarIcon: ({ color }) => <Ionicons name="home" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="cases"
        options={{
          title: "Vakalar",
          tabBarIcon: ({ color }) => <Ionicons name="medical" size={24} color={color} />,
        }}
      />
      
      {/* ✅ YENİ EKLENEN: GEÇMİŞ SEKMESİ */}
      <Tabs.Screen
        name="history"
        options={{
          title: "Geçmiş",
          tabBarIcon: ({ color }) => <Ionicons name="time-outline" size={24} color={color} />,
        }}
      />

      <Tabs.Screen
        name="stats" 
        options={{
          title: "Analiz",
          tabBarIcon: ({ color }) => <Ionicons name="analytics" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profil",
          tabBarIcon: ({ color }) => <Ionicons name="person" size={24} color={color} />,
        }}
      />
      
      {/* Tab menüde görünmeyen detay sayfaları */}
      <Tabs.Screen name="case/[id]/index" options={{ href: null }} />
      <Tabs.Screen name="case/[id]/chat" options={{ href: null }} />
    </Tabs>
  );
}