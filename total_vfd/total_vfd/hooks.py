app_name = "total_vfd"
app_title = "Total VFD"
app_publisher = "Total VFD Integration"
app_description = "Fiscalise Sales and POS invoices via Total VFD API (Tanzania TRA)"
app_email = "support@example.com"
app_license = "MIT"
app_version = "1.0.3"

required_apps = ["erpnext"]

before_install = "total_vfd.install.before_install"
after_install = "total_vfd.install.after_install"
boot_session = "total_vfd.boot.boot_session"

add_to_apps_screen = [
    {
        "name": "total_vfd",
        "logo": "/assets/total_vfd/images/total_vfd.svg",
        "title": "Total VFD",
        "route": "/app/total-vfd-settings",
        "has_permission": "total_vfd.api.setup_hub.has_app_permission",
    }
]

doc_events = {
    "Sales Invoice": {
        "validate": [
            "total_vfd.api.pos_defaults.apply_sales_fiscalise_default",
            "total_vfd.api.fiscal_service.validate_sales_fiscalise_license",
        ],
        "on_submit": "total_vfd.api.fiscal_service.fiscalise_sales_invoice",
    },
    "POS Invoice": {
        "validate": "total_vfd.api.pos_defaults.apply_pos_fiscalise_default",
        "on_submit": "total_vfd.api.fiscal_service.fiscalise_pos_invoice",
    },
    "POS Profile": {
        "validate": "total_vfd.api.pos_defaults.sync_pos_profile_print_format",
    },
    "Company": {
        "on_update": "total_vfd.api.setup_hub.company_updated",
    },
}

scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "total_vfd.api.fiscal_service.process_queue",
        ],
        "0 6 * * *": [
            "total_vfd.total_vfd.doctype.total_vfd_license.total_vfd_license.cron_check_license",
        ],
    },
}

fixtures = ["custom_field.json", "role.json"]

app_include_js = [
    "/assets/total_vfd/js/total_vfd_utils.js",
    "/assets/total_vfd/js/pos_fiscal_bridge.js",
    "/assets/total_vfd/js/total_vfd_boot.js",
]

doctype_js = {
    "Total VFD License": "public/js/total_vfd_license_redirect.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "POS Invoice": "public/js/pos_invoice.js",
    "POS Profile": "public/js/pos_profile.js",
    "Company": "public/js/company.js",
    "Total VFD Settings": "public/js/total_vfd_settings.js",
}

doctype_list_js = {
    "Total VFD Fiscal Log": "public/js/total_vfd_fiscal_log_list.js",
}
