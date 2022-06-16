import * as durapy from "./durapy.js";

$(document).ready(function() {
    let searchParams = new URLSearchParams(window.location.search)
    let key = searchParams.has('key') ? searchParams.get('key') : null;
    durapy.initialize_commands_send('commands-send-container', key, '/commands/history');
});
