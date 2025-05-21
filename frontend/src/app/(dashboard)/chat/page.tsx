import ChatLayout from '@/components/layouts/chat-layout';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Chat - TripSage',
  description: 'Chat with TripSage AI to plan your trips',
};

export default function ChatPage() {
  return (
    <ChatLayout>
      <div className="flex flex-col items-center justify-center h-full">
        <div className="max-w-md text-center">
          <h2 className="text-2xl font-bold mb-2">Welcome to TripSage Chat</h2>
          <p className="text-muted-foreground mb-4">
            Ask me anything about trip planning, destinations, flights, accommodations, or travel tips.
          </p>
          <div className="grid grid-cols-2 gap-3 mt-6">
            <SuggestionButton text="Plan a trip to Japan" />
            <SuggestionButton text="Find budget flights to Europe" />
            <SuggestionButton text="Best time to visit Bali" />
            <SuggestionButton text="Family-friendly hotels in NYC" />
          </div>
        </div>
      </div>
    </ChatLayout>
  );
}

function SuggestionButton({ text }: { text: string }) {
  return (
    <button 
      className="p-3 text-sm bg-secondary/50 hover:bg-secondary rounded-lg text-left"
    >
      {text}
    </button>
  );
}