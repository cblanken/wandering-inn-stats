/** @type {import('stylelint').Config} */
export default {
  extends: ['stylelint-config-recommended'],
  rules: {
    'at-rule-no-unknown': [
      true,
      {
        ignoreAtRules: [
          'apply',
          'plugin',
          'responsive',
          'screen',
          'source',
          'tailwind',
          'theme',
          'variants',
        ],
      },
    ],
  },
};
