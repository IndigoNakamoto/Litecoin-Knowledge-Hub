# Litecoin Knowledge Hub Integration Plan
## Architecture Overview

We are using a **Guest Tunnel + Worker Proxy** approach.

1.  **Guest Tunnel:** You create a tunnel entry and provide me the token. I run the daemon. This exposes my container securely as an internal subdomain (e.g., `chat-origin.litecoin.com`).
2.  **Worker:** You add a Worker route `litecoin.com/chat*` that transparently proxies to that internal subdomain.

**Note:** The app is configured with `basePath: '/chat'` in `frontend/next.config.ts`, so the Worker should **not** strip the path prefix.

-----

## Action Items

### 1\. Create Guest Tunnel (Zero Trust)

I need a secure "backdoor" to connect my container to the `litecoin.com` zone without opening ports.

1.  Go to **Zero Trust \> Networks \> Tunnels**.
2.  Create a new tunnel named: `knowledge-hub-guest`.
3.  **Save the Tunnel Token** (starts with `ey...`).
4.  In the "Public Hostname" tab for this tunnel, add:
      * **Subdomain:** `chat-origin` (or similar internal name users won't guess).
      * **Domain:** `litecoin.com`
      * **Service:** `http://frontend:3000`
5.  **Action:** Please send me the **Tunnel Token**.

### 2\. Deploy Cloudflare Worker

This Worker transparently proxies traffic from the main site to the tunnel endpoint.

1.  Create a new Worker.
2.  **Route:** `litecoin.com/chat*` (Ensure the wildcard `*` is present).
3.  **Code:**

<!-- end list -->

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Only intercept requests starting with /chat
    if (url.pathname.startsWith('/chat')) {
      // Proxy to the guest tunnel endpoint
      // We keep the /chat path intact because the Next.js app expects it (basePath defined)
      const targetUrl = new URL(request.url);
      targetUrl.hostname = 'chat-origin.litecoin.com'; // The hostname defined in Step 1

      const newRequest = new Request(targetUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        redirect: 'manual',
      });

      return fetch(newRequest);
    }

    // Fallback (though the route trigger handles this)
    return fetch(request);
  }
}
```

-----

## Summary of Deliverables needed from you:

1.  **Tunnel Token** (for `knowledge-hub-guest`)
2.  Confirmation when the **Worker** is active.