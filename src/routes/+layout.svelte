<script lang="ts">
    import '../app.css';
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { user, isAuthenticated, setGuestMode } from '$lib/stores';
    
    onMount(() => {
        // Check if user is authenticated on app load
        const token = localStorage.getItem('token');
        if (token) {
            // TODO: Validate token with backend
            isAuthenticated.set(true);
        } else {
            // No token found, set guest mode
            setGuestMode();
        }
        
        // Simple routing logic for now
        const currentPath = $page.url.pathname;
        const isAuthPage = currentPath.startsWith('/auth');
        
        // For now, allow access to all pages during development
        // TODO: Implement proper authentication routing
    });
</script>

<main class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <slot />
</main>

<style>
    :global(html) {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    }
</style>