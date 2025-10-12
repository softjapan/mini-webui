<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import MessageList from '$lib/components/chat/MessageList.svelte';
    import MessageInput from '$lib/components/chat/MessageInput.svelte';
    import GuestMessageInput from '$lib/components/chat/GuestMessageInput.svelte';
    import { listChats, createChat, getChat, deleteChat, guestChat, guestChatStream } from '$lib/apis/chats';
    import { isGuest, setGuestMode, clearAuth, isAuthenticated } from '$lib/stores';

    type ChatMessage = { role: string; content: string; timestamp?: number; data?: Record<string, any> };
    let cidCounter = 0;
    const nextCid = () => (++cidCounter).toString();

    let chats: any[] = [];
    let selectedChatId: string | null = null;
    let messages: ChatMessage[] = [];
    let streaming = true;
    let useRag = false;
    let ragTopK = 4;
    let ragTemperature = 0.3;
    let pendingAssistantIndex: number | null = null;
    let isGuestMode = false;
    let ignoreFinalGuestSse: boolean = false;

    $: if (useRag) {
        streaming = false;
    }

    const defaultChatTitle = () => `Chat ${new Date().toLocaleString()}`;

    async function loadChat(id: string) {
        selectedChatId = id;
        const chat = await getChat(id);
        messages = chat.chat || [];
        pendingAssistantIndex = null;
    }

    async function refreshChats(preferId?: string) {
        chats = await listChats();
        if (chats.length === 0) {
            messages = [];
            pendingAssistantIndex = null;
            if (!selectedChatId) {
                selectedChatId = null;
            } else if (!chats.find((c) => c.id === selectedChatId)) {
                selectedChatId = null;
            }
            return;
        }

        const nextId = preferId && chats.find((c) => c.id === preferId)
            ? preferId
            : selectedChatId && chats.find((c) => c.id === selectedChatId)
                ? selectedChatId
                : chats[0].id;
        if (!selectedChatId || selectedChatId !== nextId) {
            selectedChatId = nextId;
        }
        await loadChat(nextId);
    }

    async function getOrCreateChat(): Promise<string | null> {
        if (selectedChatId) {
            return selectedChatId;
        }
        if (isGuestMode) {
            // Guests cannot create persistent chats
            return null;
        }
        const created = await createChat(defaultChatTitle());
        await refreshChats(created.id);
        return created.id;
    }

    async function handleCreate() {
        const title = prompt('Chat title?', defaultChatTitle());
        if (!title) return;
        const c = await createChat(title);
        await refreshChats(c.id);
    }

    onMount(() => {
        (async () => {
            // Check if user is in guest mode
            isGuestMode = $isGuest;
            
            if (isGuestMode) {
                // Guest mode: no persistent chats, start with empty messages
                messages = [];
                chats = [];
                selectedChatId = null;
            } else {
                // Authenticated mode: load chats
                await refreshChats();
                if (!selectedChatId) {
                    await getOrCreateChat();
                }
            }
        })();
    });

    // React to changes in guest mode
    $: if ($isGuest !== isGuestMode) {
        isGuestMode = $isGuest;
        if (isGuestMode) {
            // Switching to guest mode: clear messages and chats
            messages = [];
            chats = [];
            selectedChatId = null;
        } else {
            // Switching to authenticated mode: load chats
            refreshChats().then(() => {
                if (!selectedChatId) {
                    getOrCreateChat();
                }
            });
        }
    }

    // React to authentication changes
    $: if ($isAuthenticated && !$isGuest && isGuestMode) {
        // User just logged in from guest mode
        isGuestMode = false;
        refreshChats().then(() => {
            if (!selectedChatId) {
                getOrCreateChat();
            }
        });
    }

    function handleSent(event: CustomEvent<{ chatId?: string }>) {
        const id = event.detail?.chatId ?? selectedChatId;
        if (id) {
            refreshChats(id).catch((err) => console.error(err));
        }
    }

    async function handleGuestSent(event: CustomEvent<{ content: string }>) {
        const content = event.detail?.content;
        if (!content) return;

        if (streaming && !useRag) {
            // Guest streaming
            let acc = '';
            const nowSec = Math.floor(Date.now() / 1000);
            const currentMessages = [...messages, { role: 'user', content, timestamp: nowSec, cid: nextCid() } as any];
            messages = currentMessages;
            // insert a placeholder with a marker
            const placeholder = { role: 'assistant', content: '', __placeholder: true, cid: nextCid() } as any;
            pendingAssistantIndex = messages.push(placeholder) - 1;
            messages = [...messages];
            ignoreFinalGuestSse = false;

            try {
                await guestChatStream(
                    content,
                    currentMessages.slice(0, -1), // Exclude the user message we just added
                    {
                        use_rag: useRag,
                        rag_top_k: ragTopK,
                        rag_temperature: ragTemperature,
                    },
                    (chunk) => {
                        acc += chunk;
                        if (pendingAssistantIndex != null) {
                            messages[pendingAssistantIndex].content = acc;
                            messages = [...messages];
                        }
                    },
                    (updatedMessages) => {
                        if (ignoreFinalGuestSse) {
                            // fallback で確定反映済み。プレースホルダをクリーンアップして終了
                            pendingAssistantIndex = null;
                            ignoreFinalGuestSse = false;
                            return;
                        }
                        // Avoid duplicates: replace only the placeholder if exists
                        if (pendingAssistantIndex != null && messages[pendingAssistantIndex]?.__placeholder) {
                            const finalTwo = updatedMessages.slice(-2);
                            // remove placeholder and user we added, then append final two
                            messages = [...messages.slice(0, -2), ...finalTwo];
                        } else {
                            messages = updatedMessages;
                        }
                        // De-duplicate consecutive identical (role+content) at tail
                        if (messages.length >= 2) {
                            const a = messages[messages.length - 1];
                            const b = messages[messages.length - 2];
                            if (a.role === b.role && a.content === b.content) {
                                messages = [...messages.slice(0, -1)];
                            }
                        }
                        pendingAssistantIndex = null;
                        ignoreFinalGuestSse = false;
                    }
                );
            } catch (error) {
                console.error('Guest streaming error:', error);
                // Fallback to non-streaming
                const response = await guestChat({
                    content,
                    messages: currentMessages.slice(0, -1),
                    use_rag: useRag,
                    rag_top_k: ragTopK,
                    rag_temperature: ragTemperature,
                });
                messages = response.messages;
                pendingAssistantIndex = null;
                ignoreFinalGuestSse = true;
            }
        } else {
            // Guest non-streaming
            const nowSec = Math.floor(Date.now() / 1000);
            const currentMessages = [...messages, { role: 'user', content, timestamp: nowSec, cid: nextCid() } as any];
            messages = currentMessages;

            const response = await guestChat({
                content,
                messages: currentMessages.slice(0, -1), // Exclude the user message we just added
                use_rag: useRag,
                rag_top_k: ragTopK,
                rag_temperature: ragTemperature,
            });

            messages = response.messages;
        }
    }

    async function handleDeleteChat(e: CustomEvent<{ id: string }>) {
        const id = e.detail?.id;
        if (!id) return;
        const ok = confirm('Delete this chat?');
        if (!ok) return;
        try {
            await deleteChat(id);
            await refreshChats();
            if (!selectedChatId) {
                await getOrCreateChat();
            }
        } catch (err) {
            alert((err as Error).message || 'Failed to delete');
        }
    }
</script>

<div class="flex h-full">
    {#if !isGuestMode}
        <Sidebar {chats} selected={selectedChatId} onSelect={loadChat} onCreate={handleCreate} on:deleteChat={handleDeleteChat} />
    {/if}
    <div class="flex-1 flex flex-col">
        <div class="p-4 border-b border-gray-200 dark:border-gray-800 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between bg-white/80 dark:bg-gray-950/60 backdrop-blur">
          <div class="text-[11px] font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">
            {#if isGuestMode}
              Guest Mode
            {:else}
              {selectedChatId ? `Chat ${selectedChatId}` : 'Ready'}
            {/if}
          </div>
          <div class="flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-300">
            <label class="flex items-center gap-2">
              <input type="checkbox" bind:checked={streaming} disabled={useRag} />
              Streaming
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" bind:checked={useRag} />
              RAG
            </label>
            {#if !isGuestMode}
              <button
                class="btn-chip"
                on:click={() => goto('/profile')}
              >
                Profile
              </button>
            {/if}
            {#if useRag}
              <div class="flex items-center gap-1">
                <span>Top&nbsp;K</span>
                <input class="w-16 input-field !px-2 !py-1" type="number" min="1" max="20" bind:value={ragTopK} />
              </div>
              <div class="flex items-center gap-1">
                <span>Temp</span>
                <input class="w-16 input-field !px-2 !py-1" type="number" step="0.1" min="0" max="2" bind:value={ragTemperature} />
              </div>
            {/if}
            {#if isGuestMode}
              <button 
                class="rounded-2xl border border-blue-500/70 px-4 py-1.5 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-500 hover:text-white"
                on:click={() => {
                  goto('/auth');
                }}
              >
                ログインしてチャット履歴を保存
              </button>
            {/if}
          </div>
        </div>
        {#if useRag}
          <div class="px-3 text-xs text-gray-600 dark:text-gray-300">
            LangGraphベースのRAGで回答します。ストリーミングは自動的にオフになります。
          </div>
        {/if}
        {#if messages.length === 0}
          <!-- 初回は中央に入力 + ヒーローを表示（プロフェッショナルな印象） -->
          <div class="flex-1 relative overflow-hidden">
            <!-- 背景グラデーション -->
            <div class="pointer-events-none absolute inset-0 bg-gradient-to-b from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-950 dark:to-gray-900"></div>

            <div class="pointer-events-none absolute inset-x-0 top-20 flex justify-center">
              <div class="h-64 w-[40rem] rounded-full bg-gradient-to-r from-sky-200 via-indigo-100 to-fuchsia-200 dark:from-indigo-950 dark:via-slate-900 dark:to-purple-900 blur-3xl opacity-80"></div>
            </div>

            <div class="relative h-full px-6 py-12 flex flex-col items-center">
              <!-- ヒーロー領域 -->
              <div class="w-full max-w-3xl text-center space-y-6 mb-12">
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-xl border border-gray-200/70 dark:border-gray-700/70 text-[11px] text-gray-600 dark:text-gray-300 bg-white/70 dark:bg-gray-800/50 backdrop-blur">
                  <span>mini-webui</span>
                  <span class="text-gray-400">·</span>
                  <span>FastAPI × SvelteKit</span>
                </div>
                <p class="text-sm sm:text-base leading-relaxed text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
                  ミニマルな UI とストリーミング対応で、OpenAI API と自然に会話できます。LangGraph RAG での検索回答もワンタップです。
                </p>
                <div class="flex flex-wrap justify-center gap-2 text-[11px] sm:text-xs text-gray-500">
                  <span class="rounded-xl border border-gray-200/70 dark:border-gray-700/60 bg-white/70 dark:bg-gray-800/40 px-3 py-1">
                    📌 今日の会議を3行でまとめて
                  </span>
                  <span class="rounded-xl border border-gray-200/70 dark:border-gray-700/60 bg-white/70 dark:bg-gray-800/40 px-3 py-1">
                    💡 製品紹介のキャッチコピー案
                  </span>
                  <span class="rounded-xl border border-gray-200/70 dark:border-gray-700/60 bg-white/70 dark:bg-gray-800/40 px-3 py-1">
                    🔍 RAGで社内マニュアルを検索
                  </span>
                </div>
              </div>

              <!-- 入力カード -->
              <div id="try" class="w-full max-w-2xl">
                {#if isGuestMode}
                  <GuestMessageInput {streaming} {useRag} {ragTopK} {ragTemperature} on:sent={handleGuestSent} />
                {:else}
                  <MessageInput chatId={selectedChatId} resolveChat={getOrCreateChat} {streaming} {useRag}
                    ragTopK={ragTopK}
                    ragTemperature={ragTemperature}
                    on:sent={handleSent}
                    on:streamstart={(e) => {
                      // Optimistically append the user's message, then a placeholder assistant message
                      const targetId = e.detail?.chatId ?? selectedChatId;
                      if (!targetId) return;
                      if (selectedChatId !== targetId) {
                        selectedChatId = targetId;
                        messages = [];
                      }
                      if (selectedChatId) {
                        const nowSec = Math.floor(Date.now() / 1000);
                        const userText = e.detail?.content || '';
                        if (userText) {
                          messages = [...messages, { role: 'user', content: userText, timestamp: nowSec }];
                        }
                        pendingAssistantIndex = messages.push({ role: 'assistant', content: '' }) - 1;
                        messages = [...messages];
                      }
                    }}
                    on:stream={(e) => {
                      const targetId = e.detail?.chatId ?? selectedChatId;
                      if (!targetId || targetId !== selectedChatId) return;
                      if (pendingAssistantIndex != null) {
                        messages[pendingAssistantIndex].content = e.detail.partial;
                        messages = [...messages]; // trigger reactivity
                      }
                    }}
                    on:streamend={async (e) => {
                      // finalize the assistant message in place, then sync from server
                      const targetId = e.detail?.chatId ?? selectedChatId;
                      if (!targetId || targetId !== selectedChatId) return;
                      if (pendingAssistantIndex != null) {
                        messages[pendingAssistantIndex].content = e.detail.content || '';
                        messages = [...messages];
                        pendingAssistantIndex = null;
                      }
                      await refreshChats(targetId);
                    }}
                  />
                {/if}
              </div>
              <div class="mt-10 grid w-full max-w-3xl gap-3 text-left text-[11px] text-slate-600 dark:text-slate-300 sm:grid-cols-3">
                <div class="rounded-xl border border-slate-200/60 bg-white/80 p-4 shadow-[0_12px_28px_-26px_rgba(15,23,42,0.55)] backdrop-blur dark:border-slate-800/60 dark:bg-slate-900/60">
                  <div class="mb-1 text-xs font-semibold text-slate-700 dark:text-slate-100">ストリーミング</div>
                  <p class="leading-relaxed">レスポンスを逐次取得して、会話の流れを確認しながら執筆できます。</p>
                </div>
                <div class="rounded-xl border border-slate-200/60 bg-white/80 p-4 shadow-[0_12px_28px_-26px_rgba(15,23,42,0.55)] backdrop-blur dark:border-slate-800/60 dark:bg-slate-900/60">
                  <div class="mb-1 text-xs font-semibold text-slate-700 dark:text-slate-100">LangGraph RAG</div>
                  <p class="leading-relaxed">日本語ドキュメントを参照しながら精度の高い回答を生成します。</p>
                </div>
                <div class="rounded-xl border border-slate-200/60 bg-white/80 p-4 shadow-[0_12px_28px_-26px_rgba(15,23,42,0.55)] backdrop-blur dark:border-slate-800/60 dark:bg-slate-900/60">
                  <div class="mb-1 text-xs font-semibold text-slate-700 dark:text-slate-100">管理機能</div>
                  <p class="leading-relaxed">ログインするとユーザー管理や設定変更にアクセスできます。</p>
                </div>
              </div>
              <!-- フッターの薄い案内 -->
              <div class="mt-8 text-[11px] text-gray-400 dark:text-gray-500">
                Powered by FastAPI · SvelteKit · Tailwind CSS
              </div>
            </div>
          </div>
        {:else}
          <!-- チャット開始後は下部固定 + 上部にリスト -->
          <div class="relative flex-1 overflow-hidden bg-slate-50/85 dark:bg-slate-950">
            <div class="pointer-events-none absolute inset-0">
              <div class="absolute -top-28 right-[-10%] h-80 w-80 rounded-full bg-gradient-to-br from-sky-200 via-blue-100 to-purple-200 blur-3xl opacity-50 dark:from-indigo-900 dark:via-slate-900 dark:to-purple-900"></div>
              <div class="absolute bottom-[-25%] left-[-5%] h-96 w-96 rounded-full bg-gradient-to-tr from-amber-100 via-rose-100 to-lime-200 blur-3xl opacity-40 dark:from-emerald-900 dark:via-teal-900 dark:to-slate-900"></div>
            </div>
            <div class="relative h-full">
              <MessageList messages={messages} />
            </div>
          </div>
          {#if isGuestMode}
            <GuestMessageInput {streaming} {useRag} {ragTopK} {ragTemperature} on:sent={handleGuestSent} />
          {:else}
            <MessageInput chatId={selectedChatId} resolveChat={getOrCreateChat} {streaming} {useRag}
              ragTopK={ragTopK}
              ragTemperature={ragTemperature}
              on:sent={handleSent}
              on:streamstart={(e) => {
                // Optimistically append the user's message, then a placeholder assistant message
                const targetId = e.detail?.chatId ?? selectedChatId;
                if (!targetId) return;
                if (selectedChatId !== targetId) {
                  selectedChatId = targetId;
                  messages = [];
                }
                if (selectedChatId) {
                  const nowSec = Math.floor(Date.now() / 1000);
                  const userText = e.detail?.content || '';
                  if (userText) {
                    messages = [...messages, { role: 'user', content: userText, timestamp: nowSec }];
                  }
                  pendingAssistantIndex = messages.push({ role: 'assistant', content: '' }) - 1;
                  messages = [...messages];
                }
              }}
              on:stream={(e) => {
                const targetId = e.detail?.chatId ?? selectedChatId;
                if (!targetId || targetId !== selectedChatId) return;
                if (pendingAssistantIndex != null) {
                  messages[pendingAssistantIndex].content = e.detail.partial;
                  messages = [...messages]; // trigger reactivity
                }
              }}
              on:streamend={async (e) => {
                // finalize the assistant message in place, then sync from server
                const targetId = e.detail?.chatId ?? selectedChatId;
                if (!targetId || targetId !== selectedChatId) return;
                if (pendingAssistantIndex != null) {
                  messages[pendingAssistantIndex].content = e.detail.content || '';
                  messages = [...messages];
                  pendingAssistantIndex = null;
                }
                await refreshChats(targetId);
              }}
            />
          {/if}
        {/if}
    </div>
  </div>
