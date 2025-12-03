document.addEventListener('DOMContentLoaded', function() {
    const addCustomFieldBtn = document.getElementById('add_custom_field_btn');
    const customFieldsContainer = document.getElementById('custom_fields_container');

    if (addCustomFieldBtn && customFieldsContainer) {
        addCustomFieldBtn.addEventListener('click', function() {
            const fieldGroup = document.createElement('div');
            fieldGroup.classList.add('row', 'mb-2', 'g-2', 'align-items-center');

            fieldGroup.innerHTML = `
                <div class="col-5">
                    <input type="text" class="form-control form-control-sm" name="custom_field_keys[]" placeholder="Field Name (e.g., Signature)" required>
                </div>
                <div class="col-5">
                    <input type="text" class="form-control form-control-sm" name="custom_field_values[]" placeholder="Field Value" required>
                </div>
                <div class="col-2">
                    <button type="button" class="btn btn-danger btn-sm remove-custom-field-btn">X</button>
                </div>
            `;
            customFieldsContainer.appendChild(fieldGroup);

            // Add event listener to the new remove button
            fieldGroup.querySelector('.remove-custom-field-btn').addEventListener('click', function() {
                fieldGroup.remove();
            });
        });
    }

    // Handle "Select All" checkbox for participants page
    const selectAllParticipantsCheckbox = document.getElementById('select_all_participants');
    if (selectAllParticipantsCheckbox) {
        selectAllParticipantsCheckbox.addEventListener('change', function() {
            document.querySelectorAll('input[name="participant_ids"]').forEach(checkbox => {
                checkbox.checked = selectAllParticipantsCheckbox.checked;
            });
        });
    }
});
