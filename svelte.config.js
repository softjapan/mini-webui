import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import fs from 'node:fs';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html'
		}),
		alias: {
			$lib: './src/lib'
		},
		version: {
			name: (() => {
				try {
					return (
						JSON.parse(fs.readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
							?.version || Date.now().toString()
					);
				} catch {
					return Date.now().toString();
				}
			})(),
			pollInterval: 60000
		}
	},
	onwarn: (warning, handler) => {
		const { code } = warning;
		if (code === 'css-unused-selector') return;
		handler(warning);
	}
};

export default config;