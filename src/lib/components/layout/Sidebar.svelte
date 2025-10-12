<script lang="ts">
  import type { ChatItem } from '$lib/apis/chats';
  import { user, isAuthenticated } from '$lib/stores';
  import { goto } from '$app/navigation';
  import { get } from 'svelte/store';
  import { createEventDispatcher } from 'svelte';

  export let chats: ChatItem[] = [];
  export let selected: string | null = null;
  export let onSelect: (id: string) => void;
  export let onCreate: () => void;

  const dispatch = createEventDispatcher<{ deleteChat: { id: string } }>();
  let menuOpenId: string | null = null;

  function goAdmin() { goto('/admin'); }

  function logout() {
    try {
      localStorage.removeItem('token');
    } catch {}
    user.set(null);
    isAuthenticated.set(false);
    goto('/auth');
  }

  function toggleMenu(id: string) {
    menuOpenId = menuOpenId === id ? null : id;
  }

  function requestDelete(id: string) {
    menuOpenId = null;
    dispatch('deleteChat', { id });
  }
</script>

<aside class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
  <div class="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between gap-2">
    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Chats</h2>
    <div class="flex items-center gap-2">
      {#if $user && $user.role === 'admin'}
        <button class="btn-chip" on:click={goAdmin}>Admin</button>
      {/if}
      <button class="btn-chip-primary" on:click={onCreate}>+ New</button>
      <button class="btn-chip" on:click={logout}>Logout</button>
    </div>
  </div>
  <div class="flex-1 overflow-auto" on:click={() => (menuOpenId = null)}>
    {#if chats.length === 0}
      <div class="p-4 text-sm text-gray-500">No chats yet</div>
    {:else}
      {#each chats as c}
        <div class="relative group">
          <div
            class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer {selected === c.id ? 'bg-gray-100 dark:bg-gray-700' : ''}"
            on:click={() => onSelect(c.id)}
          >
            <div class="truncate text-gray-800 dark:text-gray-100 pr-8">{c.title}</div>
            <div class="text-xs text-gray-500">{new Date(c.updated_at * 1000).toLocaleString()}</div>
          </div>
          <button
            class="absolute right-2 top-2 hidden group-hover:inline-flex items-center justify-center w-6 h-6 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
            title="More"
            on:click|stopPropagation={() => toggleMenu(c.id)}
          >
            ···
          </button>
          {#if menuOpenId === c.id}
            <div
              class="absolute right-2 top-8 z-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-md"
              on:click|stopPropagation
            >
              <button
                class="block w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                on:click={() => requestDelete(c.id)}
              >
                Delete
              </button>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</aside>
