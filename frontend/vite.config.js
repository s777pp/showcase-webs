import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const here = dirname(fileURLToPath(import.meta.url));
export default defineConfig({ plugins: [react()], build: { outDir: resolve(here, '../static/react'), emptyOutDir: true }, server: { proxy: { '/api': 'http://localhost:8000', '/static': 'http://localhost:8000' } } });
