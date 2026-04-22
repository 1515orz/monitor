function monitor() {
  return {
    connected: false,
    state: {},
    _retryDelay: 500,

    init() {
      this._connect();
    },

    _connect() {
      const ws = new WebSocket(`ws://${location.host}/ws/state`);

      ws.onopen = () => {
        this.connected = true;
        this._retryDelay = 500;
      };

      ws.onmessage = (e) => {
        this.state = JSON.parse(e.data);
      };

      ws.onclose = () => {
        this.connected = false;
        setTimeout(() => this._connect(), this._retryDelay);
        this._retryDelay = Math.min(this._retryDelay * 2, 5000);
      };

      ws.onerror = () => ws.close();
    },
  };
}
