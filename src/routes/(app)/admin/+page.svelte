<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import { getStats, listUsers, createUser, activateUser, deactivateUser, deleteUser, getSettings, updateSettings } from '$lib/apis/admin';
  import { me } from '$lib/apis/auths';

  let activeTab: 'stats'|'users'|'settings' = 'stats';
  let stats: { users: number; chats: number; messages: number } | null = null;

  // Users
  let q = '';
  let users: any[] = [];
  let total = 0;
  let offset = 0;
  let limit = 20;
  let creating = false;
  let newName = '';
  let newEmail = '';
  let newPassword = '';
  let newRole = 'user';
  let userMessage = '';
  let userError = '';

  // Settings
  let settings: any = { openai_api_key: '', openai_api_base: '', app_name: '', debug: false };
  let savingSettings = false;
  let settingsMessage = '';
  let settingsError = '';

  async function ensureAdmin() {
    try {
      const u = await me();
      if (!u || u.role !== 'admin') {
        goto('/');
        return false;
      }
      user.set(u);
      return true;
    } catch {
      goto('/auth');
      return false;
    }
  }

  async function loadStats() { stats = await getStats(); }
  async function loadUsers() {
    const r = await listUsers({ q, offset, limit });
    users = r.items;
    total = r.total;
  }
  async function loadSettings() {
    settings = await getSettings();
    settingsMessage = '';
    settingsError = '';
  }

  onMount(async () => {
    if (!(await ensureAdmin())) return;
    await Promise.all([loadStats(), loadUsers(), loadSettings()]);
  });

  async function handleCreateUser() {
    creating = true;
    userMessage = '';
    userError = '';
    try {
      await createUser({ name: newName, email: newEmail, password: newPassword, role: newRole });
      newName = newEmail = newPassword = ''; newRole = 'user';
      await loadUsers(); await loadStats();
      userMessage = 'ユーザーを作成しました';
    } catch (e) {
      userError = (e as Error).message;
    }
    creating = false;
  }

  async function toggleActive(u: any) {
    userMessage = '';
    userError = '';
    try {
      const wasActive = u.is_active;
      if (wasActive) await deactivateUser(u.id); else await activateUser(u.id);
      await loadUsers(); await loadStats();
      userMessage = wasActive ? `${u.email} を無効化しました` : `${u.email} を有効化しました`;
    } catch (e) {
      userError = (e as Error).message;
    }
  }

  async function hardDelete(u: any) {
    if (!confirm(`Delete user ${u.email}? This is irreversible.`)) return;
    userMessage = '';
    userError = '';
    try {
      await deleteUser(u.id, { hard: true });
      await loadUsers(); await loadStats();
      userMessage = `${u.email} を削除しました`;
    } catch (e) {
      userError = (e as Error).message;
    }
  }

  async function saveSettings() {
    savingSettings = true;
    settingsMessage = '';
    settingsError = '';
    try {
      await updateSettings(settings);
      settingsMessage = '設定を保存しました';
    } catch (e) {
      settingsError = (e as Error).message;
    }
    savingSettings = false;
  }

  function goBack() {
    goto('/');
  }
</script>

<div class="min-h-full bg-gradient-to-b from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-950 dark:to-gray-900">
  <div class="mx-auto w-full max-w-6xl px-6 py-12 space-y-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-2">
        <div class="inline-flex items-center gap-2 rounded-xl border border-gray-200/70 bg-white/70 px-4 py-1 text-xs uppercase tracking-[0.3em] text-gray-500 dark:border-gray-700/60 dark:bg-gray-900/50 dark:text-gray-300">
          Admin Console
        </div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">システム管理</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400">ユーザー管理、利用状況の確認、OpenAI設定をここから行えます。</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-chip" on:click={goBack}>← チャットに戻る</button>
      </div>
    </div>

    <div class="flex flex-wrap gap-3">
      <button
        class={`tab-button ${activeTab === 'stats' ? 'tab-button-active' : ''}`}
        on:click={() => activeTab = 'stats'}
      >
        ダッシュボード
      </button>
      <button
        class={`tab-button ${activeTab === 'users' ? 'tab-button-active' : ''}`}
        on:click={() => activeTab = 'users'}
      >
        ユーザー管理
      </button>
      <button
        class={`tab-button ${activeTab === 'settings' ? 'tab-button-active' : ''}`}
        on:click={() => activeTab = 'settings'}
      >
        システム設定
      </button>
    </div>

    {#if activeTab === 'stats'}
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-xl border border-gray-200/70 bg-white/85 p-6 shadow-[0_10px_26px_-20px_rgba(15,23,42,0.35)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
          <div class="text-xs uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">Users</div>
          <div class="mt-3 text-3xl font-semibold text-gray-900 dark:text-gray-100">{stats?.users ?? '-'}</div>
        </div>
        <div class="rounded-xl border border-gray-200/70 bg-white/85 p-6 shadow-[0_10px_26px_-20px_rgba(15,23,42,0.35)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
          <div class="text-xs uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">Chats</div>
          <div class="mt-3 text-3xl font-semibold text-gray-900 dark:text-gray-100">{stats?.chats ?? '-'}</div>
        </div>
        <div class="rounded-xl border border-gray-200/70 bg-white/85 p-6 shadow-[0_10px_26px_-20px_rgba(15,23,42,0.35)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
          <div class="text-xs uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">Messages</div>
          <div class="mt-3 text-3xl font-semibold text-gray-900 dark:text-gray-100">{stats?.messages ?? '-'}</div>
        </div>
      </div>
    {/if}

    {#if activeTab === 'users'}
      <div class="space-y-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex w-full max-w-xl gap-2">
            <input class="input-field" placeholder="名前またはメールで検索" bind:value={q} />
            <button class="btn-chip" on:click={loadUsers}>Search</button>
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400">合計: {total}</div>
        </div>

        {#if userMessage}
          <div class="rounded-xl border border-emerald-400/50 bg-emerald-50/80 px-4 py-3 text-sm text-emerald-600 dark:border-emerald-400/40 dark:bg-emerald-500/10 dark:text-emerald-200">
            {userMessage}
          </div>
        {/if}
        {#if userError}
          <div class="rounded-xl border border-red-400/60 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
            {userError}
          </div>
        {/if}

        <div class="rounded-xl border border-gray-200/70 bg-white/85 p-6 shadow-[0_10px_26px_-20px_rgba(15,23,42,0.35)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
          <div class="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-100">新規ユーザー作成</div>
          <div class="grid gap-3 md:grid-cols-5 md:items-end">
            <input class="input-field" placeholder="Name" bind:value={newName} />
            <input class="input-field" placeholder="Email" bind:value={newEmail} />
            <input class="input-field" placeholder="Password" type="password" bind:value={newPassword} />
            <select class="input-field" bind:value={newRole}>
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
            <button class="btn-chip-primary" on:click={handleCreateUser} disabled={creating}>{creating ? 'Creating…' : 'Create'}</button>
          </div>
        </div>

        <div class="overflow-hidden rounded-xl border border-gray-200/70 bg-white/90 shadow-[0_10px_26px_-20px_rgba(15,23,42,0.3)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
          <div class="overflow-x-auto">
            <table class="min-w-full text-sm">
              <thead>
                <tr class="border-b border-gray-200/70 bg-white/60 text-left text-gray-500 dark:border-gray-700/50 dark:bg-gray-900/50 dark:text-gray-300">
                  <th class="px-4 py-3">Name</th>
                  <th class="px-4 py-3">Email</th>
                  <th class="px-4 py-3">Role</th>
                  <th class="px-4 py-3">Active</th>
                  <th class="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {#each users as u}
                  <tr class="border-b border-gray-100/70 text-gray-700 dark:border-gray-800/60 dark:text-gray-100">
                    <td class="px-4 py-3">{u.name}</td>
                    <td class="px-4 py-3">{u.email}</td>
                    <td class="px-4 py-3 capitalize">{u.role}</td>
                    <td class="px-4 py-3">{u.is_active ? 'yes' : 'no'}</td>
                    <td class="px-4 py-3">
                      <div class="flex flex-wrap gap-2">
                        <button class="btn-chip" on:click={() => toggleActive(u)}>{u.is_active ? 'Deactivate' : 'Activate'}</button>
                        <button class="btn-chip-danger" on:click={() => hardDelete(u)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    {/if}

    {#if activeTab === 'settings'}
      <div class="space-y-6 max-w-3xl">
        {#if settingsMessage}
          <div class="rounded-xl border border-emerald-400/50 bg-emerald-50/80 px-4 py-3 text-sm text-emerald-600 dark:border-emerald-400/40 dark:bg-emerald-500/10 dark:text-emerald-200">
            {settingsMessage}
          </div>
        {/if}
        {#if settingsError}
          <div class="rounded-xl border border-red-400/60 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
            {settingsError}
          </div>
        {/if}

        <div class="grid gap-5">
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">OpenAI API Key</label>
            <input class="input-field" type="password" bind:value={settings.openai_api_key} />
          </div>
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">OpenAI API Base</label>
            <input class="input-field" bind:value={settings.openai_api_base} />
          </div>
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400">App Name</label>
            <input class="input-field" bind:value={settings.app_name} />
          </div>
          <div class="flex items-center gap-3 rounded-xl border border-gray-200/70 bg-white/70 px-4 py-3 dark:border-gray-700/60 dark:bg-gray-900/60">
            <input id="dbg" type="checkbox" bind:checked={settings.debug} class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
            <label for="dbg" class="text-sm text-gray-600 dark:text-gray-300">Debug Mode</label>
          </div>
        </div>
        <div class="flex justify-end">
          <button class="btn-primary px-6 py-2" on:click={saveSettings} disabled={savingSettings}>
            {savingSettings ? 'Saving…' : '保存する'}
          </button>
        </div>
      </div>
    {/if}
  </div>
</div>
