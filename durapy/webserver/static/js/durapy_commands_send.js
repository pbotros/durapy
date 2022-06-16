export { initialize_commands_send };

function _input_value(t) {
    if (t.attr('type') === 'checkbox') {
        return t.prop('checked');
    } else {
        if (t.val() !== ''){
            return t.val();
        } else {
            return t.attr('placeholder');
        }

    }
}

function send_command(command_type, redirect_on_success) {
    let form = $(`#${command_type} form`);
    form.find("button[type='submit']").prop('disabled', true);
    let inputs = form.find('input,select').filter(function () {
        let val = _input_value($(this));
        if (typeof val === 'string' && val.length <= 0) {
            return false;
        }
        return val !== undefined && val !== null;
    });

    let field_descriptions = [];
    inputs.each(function () {
        let input_val = _input_value($(this));
        let field_id = $(this).attr('data-id');
        field_descriptions.push({
            'id': field_id,
            'val': input_val,
        });
    });

    $.post({
        url: '/api/commands',
        data: JSON.stringify({
            'type': command_type,
            'field_descriptions': field_descriptions,
        }),
        contentType: 'application/json',
        dataType: 'json',
        success: function (data) {
            console.log('Successfully sent ', data);
            if (redirect_on_success !== null) {
                window.location.href = redirect_on_success;
            }
        },
        error: function () {
            console.log('ERROR! See logs.');
            form.find("button[type='submit']").prop('disabled', false);
        },
    });
    return false;
}

function initialize_commands_send(id, key, redirect_on_success) {
    let command_types_get = $.get({
        url: '/api/command-types',
        contentType: 'applicaton/json',
    });
    if (key !== null) {
        $.when(
            command_types_get,
            $.get({
                url: `/api/commands/${key}`,
                contentType: 'applicaton/json',
            }))
            .done(function (data_command_types, data_command) {
                handle_command_types(id, data_command_types[0].command_types, data_command[0].command, redirect_on_success);
            })
            .fail(function () {
                console.log('Fail??');
            });
    } else {
        command_types_get
            .done(function (data) {
                handle_command_types(id, data.command_types, null, redirect_on_success);
            })
            .fail(function () {
                console.log('Fail??');
            });
    }
}

function handle_command_types(id, command_types, existing_command, redirect_on_success) {
    let active_command_type;
    if (existing_command !== null) {
        active_command_type = existing_command['type'];
    } else {
        active_command_type = '';
    }

    let commands_html = '';
    command_types.forEach(function(command) {
        commands_html += `
            <li class="nav-item">
                <a class="nav-link ${command.type === active_command_type ? "active" : ""}" data-toggle="pill"
                   href="#${command.type}">${command.type}</a>
            </li>
        `
    });
    let pills_container_html = `
        <div class="mt-2">
            <ul class="nav nav-pills mt-4 mb-4" id="command-pills">
            ${commands_html}
            </ul>
        </div>
    `;

    let body_html = '';
    command_types.forEach(function (command_class) {
        let active_class = command_class.type === active_command_type ? "active" : "";
        body_html += `
                    <div class="tab-pane show ${active_class}" id="${command_class.type}"
                         role="tabpanel">
                        <form>
                        `;
        let fds;
        if (existing_command !== null && existing_command.type === command_class.type) {
            fds = existing_command['field_descriptions'];
        } else {
            fds = command_class.field_descriptions;
        }
        fds.forEach(function (fd) {
            // Unique identifier across all fields across all classes
            let fd_id_global = `${fd.parent_class_name}-${fd.id}`;
            body_html += `
                    <div class="form-group row">
                        <div class="col-sm-4 col-form-label text-right">
                            <small class="form-text d-inline-block text-muted">${fd.hint}</small>
                            <label for="${fd_id_global}">${fd.id}</label>
                        </div>`;
            if (fd.allowed) {
                body_html += `
                        <select class="custom-select form-control col-sm-6"
                                id="${fd_id_global}"
                                data-id="${fd.id}"
                                data-parent-class-name="${fd.parent_class_name}">`;
                fd.allowed.forEach(function (opt) {
                    let is_selected = (fd.placeholder === opt) || (fd.val === opt);
                    body_html += `
                            <option value="${opt}" ${is_selected ? "selected" : ""}>${opt}</option>
                    `;
                });
                body_html += '</select>';
            } else if (fd.is_bool) {
                let is_checked = fd.val || fd.placeholder;
                body_html += `
                        <div class="form-check">
                            <div class="col-sm-6">
                                <input class="form-check-input position-static mt-2" type="checkbox"
                                       data-id="${fd.id}"
                                       data-parent-class-name="${fd.parent_class_name}"
                                       value=""
                                       ${is_checked ? "checked" : ""}
                                       id="${fd_id_global}">
                            </div>
                        </div>`;
            } else {
                body_html += `
                        <input type="text" class="form-control col-sm-6" id="${fd_id_global}"
                               data-id="${fd.id}"
                               data-parent-class-name="${fd.parent_class_name}"
                               ${fd.placeholder ? `placeholder="${fd.placeholder}"` : ''}
                               ${fd.val ? `value="${fd.val}"` : ''}
                               ${fd.placeholder === null && fd.optional === false ? 'required' : ''}
                        >
                `
            }
            body_html += `</div>`;
        });

        body_html += `
                <button type="submit" class="btn btn-primary">Submit</button>
            </form>
        </div>`;
    });

    let body_container_html = `
            <div class="tab-content" id="commands-send-body">
            ${body_html}
            </div>
    `;

    $(`#${id}`).html(pills_container_html + body_container_html);
    command_types.forEach(function (command_class) {
        let command_class_temp = command_class.type;
        $(`#${command_class_temp} form`).on('submit', function() {
            send_command(command_class_temp, redirect_on_success);
        });
    });
}
