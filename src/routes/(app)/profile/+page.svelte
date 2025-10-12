<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { me, updateProfile } from '$lib/apis/auths';
  import { user, isGuest } from '$lib/stores';
  import { get } from 'svelte/store';

  let name = '';
  let email = '';
  let profileImageUrl = '';
  let bio = '';
  let loading = true;
  let saving = false;
  let successMessage = '';
  let errorMessage = '';

  async function loadProfile() {
    loading = true;
    errorMessage = '';
    successMessage = '';
    try {
      const u = await me();
      name = u.name ?? '';
      email = u.email ?? '';
      profileImageUrl = u.profile_image_url ?? '';
      bio = u.bio ?? '';
      user.set(u);
    } catch (err) {
      errorMessage = (err as Error).message || 'プロフィールの取得に失敗しました';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    if (get(isGuest)) {
      goto('/auth');
      return;
    }
    loadProfile();
  });

  $: if (!loading && $isGuest) {
    goto('/auth');
  }

  async function handleSubmit() {
    if (!name.trim()) {
      errorMessage = '名前を入力してください';
      return;
    }
    saving = true;
    successMessage = '';
    errorMessage = '';
    try {
      const payload = {
        name: name.trim(),
        profile_image_url: profileImageUrl.trim() ? profileImageUrl.trim() : null,
        bio: bio.trim() ? bio.trim() : null
      };
      const updated = await updateProfile(payload);
      user.set(updated);
      successMessage = 'プロフィールを更新しました';
    } catch (err) {
      errorMessage = (err as Error).message || 'プロフィールの更新に失敗しました';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>プロフィール設定 | mini-webui</title>
</svelte:head>

<div class="flex h-full items-center justify-center bg-gradient-to-b from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-950 dark:to-gray-900 px-4">
  <div class="w-full max-w-2xl space-y-6 rounded-2xl border border-gray-200/80 bg-white/85 p-8 shadow-[0_12px_30px_-20px_rgba(15,23,42,0.3)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">プロフィール設定</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400">表示名やアイコン、自己紹介を更新できます。</p>
      </div>
      <button class="btn-secondary text-xs" on:click={() => goto('/')}>
        ← チャットに戻る
      </button>
    </div>

    {#if loading}
      <div class="rounded-xl border border-gray-200/70 bg-white/80 p-6 text-center text-gray-500 dark:border-gray-700/70 dark:bg-gray-900/60 dark:text-gray-300">
        読み込み中…
      </div>
    {:else}
      <form class="space-y-5" on:submit|preventDefault={handleSubmit}>
        {#if successMessage}
          <div class="rounded-xl border border-emerald-400/50 bg-emerald-50/80 px-4 py-3 text-sm text-emerald-600 dark:border-emerald-400/40 dark:bg-emerald-500/10 dark:text-emerald-200">
            {successMessage}
          </div>
        {/if}
        {#if errorMessage}
          <div class="rounded-xl border border-red-400/60 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
            {errorMessage}
          </div>
        {/if}

        <div class="grid gap-5 sm:grid-cols-[9rem_1fr] sm:items-start">
          <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 sm:pt-3">Email</label>
          <div class="rounded-xl border border-gray-200/70 bg-gray-50 px-4 py-3 text-sm text-gray-500 dark:border-gray-700/60 dark:bg-gray-900/40 dark:text-gray-400">
            {email}
          </div>
        </div>

        <div class="grid gap-5 sm:grid-cols-[9rem_1fr] sm:items-start">
          <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 sm:pt-3">Name</label>
          <div>
            <input
              class="input-field"
              bind:value={name}
              placeholder="表示名"
              maxlength="80"
            />
          </div>
        </div>

        <div class="grid gap-5 sm:grid-cols-[9rem_1fr] sm:items-start">
          <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 sm:pt-3">Profile Image</label>
          <div class="space-y-3">
            <input
              class="input-field"
              bind:value={profileImageUrl}
              placeholder="https://example.com/avatar.png"
              maxlength="2048"
            />
            {#if profileImageUrl.trim()}
              <div class="flex items-center gap-3">
                <div class="text-xs text-gray-500 dark:text-gray-400">プレビュー</div>
                <img src={profileImageUrl} alt="Profile preview" class="h-12 w-12 rounded-xl object-cover border border-gray-200/70 dark:border-gray-700/60" />
              </div>
            {/if}
          </div>
        </div>

        <div class="grid gap-5 sm:grid-cols-[9rem_1fr] sm:items-start">
          <label class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400 sm:pt-3">Bio</label>
          <div>
            <textarea
              class="input-field h-32 resize-none"
              bind:value={bio}
              placeholder="自己紹介や得意分野などを入力してください"
            ></textarea>
            <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">Markdown はサポートされません。</p>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-4">
          <button type="button" class="btn-secondary" on:click={loadProfile} disabled={saving}>
            リセット
          </button>
          <button type="submit" class="btn-primary px-6 py-2" disabled={saving}>
            {saving ? '保存中…' : '変更を保存'}
          </button>
        </div>
      </form>
    {/if}
  </div>
</div>
