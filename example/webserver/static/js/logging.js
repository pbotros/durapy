import * as durapy from "./durapy.js";

let TAILER = null;

$(document).ready(function() {
    TAILER = new durapy.WebSocketTailer('example-process-logging');
});
