import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// В разработке /api уходит на локальный сервер FastAPI; в контейнере то же делает nginx.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
});
