// WebSocket connection + reconnect logic for the Janito web chat.

class ChatSocket {
    constructor(sessionId, handlers = {}) {
        this.sessionId = sessionId;
        this.handlers = handlers;   // { onEvent, onOpen, onClose, onError }
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.manualClose = false;
    }

    connect() {
        this.manualClose = false;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let url = `${protocol}//${window.location.host}/api/chat/ws/${encodeURIComponent(this.sessionId)}`;
        const token = window.__JANITO_TOKEN__;
        if (token) {
            url += `?token=${encodeURIComponent(token)}`;
        }

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            if (this.handlers.onOpen) this.handlers.onOpen();
        };

        this.ws.onmessage = (msg) => {
            try {
                const event = JSON.parse(msg.data);
                if (this.handlers.onEvent) this.handlers.onEvent(event);
            } catch (e) {
                console.error('Failed to parse WS message:', e, msg.data);
            }
        };

        this.ws.onclose = (e) => {
            if (this.handlers.onClose) this.handlers.onClose(e);
            if (!this.manualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = this.reconnectDelay * this.reconnectAttempts;
                setTimeout(() => this.connect(), delay);
            }
        };

        this.ws.onerror = (e) => {
            console.error('WebSocket error:', e);
            if (this.handlers.onError) this.handlers.onError(e);
        };
    }

    send(obj) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(obj));
            return true;
        }
        return false;
    }

    sendPrompt(content) {
        return this.send({ type: 'prompt', content });
    }

    get isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    close() {
        this.manualClose = true;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
