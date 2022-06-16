export { initialize_process_statuses };

let HEARTBEAT_THRESHOLD_SECS = 10;
let RESTARTING_THRESHOLD_SECS = 30;

function load_statuses() {
    const url = '/api/deploy';
    $.get({
        url: url,
        contentType: 'json',
        success: function (data) {
            show_statuses(data.statuses);

            setTimeout(load_statuses, 1000);
        },
        error: function (x, y, z) {
            console.log(x, y, z);
        },
    });
}

function change_process(status, process_name) {
    $.post({
        url: '/api/deploy/' + process_name + '/' + status,
        dataType: 'json',
        success: function (data) {
            console.log('STDOUT:', data.stdout);
            console.log('STDERR:', data.stderr);
        },
        error: function () {
            console.log('ERROR! See logs.');
        },
    });
}

function show_statuses(statuses) {
    $('#statuses-tbody').empty();
    statuses.forEach(function(status) {
        let columns = [];

        columns.push(`${status.process_name}`);
        if (status.last_heartbeat_ago > HEARTBEAT_THRESHOLD_SECS) {
            columns.push('<span class="badge badge-danger">Down</span>');
        } else if (status.last_started_ago < RESTARTING_THRESHOLD_SECS) {
            columns.push('<span class="badge badge-warning">Restarting</span>');
        } else {
            columns.push('<span class="badge badge-success">Up</span>');
        }
        columns.push(status.git_sha);
        columns.push(moment(status.last_started_at));

        let last_heartbeat_at = moment(status.last_heartbeat_at);
        if (status.last_heartbeat_ago > 60) {
            columns.push(`${last_heartbeat_at} (60+ seconds ago)`);
        } else {
            columns.push(`${last_heartbeat_at} (${status.last_heartbeat_ago} seconds ago)`);
        }

        if (status.target_configured === true) {
            columns.push(`
            <button type="button" class="btn btn-sm btn-danger w-100 mb-2" id="${status.process_name}-stop">Stop</button>
        `);
            columns.push(`
            <button type="button" class="btn btn-sm btn-warning w-100 mb-2" id="${status.process_name}-restart">Restart</button>
        `);
            columns.push(`
            <button type="button" class="btn btn-sm btn-success w-100 mb-2" id="${status.process_name}-update">Update</button>
        `);
        } else {
            columns.push(`
            <button type="button"
                class="btn btn-sm btn-secondary w-100 mb-2"
                disabled
                id="${status.process_name}-stop">Stop</button>
            `);
            columns.push(`
            <button type="button"
                class="btn btn-sm btn-secondary w-100 mb-2"
                disabled
                id="${status.process_name}-restart">Restart</button>
            `);
            columns.push(`
            <button type="button"
                class="btn btn-sm btn-secondary w-100 mb-2"
                disabled
                id="${status.process_name}-update">Update</button>
            `);
        }

        let tds = columns.map(c => `<td>${c}</td>`).join('');
        $('#statuses-tbody').append(`<tr>${tds}</tr>`);
    });
    statuses.forEach(function (status) {
        let process_name = status.process_name;
        $(`#${process_name}-stop`).on('click', function () {
            change_process('stop', process_name)
        });
        $(`#${process_name}-restart`).on('click', function () {
            change_process('restart', process_name)
        });
        $(`#${process_name}-update`).on('click', function () {
            change_process('update', process_name)
        });
    });
}

function initialize_process_statuses(id) {
    let contents = `
            <div class="table-responsive">
                <table class="table table-striped table-sm">
                    <thead>
                    <tr>
                        <th>Process</th>
                        <th>Status</th>
                        <th>SHA</th>
                        <th>Last Started</th>
                        <th>Last Heartbeat</th>
                        <th></th>
                        <th></th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody id="statuses-tbody">
                    </tbody>
                </table>
            </div>
    `;

    $(`#${id}`).html(contents);
    load_statuses();
}
