import { createFileRoute } from "@tanstack/react-router";
import { Dashboard } from "@/components/voice-agent/Dashboard";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Aura·01 — Voice Agent Console" },
      {
        name: "description",
        content:
          "Interactive console for Aura, a multilingual Hindi/English/Hinglish voice agent with 9 tools — weather, alarms, RAG, email, web search, and more.",
      },
    ],
  }),
});

function Index() {
  return <Dashboard />;
}
