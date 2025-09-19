module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Enhanced conventional commit rules for injx
    // Note: Dynamic validation in scripts/validate-commit.js overrides type-enum based on file changes
    'type-enum': [2, 'always', [
      'build', 'chore', 'ci', 'docs', 'feat', 'fix',
      'perf', 'refactor', 'revert', 'style', 'test'
    ]],
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    'body-leading-blank': [1, 'always'],
    'body-max-line-length': [2, 'always', 100],
    'footer-leading-blank': [1, 'always'],
    'footer-max-line-length': [2, 'always', 100]
  },

  // Hierarchical validation rules (used by scripts/validate-commit.js)
  hierarchicalRules: {
    src: {
      // Source code changes - library prefixes only
      'type-enum': [2, 'always', ['feat', 'fix', 'perf', 'refactor']],
      description: 'Source code changes require library commit types'
    },
    infrastructure: {
      // Infrastructure changes - infrastructure prefixes only
      'type-enum': [2, 'always', ['chore', 'ci', 'docs', 'test', 'build', 'style', 'refactor']],
      description: 'Infrastructure changes require infrastructure commit types'
    },
    config: {
      // Config-only changes - any prefix allowed
      'type-enum': [2, 'always', ['feat', 'fix', 'perf', 'refactor', 'chore', 'ci', 'docs', 'test', 'build', 'style']],
      description: 'Configuration-only changes allow any commit type'
    }
  }
};

// Export for ES modules compatibility
module.exports.default = module.exports;