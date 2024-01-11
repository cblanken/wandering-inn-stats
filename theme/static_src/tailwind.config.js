/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

const defaultTheme = require("tailwindcss/defaultTheme")

module.exports = {
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        container: {
            center: true,
        },
        extend: {
            fontFamily: {
                heading: ['Amatic SC', 'cursive'],
                subheading: ['Andika', 'sans'],
                para: ['Cambria', 'serif'],
            },
            colors: {
                "bg-primary": "#262b2cff",
                "bg-secondary": "#313638ff",
                "bg-tertiary": "#424647ff",
                "text-primary": "#e8e9ebff",
                "text-secondary": "#e0dfd5ff",
                "text-tertiary": "#e6cea7ff",
                "text-disabled": "#a68e77ff",
                "hl-primary": "#ef6461ff",
                "hl-secondary": "#ea8c62ff",
                "hl-tertiary": "#e4b363ff",
                "accept": "#38c17f",
                "cancel": "#f4425f",
                "info": "#8492F4",
                "warn": "#F7A71B",
            },
        },
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/line-clamp'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
