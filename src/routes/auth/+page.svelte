<script lang="ts">
    import { goto } from '$app/navigation';
    import { isAuthenticated, user, token as tokenStore, setGuestMode, isGuest } from '$lib/stores';
    import { register, login, me } from '$lib/apis/auths';

    let isLogin = true;
    let email = '';
    let password = '';
    let name = '';

    function toggleMode() {
        isLogin = !isLogin;
        email = '';
        password = '';
        name = '';
    }

    async function handleSubmit() {
        try {
            if (!isLogin) {
                await register({ name, email, password });
            }
            const res = await login({ email, password });
            localStorage.setItem('token', res.access_token);
            tokenStore.set(res.access_token);
            const u = await me();
            user.set(u);
            isAuthenticated.set(true);
            // Clear guest mode when successfully authenticated
            isGuest.set(false);
            goto('/');
        } catch (e) {
            alert((e as Error).message || 'Authentication failed');
        }
    }

    function handleGuestMode() {
        setGuestMode();
        goto('/');
    }
</script>

<main class="relative min-h-screen overflow-hidden bg-gradient-to-b from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-950 dark:to-gray-900">
    <div class="pointer-events-none absolute inset-0">
        <div class="absolute inset-x-0 top-20 flex justify-center">
            <div class="h-64 w-[36rem] rounded-full bg-gradient-to-r from-sky-200 via-indigo-100 to-fuchsia-200 blur-3xl opacity-80 dark:from-indigo-950 dark:via-slate-900 dark:to-purple-900"></div>
        </div>
    </div>

    <div class="relative mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center px-6 py-16">
        <div class="mb-8 text-center">
            <div class="inline-flex items-center gap-2 rounded-xl border border-gray-200/70 bg-white/80 px-4 py-1 text-xs uppercase tracking-[0.3em] text-gray-500 dark:border-gray-700/70 dark:bg-gray-900/50 dark:text-gray-300">
                mini-webui
            </div>
            <h1 class="mt-5 text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {isLogin ? 'ログイン' : 'アカウント作成'}
            </h1>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
                メールアドレスとパスワードを入力してください。
            </p>
        </div>

        <div class="rounded-2xl border border-gray-200/80 bg-white/85 p-8 shadow-[0_12px_30px_-20px_rgba(15,23,42,0.3)] backdrop-blur dark:border-gray-700/60 dark:bg-gray-900/70">
            <form class="space-y-5" on:submit|preventDefault={handleSubmit}>
                {#if !isLogin}
                    <div class="space-y-2">
                        <label class="text-xs font-medium uppercase tracking-[0.25em] text-gray-500 dark:text-gray-400">Name</label>
                        <div class="rounded-xl border border-gray-200/70 bg-white px-4 py-3 focus-within:border-indigo-400 dark:border-gray-700/60 dark:bg-gray-900">
                            <input
                                id="name"
                                name="name"
                                type="text"
                                required={!isLogin}
                                bind:value={name}
                                class="w-full border-none bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder:text-gray-500"
                                placeholder="フルネーム"
                            />
                        </div>
                    </div>
                {/if}

                <div class="space-y-2">
                    <label class="text-xs font-medium uppercase tracking-[0.25em] text-gray-500 dark:text-gray-400">Email</label>
                    <div class="rounded-xl border border-gray-200/70 bg-white px-4 py-3 focus-within:border-indigo-400 dark:border-gray-700/60 dark:bg-gray-900">
                        <input
                            id="email"
                            name="email"
                            type="email"
                            required
                            bind:value={email}
                            class="w-full border-none bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder:text-gray-500"
                            placeholder="name@example.com"
                        />
                    </div>
                </div>

                <div class="space-y-2">
                    <label class="text-xs font-medium uppercase tracking-[0.25em] text-gray-500 dark:text-gray-400">Password</label>
                    <div class="rounded-xl border border-gray-200/70 bg-white px-4 py-3 focus-within:border-indigo-400 dark:border-gray-700/60 dark:bg-gray-900">
                        <input
                            id="password"
                            name="password"
                            type="password"
                            required
                            bind:value={password}
                            class="w-full border-none bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder:text-gray-500"
                            placeholder="••••••••"
                        />
                    </div>
                </div>

                <button
                    type="submit"
                    class="btn-primary w-full justify-center py-3 text-base font-semibold"
                >
                    {isLogin ? 'サインイン' : 'アカウントを作成'}
                </button>
            </form>

            <div class="mt-6 space-y-3 text-center text-sm text-gray-500 dark:text-gray-400">
                <button
                    type="button"
                    on:click={toggleMode}
                    class="text-indigo-500 underline-offset-4 transition hover:text-indigo-600 dark:text-indigo-300 dark:hover:text-indigo-200"
                >
                    {isLogin ? '新規登録はこちら' : '既にアカウントをお持ちの方はこちら'}
                </button>
                <button
                    type="button"
                    on:click={handleGuestMode}
                    class="text-gray-500 underline-offset-4 transition hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100"
                >
                    ゲストモードで試す（ログイン不要）
                </button>
                {#if $isGuest}
                    <p class="text-xs text-gray-400 dark:text-gray-500">
                        ゲスト利用中。ログインすると履歴保存や管理機能が有効になります。
                    </p>
                {/if}
            </div>
        </div>
    </div>
</main>
