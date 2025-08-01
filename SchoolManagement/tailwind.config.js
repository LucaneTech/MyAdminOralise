// tailwind.config.js
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {},
  },
  darkMode: 'class',
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark'],
  },
};
