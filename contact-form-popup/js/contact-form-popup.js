jQuery(document).ready(function($) {

    // 1. Show popup when .contact-popup is clicked
    $('.contact-popup').on('click', function(e) {
        e.preventDefault();
        const staffId = $(this).data('staffid');

        // 2. Retrieve staff email via AJAX
        $.ajax({
            url: cfpData.ajaxUrl,
            type: 'POST',
            data: {
                action: 'cfp_get_staff_email',
                nonce: cfpData.nonce,
                staff_id: staffId
            },
            success: function(response) {
                if (response.success) {
                    // Put the staff email into our hidden field
                    $('#cfp-staff-email').val(response.data.email);
                    // Show the popup
                    $('#cfp-popup-overlay').fadeIn();
                } else {
                    alert('Staff email not found.');
                }
            }
        });
    });

    // 3. Close the popup
    $('#cfp-popup-close').on('click', function() {
        $('#cfp-popup-overlay').fadeOut();
    });

    // 4. Submit the form and send email
    $('.cfp-contact-form').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();

        $.ajax({
            url: cfpData.ajaxUrl,
            type: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    alert(response.data.message);
                    $('#cfp-popup-overlay').fadeOut();
                } else {
                    alert(response.data.message);
                }
            }
        });
    });
});
