<script lang="ts">
  import { afterUpdate } from 'svelte';
  import { renderMarkdown } from '$lib/utils/markdown';
  type DocumentEntry = { id?: string; page_content?: string; metadata?: Record<string, any> };

  type MessageData = {
    documents?: DocumentEntry[];
    traces?: Record<string, any>[];
    mode?: string;
  };

  export let messages: { role: string; content: string; timestamp?: number; data?: MessageData }[] = [];

  let container: HTMLDivElement;

  // Minimal auto-scroll to bottom on update
  afterUpdate(() => {
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });

  const DOC_SNIPPET_LEN = 120;

  function docLabel(idx: number, doc: DocumentEntry | undefined) {
    const source = doc?.metadata?.source ?? doc?.metadata?.path ?? doc?.id ?? `doc-${idx + 1}`;
    return `${idx + 1}. ${source}`;
  }

  function docSnippet(content: string | undefined) {
    if (!content) return '';
    return content.length > DOC_SNIPPET_LEN ? `${content.slice(0, DOC_SNIPPET_LEN)}…` : content;
  }
</script>

<div
  id="chat-feed"
  class="mx-auto h-full w-full max-w-5xl overflow-y-auto px-5 py-8 sm:px-10 space-y-8 scrollbar-thin"
  bind:this={container}
>
  {#each messages as m, i (m.cid ?? `${m.timestamp ?? ''}-${m.role}-${typeof m.content === 'string' ? m.content.slice(0,20) : ''}`)}
    <div class="chat-message {m.role}">
      <div class="avatar h-10 w-10 flex items-center justify-center rounded-full border border-white/50 bg-white/70 text-xs font-semibold uppercase tracking-wide text-slate-500 shadow-sm dark:border-slate-700/70 dark:bg-slate-900/80 dark:text-slate-300">
        {m.role === 'user' ? 'You' : 'AI'}
      </div>
      <div class="bubble">
        <div class="meta">
          {m.role === 'user' ? 'You' : 'Assistant'}
          {#if m.timestamp}
            · {new Date(m.timestamp * 1000).toLocaleTimeString()}
          {/if}
        </div>
        {#if m.role === 'assistant'}
          <div class="prose prose-sm sm:prose-base dark:prose-invert max-w-none">
            {@html renderMarkdown(typeof m.content === 'string' ? m.content : '```json\n' + JSON.stringify(m.content, null, 2) + '\n```')}
          </div>
          {#if m.data?.documents && m.data.documents.length}
            <div class="mt-5 rounded-2xl border border-slate-200/70 bg-slate-50/90 p-4 text-xs text-slate-600 shadow-sm dark:border-slate-700/60 dark:bg-slate-900/60 dark:text-slate-300">
              <div class="mb-3 text-[11px] uppercase tracking-[0.25em] text-slate-400 dark:text-slate-500">References</div>
              <div class="space-y-3">
                {#each m.data.documents as doc, idx}
                  <div class="rounded-xl border border-slate-200/60 bg-white/95 p-3 shadow-sm dark:border-slate-700/40 dark:bg-slate-900/70">
                    <div class="text-xs font-semibold text-slate-700 dark:text-slate-200">{docLabel(idx, doc)}</div>
                    {#if doc?.page_content}
                      <div class="mt-1 text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">{docSnippet(doc.page_content)}</div>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {:else}
          <div class="whitespace-pre-wrap text-sm leading-7 text-white/90">
            {m.content}
          </div>
        {/if}
      </div>
    </div>
  {/each}
</div>
