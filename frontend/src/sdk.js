export async function initDiscord() {
    if (import.meta.env.DEV) {
        return {
            access_token: "dev_token",
            user_id: "test_user_123",
            username: "testuser",
            channel_id: "dev_channel_123",
        };
    }

    const { DiscordSDK } = await import("@discord/embedded-app-sdk");
    const sdk = new DiscordSDK(import.meta.env.VITE_DISCORD_CLIENT_ID);
    await sdk.ready();

    sdk.patchUrlMappings([
        { prefix: "/api", target: import.meta.env.VITE_SERVER_URL },
    ]);

    const { code } = await sdk.commands.authorize({
        client_id: import.meta.env.VITE_DISCORD_CLIENT_ID,
        response_type: "code",
        state: "",
        prompt: "none",
        scope: ["identify"],
    });

    const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
    });

    const authData = await res.json();
    return { ...authData, channel_id: sdk.channelId ?? null };
}