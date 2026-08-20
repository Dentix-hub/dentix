module.exports = {
    root: true,
    env: { browser: true, es2020: true },
    extends: [
        'eslint:recommended',
        'plugin:react/recommended',
        'plugin:react/jsx-runtime',
        'plugin:react-hooks/recommended',
    ],
    ignorePatterns: ['dist', '.eslintrc.cjs'],
    parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    settings: { react: { version: '18.2' } },
    plugins: ['react-refresh'],
    rules: {
        'react-refresh/only-export-components': [
            'warn',
            {
                allowConstantExport: true,
                allowExportNames: ['motion', 'useProcedures', 'toast'],
            },
        ],
        'react/prop-types': 'off',
        'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        'react/no-unknown-property': ['error', { ignore: ['css'] }],
    },
    overrides: [
        {
            files: ['playwright.config.js', 'e2e/**/*.js'],
            env: { node: true },
        },
        {
            files: ['src/setupTests.js', 'src/**/*.test.js', 'src/**/*.test.jsx'],
            globals: {
                global: 'readonly',
                describe: 'readonly',
                it: 'readonly',
                test: 'readonly',
                expect: 'readonly',
                vi: 'readonly',
            },
        },
    ],
}
