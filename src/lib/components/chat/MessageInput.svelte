<script lang="ts">
  import { createEventDispatcher, onMount, afterUpdate, tick } from 'svelte';
  import { sendMessage, streamMessage } from '$lib/apis/chats';

  export let chatId: string | null = null;
  export let resolveChat: (() => Promise<string | null>) | null = null;
  export let streaming: boolean = false;
  export let useRag: boolean = false;
  export let ragTopK: number = 4;
  export let ragTemperature: number | null = 0.3;
  const dispatch = createEventDispatcher();

  let content = '';
  let sending = false;
  let composing = false; // IME composition state
  let textareaEl: HTMLTextAreaElement | null = null;

  function autoResize() {
    if (!textareaEl) return;
    textareaEl.style.height = 'auto';
    const maxHeight = 220;
    textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, maxHeight)}px`;
  }

  onMount(() => {
    autoResize();
  });

  afterUpdate(() => {
    autoResize();
  });

  async function handleSend() {
    if (!content.trim() || sending) return;
    sending = true;
    const text = content;
    let targetChatId = chatId;
    try {
      if (!targetChatId && resolveChat) {
        targetChatId = await resolveChat();
      }
      if (!targetChatId) {
        throw new Error('Unable to determine chat room');
      }
      content = '';
      await tick();
      autoResize();
      if (streaming && !useRag) {
        let acc = '';
        // notify parent with the user's text so it can optimistically render
        dispatch('streamstart', { content: text, chatId: targetChatId });
        await streamMessage(targetChatId, text, {}, (chunk) => {
          acc += chunk;
          dispatch('stream', { partial: acc, chatId: targetChatId });
        });
        // streaming completed
        dispatch('streamend', { content: acc, chatId: targetChatId });
      } else {
        const topK = useRag ? Math.max(1, Math.floor(ragTopK)) : undefined;
        const temp = useRag && ragTemperature != null ? Math.min(2, Math.max(0, ragTemperature)) : undefined;
        await sendMessage(targetChatId, text, {
          use_rag: useRag || undefined,
          rag_top_k: topK,
          rag_temperature: temp,
        });
        // non-streaming completed
        dispatch('sent', { chatId: targetChatId });
      }
    } catch (e) {
      content = text;
      console.error(e);
      alert((e as Error).message || 'Failed to send');
    } finally {
      sending = false;
    }
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && e.shiftKey) {
      const composingNow = (e as any).isComposing || composing || (e as any).keyCode === 229;
      if (composingNow) return;
      e.preventDefault();
      handleSend();
    }
  }
</script>

<div class="border-t border-slate-200/70 bg-white/80 px-4 py-4 dark:border-slate-800/70 dark:bg-slate-950/60">
  <div class="mx-auto w-full max-w-3xl">
    <div class="rounded-2xl border border-slate-200/70 bg-white/90 p-4 shadow-[0_10px_26px_-18px_rgba(15,23,42,0.4)] backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/80">
      <textarea
        bind:this={textareaEl}
        class="w-full resize-none border-none bg-transparent text-sm leading-6 text-slate-900 placeholder:text-slate-400 focus:outline-none dark:text-slate-100 dark:placeholder:text-slate-500"
        placeholder="メッセージを入力..."
        rows="1"
        bind:value={content}
        on:keydown={onKeyDown}
        on:compositionstart={() => (composing = true)}
        on:compositionend={() => (composing = false)}
        on:input={autoResize}
      />
      <div class="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
        {#if useRag}
          <span class="inline-flex items-center gap-2 rounded-xl border border-purple-400/50 bg-purple-50/70 px-3 py-1 text-purple-500 dark:border-purple-500/40 dark:bg-purple-500/10 dark:text-purple-200">
            <span class="h-1.5 w-1.5 rounded-full bg-purple-400 dark:bg-purple-300"></span>
            LangGraph RAG モード
          </span>
        {:else if streaming}
          <span class="inline-flex items-center gap-2 rounded-xl border border-emerald-400/50 bg-emerald-50/80 px-3 py-1 text-emerald-500 dark:border-emerald-400/40 dark:bg-emerald-500/10 dark:text-emerald-200">
            <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 dark:bg-emerald-300"></span>
            ストリーミング応答
          </span>
        {:else}
          <span class="inline-flex items-center gap-2 rounded-xl border border-slate-300/60 bg-slate-100/80 px-3 py-1 text-slate-500 dark:border-slate-700/60 dark:bg-slate-800/40 dark:text-slate-300">
            <span class="h-1.5 w-1.5 rounded-full bg-slate-300 dark:bg-slate-500"></span>
            シンプル応答
          </span>
        {/if}
        <span class="hidden text-slate-400 sm:flex">Shift+Enterで送信 · Enterで改行</span>
        <div class="ml-auto flex items-center gap-2">
          <button
            class="btn-primary px-5 py-2"
            on:click={handleSend}
            disabled={sending || (!chatId && !resolveChat)}
          >
            Send
            <span aria-hidden="true">↵</span>
          </button>
        </div>
      </div>
    </div>
  </div>
  <slot />
</div>
