export { WebSocketTailer };

function escapeHtml(string) {
    // https://stackoverflow.com/questions/24816/escaping-html-strings-with-jquery
    var entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };

    return String(string).replace(/[&<>"'`=\/]/g, function (s) {
        return entityMap[s];
    });
}

class WebSocketTailer {
    constructor(textarea_id) {
        let ws = new WebSocket(`ws://${window.location.host}/ws/tail`);
        let logs = $('#' + textarea_id);

        ws.onopen = function () {
            logs.html(logs.html() + '==== CONNECTED ====\n\n');
        };
        ws.onclose = function () {
            logs.html(logs.html() + '\n\n==== DISCONNECTED ====');
        };

        this.whitelist_processes = null;

        let that = this;
        ws.onmessage = function (event) {
            let tabs = event.data.split("\t");

            let timestamp = '';
            let app_name = '';
            let message_type = '';
            let message_message = '';

            if (tabs.length === 3) {
                timestamp = tabs[0];
                app_name = tabs[1];

                if (that.whitelist_processes !== null && !that.whitelist_processes.includes(app_name)) {
                    // Not whitelisted; ignore.
                    return;
                }

                try {
                    let message = JSON.parse(tabs[2]);
                    message_type = message['type'];
                    message_message = message['message'];
                } catch (e) {
                    message_type = '';
                    message_message = tabs[2];
                }
            } else {
                message_message = event.data;
            }

            let line = `${timestamp}\t${app_name}\t${message_type}\t${message_message}`;
            logs.html(logs.html() + escapeHtml(line) + '\n');
            logs[0].scrollTop = logs[0].scrollHeight;
        };
        this.ws = ws;
    }

    set_whitelisted_processes(processes) {
        this.whitelist_processes = processes;
    }
}
