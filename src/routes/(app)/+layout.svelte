<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { user, isAuthenticated, setGuestMode } from '$lib/stores';
    import { me } from '$lib/apis/auths';

    onMount(async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            // No token found, set guest mode instead of redirecting
            setGuestMode();
            return;
        }
        try {
            const u = await me();
            user.set(u);
            isAuthenticated.set(true);
        } catch {
            localStorage.removeItem('token');
            // If token is invalid, set guest mode instead of redirecting
            setGuestMode();
        }
    });
</script>

<div class="flex h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Sidebar will be added here -->
    <div class="flex-1 flex flex-col">
        <!-- Header will be added here -->
        <main class="flex-1 overflow-hidden">
            <slot />
        </main>
    </div>
</div>
