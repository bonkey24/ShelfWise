import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Bot,
  Send,
  AlertTriangle,
  TrendingUp,
  ShoppingCart,
  BarChart3,
  RotateCcw,
  AlertCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import api from '../api/client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  tools_used?: string[];
}

export const AssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputValue).trim();
    if (!text || isLoading) return;

    setError(null);
    const updatedMessages: ChatMessage[] = [...messages, { role: 'user', content: text }];
    setMessages(updatedMessages);
    setInputValue('');
    setIsLoading(true);

    try {
      // Send the entire conversation history (role & content only)
      const payload = {
        messages: updatedMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      };

      const res = await api.post<{ reply: string; tools_used: string[] }>(
        '/assistant/chat/',
        payload
      );

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.data.reply,
          tools_used: res.data.tools_used,
        },
      ]);
    } catch (err: any) {
      console.error('Chat error:', err);
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to get a response from the assistant.';
      setError(msg);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setError(null);
    setInputValue('');
    inputRef.current?.focus();
  };

  const suggestionChips = [
    {
      label: 'Which items will stock out soon?',
      icon: <AlertTriangle className="w-4 h-4 text-red-600" />,
      bg: 'bg-red-50 hover:bg-red-100 border-red-200',
    },
    {
      label: 'How is demand trending for S1097 P1?',
      icon: <TrendingUp className="w-4 h-4 text-blue-600" />,
      bg: 'bg-blue-50 hover:bg-blue-100 border-blue-200',
    },
    {
      label: 'What should I reorder this week?',
      icon: <ShoppingCart className="w-4 h-4 text-amber-600" />,
      bg: 'bg-amber-50 hover:bg-amber-100 border-amber-200',
    },
    {
      label: 'How accurate is the forecast?',
      icon: <BarChart3 className="w-4 h-4 text-emerald-600" />,
      bg: 'bg-emerald-50 hover:bg-emerald-100 border-emerald-200',
    },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] sm:h-[calc(100vh-8.5rem)] max-w-4xl mx-auto">
      {/* Top Bar Actions: Status chip & New Chat */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-200 shrink-0">
        <p className="text-xs text-slate-500">
          Ask questions about sales projections, stockout risks, or reorder quantities.
        </p>

        <div className="flex items-center gap-2 shrink-0">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            <span>Answers come from your forecast data</span>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleNewChat}
              className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
              title="Reset conversation"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>New chat</span>
            </button>
          )}
        </div>
      </section>

      {/* Main Chat Stream */}
      <div className="flex-1 overflow-y-auto py-6 px-1 space-y-6">
        {messages.length === 0 ? (
          /* Empty State */
          <div className="h-full flex flex-col items-center justify-center text-center my-auto px-4 py-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-700 via-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-md mb-4 ring-4 ring-blue-50">
              <Sparkles className="w-7 h-7" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Demand &amp; Inventory Intelligence Co-Pilot
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 max-w-md mt-1.5 leading-relaxed">
              Ask questions about sales projections, impending stockout risks, or purchase order
              quantities across all stores.
            </p>

            {/* Clickable Suggestion Chips */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl mt-8">
              {suggestionChips.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(chip.label)}
                  className="flex items-center gap-3 p-3.5 rounded-xl bg-white border border-slate-200 hover:border-blue-500 shadow-xs hover:shadow-sm text-left transition-all duration-150 group cursor-pointer"
                >
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${chip.bg}`}
                  >
                    {chip.icon}
                  </div>
                  <span className="text-xs font-medium text-slate-800 group-hover:text-blue-700 transition-colors leading-snug">
                    {chip.label}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Conversation Thread */
          messages.map((msg, index) => (
            <div key={index} className="w-full">
              {msg.role === 'user' ? (
                /* User Bubble */
                <div className="flex justify-end">
                  <div className="max-w-xl bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-br-sm shadow-xs text-sm leading-relaxed">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ) : (
                /* Assistant Message Card */
                <div className="flex items-start gap-3 w-full">
                  <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="flex-1 bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-5 shadow-xs text-slate-900 max-w-3xl overflow-hidden">
                    {/* Tool Badges */}
                    {msg.tools_used && msg.tools_used.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 mb-3 pb-2.5 border-b border-slate-100">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          Tools queried:
                        </span>
                        {msg.tools_used.map((tool) => (
                          <span
                            key={tool}
                            className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200"
                          >
                            {tool}()
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Markdown Body */}
                    <div className="prose prose-sm max-w-none text-slate-800 text-sm leading-relaxed space-y-3">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h3: ({ children }) => (
                            <h3 className="text-sm font-bold text-slate-900 mt-2 mb-1 flex items-center gap-1.5">
                              {children}
                            </h3>
                          ),
                          h4: ({ children }) => (
                            <h4 className="text-xs font-bold text-slate-900 mt-2 mb-1">
                              {children}
                            </h4>
                          ),
                          p: ({ children }) => (
                            <p className="text-xs sm:text-sm text-slate-800 leading-relaxed my-1.5">
                              {children}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="list-disc pl-5 my-2 space-y-1 text-xs sm:text-sm text-slate-800">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="list-decimal pl-5 my-2 space-y-1 text-xs sm:text-sm text-slate-800">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                          strong: ({ children }) => (
                            <strong className="font-semibold text-slate-900">{children}</strong>
                          ),
                          blockquote: ({ children }) => (
                            <blockquote className="p-2.5 rounded-lg bg-slate-50 border-l-3 border-blue-500 text-xs text-slate-600 italic my-2">
                              {children}
                            </blockquote>
                          ),
                          table: ({ children }) => (
                            <div className="overflow-x-auto my-3 border border-slate-200 rounded-lg shadow-2xs">
                              <table className="w-full text-left text-xs divide-y divide-slate-200">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }) => (
                            <thead className="bg-slate-50 text-slate-700 font-semibold uppercase tracking-wider text-[10px]">
                              {children}
                            </thead>
                          ),
                          tbody: ({ children }) => (
                            <tbody className="divide-y divide-slate-100 bg-white">
                              {children}
                            </tbody>
                          ),
                          tr: ({ children }) => (
                            <tr className="hover:bg-slate-50/80 transition-colors">{children}</tr>
                          ),
                          th: ({ children }) => <th className="px-3 py-2 font-bold">{children}</th>,
                          td: ({ children }) => (
                            <td className="px-3 py-2 font-mono text-slate-800">{children}</td>
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading / Typing Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 w-full">
            <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs shrink-0 mt-0.5">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-4 shadow-xs flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
              <span className="text-xs text-slate-500 font-medium">
                Querying forecast data and generating recommendation...
              </span>
            </div>
          </div>
        )}

        {/* Error Alert Banner */}
        {error && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-xs font-semibold underline hover:text-red-900 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar Fixed/Sticky at Bottom */}
      <footer className="pt-3 pb-2 bg-slate-50 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="relative flex items-center rounded-xl border border-slate-300 bg-white shadow-xs focus-within:ring-2 focus-within:ring-blue-600 focus-within:border-transparent transition-all"
        >
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Ask a question about sales, stockouts, or reorder quantities..."
            className="w-full pl-4 pr-12 py-3 text-xs sm:text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none bg-transparent"
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="absolute right-2 p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-xs"
            title="Send query"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
        <p className="text-[10px] text-center text-slate-400 mt-2">
          Grounded in actual retail sales &amp; LightGBM forecasts · Inventory stock levels are simulated demo data
        </p>
      </footer>
    </div>
  );
};

export default AssistantPage;
