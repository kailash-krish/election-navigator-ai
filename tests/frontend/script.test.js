const ElectionNavigator = require('../../static/script.js');

describe('ElectionNavigator AI Frontend Logic', () => {
  test('categorizeQuery identifies eligibility', () => {
    expect(ElectionNavigator._categorizeQuery('Am I eligible to vote?')).toBe('eligibility');
    expect(ElectionNavigator._categorizeQuery('Do I qualify?')).toBe('eligibility');
  });

  test('categorizeQuery identifies registration', () => {
    expect(ElectionNavigator._categorizeQuery('How to get voter id')).toBe('registration');
    expect(ElectionNavigator._categorizeQuery('Where is form 6')).toBe('registration');
  });

  test('categorizeQuery identifies timeline', () => {
    expect(ElectionNavigator._categorizeQuery('Show election schedule')).toBe('timeline');
    expect(ElectionNavigator._categorizeQuery('What are the phases?')).toBe('timeline');
  });

  test('state is encapsulated and accessible', () => {
    const state = ElectionNavigator.getState();
    expect(state).toHaveProperty('language', 'en');
    expect(state).toHaveProperty('context', []);
    expect(state).toHaveProperty('progress');
  });
});
