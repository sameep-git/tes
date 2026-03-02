'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Loader2, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatPanel() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([
    { role: 'assistant', content: 'Hello Prof. Hawley. The Fall 2025 scheduling cycle is active. How can I help you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, activeTool, scrollToBottom]);

  const handleSend = async () => {
    if (!input.trim() || isThinking) return;

    const userMessage = input;
    setInput('');
    setIsThinking(true);
    setActiveTool(null);

    // Add user message and an empty assistant placeholder in one update
    setMessages(prev => [...prev, { role: 'user', content: userMessage }, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.body) throw new Error("No body returned");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages from buffer
        const parts = buffer.split('\n\n');
        // Keep the last part as it may be incomplete
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'tool_call') {
                setActiveTool(data.name);
              } else if (data.type === 'text') {
                setActiveTool(null);
                setMessages(prev => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last.role === 'assistant') {
                    updated[updated.length - 1] = { ...last, content: last.content + data.content };
                  }
                  return updated;
                });
              } else if (data.type === 'error') {
                setActiveTool(null);
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { role: 'assistant', content: `Error: ${data.content}` };
                  return updated;
                });
              } else if (data.type === 'done') {
                setIsThinking(false);
                setActiveTool(null);
              }
            } catch {
              // Ignore malformed JSON chunks
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content: 'Connection error. Make sure the FastAPI backend is running.' };
        return updated;
      });
    } finally {
      setIsThinking(false);
      setActiveTool(null);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-600" />
          <h2 className="font-semibold text-gray-800">TES Agent</h2>
        </div>
        <span className="flex h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]"></span>
      </div>

      {/* Messages — plain scrollable div instead of ScrollArea to avoid viewport issues */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 min-h-0">
        <div className="space-y-6 pb-4">
          {messages.map((msg, i) => {
            // Hide empty assistant placeholders while streaming
            if (msg.role === 'assistant' && msg.content === '' && i === messages.length - 1 && isThinking) {
              return null;
            }
            if (msg.content === '') return null;

            return (
              <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-indigo-100 text-indigo-700'}`}>
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${msg.role === 'user' ? 'bg-gray-800 text-white rounded-tr-none' : 'bg-gray-100 text-gray-800 rounded-tl-none'}`}>
                  {msg.role === 'assistant' ? (
                    <div className="chat-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            );
          })}

          {/* Thinking / Tool Execution Visibility Block */}
          {(isThinking || activeTool) && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center flex-shrink-0">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="bg-white border border-indigo-100 shadow-sm rounded-lg px-4 py-3 text-sm text-gray-600 flex flex-col gap-2 min-w-[200px]">
                {activeTool ? (
                  <div className="flex items-center gap-2 text-indigo-600 font-medium">
                    <Wrench className="w-4 h-4" />
                    <span>Executing <code className="bg-indigo-50 px-1.5 py-0.5 rounded text-xs border border-indigo-100">{activeTool}</code>...</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="flex space-x-1">
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></span>
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                    </span>
                    <span className="text-indigo-400 font-medium">Analyzing...</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Invisible scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input — always pinned at bottom */}
      <div className="p-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex flex-col gap-2"
        >
          <div className="flex items-center gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask TES Agent to do something..."
              className="flex-1 bg-white"
              disabled={isThinking}
            />
            <Button type="submit" size="icon" disabled={!input.trim() || isThinking} className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all">
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-center text-gray-400 mt-1 flex items-center justify-center gap-1">
            <Bot className="w-3 h-3" /> Agent can view and modify the database directly
          </p>
        </form>
      </div>
    </div>
  );
}