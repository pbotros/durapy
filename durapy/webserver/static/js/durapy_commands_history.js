export { initialize_commands_history };

let last_commands_offset = 0;
const NUM_COMMANDS_PER_PAGE = 10;

function load_last_commands() {
    const url = '/api/commands';
    $.get({
        url: url,
        success: function (data) {
            show_commands(data.commands);
        },
        data: {'offset': last_commands_offset, 'num': NUM_COMMANDS_PER_PAGE},
        dataType: 'json',
        error: function (x, y, z) {
            console.log(x, y, z);
        },
    });
}

function last_commands_next() {
    last_commands_offset += NUM_COMMANDS_PER_PAGE;
    load_last_commands();
}

function last_commands_previous() {
    last_commands_offset -= NUM_COMMANDS_PER_PAGE;
    if (last_commands_offset < 0) {
        last_commands_offset = 0;
    }
    load_last_commands();
}

function show_commands(commands) {
    $('#recent-commands-tbody').empty();
    let idx = last_commands_offset + 1;
    commands.forEach(function (command) {
        let columns = [];
        columns.push(idx);
        idx += 1;
        columns.push(new Date(command.timestamp_ms).toLocaleString());
        columns.push(command.type);

        let data_table = '<table class="table table-striped table-sm">';
        data_table += '<thead><tr><th>Key</th><th>Value</th></tr></thead>';
        data_table += '<tbody>';
        command.field_descriptions.forEach(function (field_description) {
            data_table += `<tr><td>${field_description.id}</td><td>${field_description.val}</td></tr>`
        });
        data_table += '</tbody>';
        data_table += '</table>';

        if (command.field_descriptions.length > 0) {
            columns.push(data_table);
        } else {
            columns.push('N/A');
        }

        columns.push(`
                <a class="btn btn-link w-100" href="/commands/send?key=${command.key}" role="button">
                Resend
                </a>
            `);

        let tds = columns.map(c => `<td>${c}</td>`).join('');
        $('#recent-commands-tbody').append(`<tr>${tds}</tr>`);
    });
}

function initialize_commands_history(id) {
    let contents = `
        <nav aria-label="Page navigation example">
            <ul class="pagination float-right">
                <li class="page-item"><a class="page-link" href="#" id="last-commands-previous-btn">Previous</a></li>
                <li class="page-item"><a class="page-link" href="#" id="last-commands-next-btn">Next</a></li>
            </ul>
        </nav>
        <div class="table-responsive">
            <table class="table table-striped table-sm">
                <thead>
                <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Data</th>
                    <th></th>
                </tr>
                </thead>
                <tbody id="recent-commands-tbody">
                </tbody>
            </table>
        </div>
    `;

    $(`#${id}`).html(contents);
    $('#last-commands-previous-btn').on('click', last_commands_previous);
    $('#last-commands-next-btn').on('click', last_commands_next);
    load_last_commands();
}