<?php
/**
 * Plugin Name: Contact Form Popup
 * Description: A simple contact form popup that fetches staff email from a custom post type and sends inquiries via AJAX, now with reCAPTCHA + honeypot.
 * Version: 1.1
 * Author: Tessa Tech
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Enqueue scripts and styles
 */
function cfp_enqueue_scripts() {
    // Enqueue jQuery (if not already loaded)
    wp_enqueue_script('jquery');

    // Enqueue custom JS
    wp_enqueue_script(
        'cfp-js',
        plugin_dir_url(__FILE__) . 'js/contact-form-popup.js',
        array('jquery'),
        '1.2',
        true
    );

    // Localize script for AJAX URL, Nonce, and reCAPTCHA site key
    wp_localize_script(
        'cfp-js',
        'cfpData',
        array(
            'ajaxUrl'      => admin_url('admin-ajax.php'),
            'nonce'        => wp_create_nonce('cfp_nonce'),
            'recaptchaKey' => '6Lc-iMQrAAAAALLi9UvN9gG93rjVhZGBtkz40HZx', // Replace with your actual Site Key
        )
    );

    // Enqueue reCAPTCHA script
    wp_enqueue_script(
        'google-recaptcha',
        'https://www.google.com/recaptcha/api.js',
        array(),
        null,
        true
    );

    // Enqueue custom CSS
    wp_enqueue_style(
        'cfp-css',
        plugin_dir_url(__FILE__) . 'css/contact-form-popup.css',
        array(),
        '1.1'
    );
}
add_action('wp_enqueue_scripts', 'cfp_enqueue_scripts');

/**
 * Add settings page to the admin menu
 */
function cps_add_settings_page() {
    add_submenu_page(
        'options-general.php', // Parent slug (Settings)
        'Contact Popup Settings', // Page title
        'Contact Popup', // Menu title
        'manage_options', // Capability
        'contact-popup-settings', // Menu slug
        'cps_render_settings_page' // Callback function
    );
}
add_action('admin_menu', 'cps_add_settings_page');

/**
 * Render the settings page
 */
function cps_render_settings_page() {
    ?>
    <div class="wrap">
        <h1>Contact Popup Settings</h1>
        <form method="post" action="options.php">
            <?php
            settings_fields('cps_options_group'); // Settings group
            do_settings_sections('contact-popup-settings'); // Page slug
            submit_button();
            ?>
        </form>
    </div>
    <?php
}

/**
 * Register settings and fields
 */
function cps_register_settings() {
    // Default form content
    $default_form_content = '
    <form id="cfp-contact-form" class="cfp-contact-form">
        <!-- Honeypot (hidden) field to detect bots -->
        <p class="cfp-honeypot-field" style="display:none;">
            <label for="cfp_hp">Leave this field empty</label>
            <input type="text" id="cfp_hp" name="cfp_hp" value="" />
        </p>

        <!-- Hidden fields to store staff email and handle AJAX submission -->
        <input type="hidden" id="cfp-staff-email" name="staff_email" value="" />
        <input type="hidden" name="action" value="cfp_send_mail" />

        <p>
            <label for="cfp-name">Name:</label><br />
            <input type="text" id="cfp-name" name="name" required />
        </p>

        <p>
            <label for="cfp-phone">Phone:</label><br />
            <input type="text" id="cfp-phone" name="phone" required />
        </p>

        <p>
            <label for="cfp-email">Your Email:</label><br />
            <input type="email" id="cfp-email" name="email" required />
        </p>

        <p>
            <label for="cfp-message">How can we help you?</label><br />
            <textarea id="cfp-message" name="message" rows="4"></textarea>
        </p>

        <p>
            <label for="cfp-hearabout">How did you hear about us?</label><br />
            <select name="hearabout">
                <option value="Event">Event</option>
                <option value="Referral">Referral</option>
                <option value="Internet">Internet</option>
                <option value="Article">Article</option>
                <option value="Advertisement">Advertisement</option>
            </select>
        </p>

        <!-- reCAPTCHA widget -->
        <div class="g-recaptcha" data-sitekey="6Lc-iMQrAAAAALLi9UvN9gG93rjVhZGBtkz40HZx"></div>

        <p>
            <button type="submit">Send</button>
        </p>
    </form>';

    // Register settings
    register_setting('cps_options_group', 'cps_options', 'cps_sanitize_options');

    // Add settings section
    add_settings_section(
        'cps_main_section', // Section ID
        'Contact Form Settings', // Section title
        'cps_section_text', // Callback function
        'contact-popup-settings' // Page slug
    );

    // Add email sender field
    add_settings_field(
        'cps_email_sender', // Field ID
        'Email Sender', // Field title
        'cps_email_sender_input', // Callback function
        'contact-popup-settings', // Page slug
        'cps_main_section' // Section ID
    );

    // Add additional emails field
    add_settings_field(
        'cps_additional_emails', // Field ID
        'Additional Emails', // Field title
        'cps_additional_emails_input', // Callback function
        'contact-popup-settings', // Page slug
        'cps_main_section' // Section ID
    );

    // Add form content field
    add_settings_field(
        'cps_form_content', // Field ID
        'Form Content', // Field title
        'cps_form_content_input', // Callback function
        'contact-popup-settings', // Page slug
        'cps_main_section' // Section ID
    );

    // Set default form content if not already set
    $options = get_option('cps_options');
    if (empty($options['form_content'])) {
        $options['form_content'] = $default_form_content;
        update_option('cps_options', $options);
    }
}
add_action('admin_init', 'cps_register_settings');

/**
 * Section text
 */
function cps_section_text() {
    echo '<p>Configure the contact popup form settings.</p>';
}

/**
 * Email sender input field
 */
function cps_email_sender_input() {
    $options = get_option('cps_options');
    echo "<input id='cps_email_sender' name='cps_options[email_sender]' size='40' type='email' value='{$options['email_sender']}' />";
}

/**
 * Additional emails input field
 */
function cps_additional_emails_input() {
    $options = get_option('cps_options');
    echo "<input id='cps_additional_emails' name='cps_options[additional_emails]' size='40' type='text' value='{$options['additional_emails']}' />";
    echo "<p class='description'>Enter additional emails separated by commas.</p>";
}

/**
 * Form content textarea
 */
function cps_form_content_input() {
    $options = get_option('cps_options');
    $form_content = isset($options['form_content']) ? $options['form_content'] : '';
    ?>
    <textarea id="cps_form_content" name="cps_options[form_content]" rows="10" cols="50"><?php echo esc_textarea($form_content); ?></textarea>
    <p class="description">Enter the HTML content for the contact form.</p>
    <h3>Preview:</h3>
    <div style="border: 1px solid #ccc; padding: 10px; margin-top: 10px;">
        <?php echo wp_kses_post($form_content); ?>
    </div>
    <?php
}

/**
 * Sanitize options
 */
function cps_sanitize_options($input) {
    $input['email_sender'] = sanitize_email($input['email_sender']);
    $input['additional_emails'] = sanitize_text_field($input['additional_emails']);
    $input['form_content'] = wp_kses_post($input['form_content']);
    return $input;
}

/**
 * Add popup HTML to footer
 */
function cfp_add_popup_html() {
    if (!is_page_template('template-contact.php')) {
        $options = get_option('cps_options');
        ?>
        <div id="cfp-popup-overlay">
            <div id="cfp-popup">
                <div class="popularblogbox-heading">Send us a message</div>
                <span id="cfp-popup-close">&times;</span>
                <div id="cfp-popup-content">
                    <form id="cfp-contact-form" class="cfp-contact-form">

                        <!-- Hidden fields to store staff email and handle AJAX submission -->
                        <input type="hidden" id="cfp-staff-email" name="staff_email" value="" />
                        <input type="hidden" name="action" value="cfp_send_mail" />
                    <?php echo wp_kses_post($options['form_content']); ?>
                    </form>
                </div>
            </div>
        </div>
        <?php
    }
}
add_action('wp_footer', 'cfp_add_popup_html');

/**
 * AJAX handler to get the staff email from a custom post type
 */
function cfp_get_staff_email() {
    check_ajax_referer('cfp_nonce', 'nonce');

    $staff_id = isset($_POST['staff_id']) ? intval($_POST['staff_id']) : 0;
    $email = '';

    if ($staff_id) {
        $staff_post = get_post($staff_id);
        if ($staff_post && $staff_post->post_type === 'scs-professionals') {
            $email = get_post_meta($staff_id, 'wpcf-user-email', true);
        }
    }

    wp_send_json_success(array('email' => $email));
}
add_action('wp_ajax_cfp_get_staff_email', 'cfp_get_staff_email');
add_action('wp_ajax_nopriv_cfp_get_staff_email', 'cfp_get_staff_email');

/**
 * AJAX handler to send the form data via email, with reCAPTCHA & honeypot
 */
function cfp_send_mail() {

    $options = get_option('cps_options');

    // Honeypot check
    if (!empty($_POST['cfp_hp'])) {
        wp_send_json_error(array('message' => 'Spam detected.'));
    }

    // reCAPTCHA verification
    $recaptcha_token = sanitize_text_field($_POST['g-recaptcha-response'] ?? '');
    if (empty($recaptcha_token)) {
        wp_send_json_error(array('message' => 'reCAPTCHA verification failed (empty token).'));
    }

    $secret_key = '6Lc-iMQrAAAAAPxeO_9ekTXPhTW1Ux-vynZbl0DM'; // Replace with your actual Secret Key
    $response = wp_remote_post('https://www.google.com/recaptcha/api/siteverify', array(
        'body' => array(
            'secret'   => $secret_key,
            'response' => $recaptcha_token,
            'remoteip' => $_SERVER['REMOTE_ADDR'],
        ),
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'reCAPTCHA request failed.'));
    }

    $body = json_decode(wp_remote_retrieve_body($response));
    if (empty($body->success) || $body->success !== true) {
        wp_send_json_error(array('message' => 'reCAPTCHA verification failed.'));
    }

    // Collect form data
    $staff_email = sanitize_email($_POST['staff_email'] ?? '');
    $name = sanitize_text_field($_POST['name'] ?? '');
    $phone = sanitize_text_field($_POST['phone'] ?? '');
    $email = sanitize_email($_POST['email'] ?? '');
    $hearabout = sanitize_text_field($_POST['hearabout'] ?? '');
    $message = sanitize_textarea_field($_POST['message'] ?? '');

    // Prepare email
    $subject = 'New Inquiry from ' . $name;
    $email_body = "Name: $name\nPhone: $phone\nEmail: $email\nHow did you hear about us: $hearabout\n\nMessage:\n$message";
    $recipients = !empty($staff_email) ? array($staff_email, $options['additional_emails']) : $options['additional_emails'];
    $headers = array(
        'From: ' . get_bloginfo('name') . ' <' . $options['email_sender'] . '>',
        'Reply-To: ' . $options['email_sender'],
    );

    // Send email
    $sent = wp_mail($recipients, $subject, $email_body, $headers);

    if ($sent) {
        wp_send_json_success(array('message' => 'Your message is sent successfully.'));
    } else {
        wp_send_json_error(array('message' => 'Failed to send the message.'));
    }
}
add_action('wp_ajax_cfp_send_mail', 'cfp_send_mail');
add_action('wp_ajax_nopriv_cfp_send_mail', 'cfp_send_mail');

/**
 * Shortcode: [cfp_form staff_id="123"]
 * Displays the same form inline (NO popup).
 */
function cfp_contact_form_shortcode($atts) {
    $atts = shortcode_atts(array(
        'staff_id' => 0,
    ), $atts, 'cfp_form');

    $options = get_option('cps_options');

    ob_start();
    ?>
    <div class="cfp-shortcode-form-container">
        <form id="cfp-contact-form" class="cfp-contact-form">

            <!-- Hidden fields to store staff email and handle AJAX submission -->
            <input type="hidden" id="cfp-staff-email" name="staff_email" value="" />
            <input type="hidden" name="action" value="cfp_send_mail" />
        <?php echo wp_kses_post($options['form_content']); ?>
        <div class="cfp-form-feedback"></div>
        </form>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('cfp_form', 'cfp_contact_form_shortcode');