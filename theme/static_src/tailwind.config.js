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
    /* JS 1: Ignore any JavaScript in node_modules Folder. */
    // '!../../**/node_modules',
    /* JS 2: Process all JavaScript files in the project. */
    // '../../**/*.js',
    '../../**/static/js/*.js',

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
        heading: ['Candara', 'Calibri', 'Corbel', 'sans'],
        subheading: ['Verdana', 'Tahoma', 'sans'],
        para: ['Verdana', 'Tahoma', 'sans'],
        // para: ['Constantia', 'Cambria', 'serif'],
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
        // "hl-tertiary": "#bea2f2",
        "accept": "#38c17f",
        "cancel": "#f4425f",
        "info": "rgb(164 174 240)",
        "info-inverted": "rgb(66 89 237)",
        "warn": "#F7A71B",
        "plotly-bg": "#111111",
      },
      maxWidth: {
        '1/5': '20%',
        '1/4': '25%',
        '1/3': '33%',
        '1/2': '50%',
      },
      keyframes: {
        flip180: {
          "0%": { transform: "rotate(0)" },
          "100%": { transform: "rotate(-180deg)" },
        },
        spin: {
          "0%": { transform: "roatate(0deg)" },
          "100%": { transform: "roatate(360deg)" },
        }
      },
    },
    animation: {
      "flip-icon": "flip180 0.25s linear forwards",
      "spin-slow": "spin 2s linear infinite",
    }
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
