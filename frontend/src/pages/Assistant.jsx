import React, { useState } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

const Assistant = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I can help with flights, hotels and restaurants. Ask me anything.' }
  ]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!text.trim()) return;
    const newMsgs = [...messages, { role: 'user', content: text }];
    setMessages(newMsgs);
    setText('');
    setLoading(true);
    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMsgs })
      });
      const json = await res.json();
      const answer = json.answer || 'Sorry, I could not answer that.';
      setMessages([...newMsgs, { role: 'assistant', content: answer }]);
    } catch (e) {
      setMessages([...newMsgs, { role: 'assistant', content: 'Error contacting assistant.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold mb-4">WanderLite Assistant</h1>
        <Card className="p-4 h-[65vh] overflow-y-auto space-y-3 bg-white">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`${m.role === 'user' ? 'bg-sky-500 text-white' : 'bg-gray-100 text-gray-900'} px-3 py-2 rounded-lg max-w-[80%] whitespace-pre-line`}>{m.content}</div>
            </div>
          ))}
        </Card>
        <div className="mt-4 flex gap-2">
          <Input placeholder="Ask about flights, hotels, restaurants..." value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') send(); }} />
          <Button onClick={send} disabled={loading}>{loading ? 'Thinking…' : 'Send'}</Button>
        </div>
      </div>
    </div>
  );
};

export default Assistant;


