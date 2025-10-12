import { apiFetch, API_BASE, getToken } from '../client';

export interface ChatItem {
  id: string;
  title: string;
  archived: boolean;
  pinned: boolean;
  created_at: number;
  updated_at: number;
}

export interface ChatModel extends ChatItem {
  user_id: string;
  chat: { role: string; content: string; timestamp?: number; data?: Record<string, any> }[];
  meta?: Record<string, any>;
  share_id?: string | null;
}

export async function listChats(): Promise<ChatItem[]> {
  return apiFetch('/api/chats');
}

export async function createChat(title: string): Promise<ChatModel> {
  return apiFetch('/api/chats', { method: 'POST', body: JSON.stringify({ title }) });
}

export async function getChat(id: string): Promise<ChatModel> {
  return apiFetch(`/api/chats/${id}`);
}

export async function deleteChat(id: string) {
  return apiFetch(`/api/chats/${id}`, { method: 'DELETE' });
}

export interface SendMessageOptions {
  model?: string;
  temperature?: number;
  api_base?: string;
  use_rag?: boolean;
  rag_top_k?: number;
  rag_temperature?: number;
}

export async function sendMessage(id: string, content: string, options: SendMessageOptions = {}) {
  return apiFetch(`/api/chats/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content, ...options })
  });
}

// Optional streaming via fetch to allow Authorization header
export interface StreamMessageOptions extends SendMessageOptions {}

export async function streamMessage(
  id: string,
  content: string,
  opts: StreamMessageOptions = {},
  onChunk?: (text: string) => void,
): Promise<void> {
  const url = new URL(`${API_BASE}/api/chats/${id}/stream`);
  url.searchParams.set('content', content);
  if (opts.model) url.searchParams.set('model', String(opts.model));
  if (opts.temperature != null) url.searchParams.set('temperature', String(opts.temperature));
  if (opts.use_rag) url.searchParams.set('use_rag', 'true');
  if (opts.rag_top_k != null) url.searchParams.set('rag_top_k', String(opts.rag_top_k));
  if (opts.rag_temperature != null) url.searchParams.set('rag_temperature', String(opts.rag_temperature));
  if (opts.api_base) url.searchParams.set('api_base', String(opts.api_base));

  const token = getToken();
  const headers: Record<string, string> = { Accept: 'text/event-stream' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers,
    // Ensure CORS preflight passes and streaming isn't buffered by caches
    cache: 'no-store',
    mode: 'cors'
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '');
    throw new Error(text || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split(/\r?\n/);
    buf = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        onChunk?.(data);
      }
    }
  }
}

// ============ Guest Chat API ============

export interface GuestChatRequest {
  content: string;
  messages: { role: string; content: string; timestamp?: number; data?: Record<string, any> }[];
  model?: string;
  temperature?: number;
  api_base?: string;
  use_rag?: boolean;
  rag_top_k?: number;
  rag_temperature?: number;
}

export interface GuestChatResponse {
  response: string;
  messages: { role: string; content: string; timestamp?: number; data?: Record<string, any> }[];
  data?: Record<string, any>;
}

export async function guestChat(request: GuestChatRequest): Promise<GuestChatResponse> {
  try {
    return await apiFetch('/api/chats/guest/chat', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  } catch (error) {
    console.error('Guest chat API error:', error);
    throw error;
  }
}

export async function guestChatStream(
  content: string,
  messages: { role: string; content: string; timestamp?: number; data?: Record<string, any> }[] = [],
  opts: StreamMessageOptions = {},
  onChunk?: (text: string) => void,
  onMessages?: (messages: { role: string; content: string; timestamp?: number; data?: Record<string, any> }[]) => void,
): Promise<void> {
  // Use two-segment path to avoid collision with `/api/chats/{chat_id}`
  const url = new URL(`${API_BASE}/api/chats/guest/stream`);
  url.searchParams.set('content', content);
  url.searchParams.set('messages', JSON.stringify(messages));
  if (opts.model) url.searchParams.set('model', String(opts.model));
  if (opts.temperature != null) url.searchParams.set('temperature', String(opts.temperature));
  if (opts.use_rag) url.searchParams.set('use_rag', 'true');
  if (opts.rag_top_k != null) url.searchParams.set('rag_top_k', String(opts.rag_top_k));
  if (opts.rag_temperature != null) url.searchParams.set('rag_temperature', String(opts.rag_temperature));
  if (opts.api_base) url.searchParams.set('api_base', String(opts.api_base));

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: { Accept: 'text/event-stream' },
    cache: 'no-store',
    mode: 'cors'
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '');
    console.error('Guest streaming API error:', res.status, text);
    throw new Error(text || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split(/\r?\n/);
    buf = lines.pop() || '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        
        // Check if it's a messages update
        try {
          const parsed = JSON.parse(data);
          if (parsed.type === 'messages' && onMessages) {
            onMessages(parsed.data);
          }
        } catch {
          // Regular text chunk
          onChunk?.(data);
        }
      }
    }
  }
}
