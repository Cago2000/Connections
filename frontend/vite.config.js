import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    base: "/",
    plugins: [react()],
    server: {
        host: "0.0.0.0",
        port: 5173,
        strictPort: true,
        allowedHosts: ["connections.nba-standings-cago2000.org"],
        proxy: {
            "/api": "http://localhost:8000",
        },
        headers: {
            "Content-Security-Policy": [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline'",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src https://fonts.gstatic.com",
                "connect-src 'self' https://discord.com https://*.discord.com",
                "frame-ancestors https://discord.com https://ptb.discord.com https://canary.discord.com",
            ].join("; "),
        },
    },
    build: {
        rollupOptions: {
            output: {
                entryFileNames: "assets/[name].js",
                chunkFileNames: "assets/[name].js",
                assetFileNames: "assets/[name].[ext]",
            },
        },
    },
});