// Using globals from vitest setup
test('basic math works', () => {
    expect(1 + 1).toBe(2);
});

test('strings work', () => {
    expect('hello').toContain('ell');
});
