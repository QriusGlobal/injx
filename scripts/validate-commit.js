#!/usr/bin/env bun

const fs = require('fs');
const { execSync } = require('child_process');
const lint = require('@commitlint/lint').default;

// The first argument from pre-commit is the path to the COMMIT_EDITMSG file
const commitMsgFile = process.argv[2];
if (!commitMsgFile) {
  console.error('Error: Commit message file path not provided.');
  process.exit(1);
}
const commitMessage = fs.readFileSync(commitMsgFile, 'utf8');

// 1. Define Rule Sets based on the project's validation hierarchy
const validationHierarchy = {
  // Highest priority: src/ changes
  src: {
    rules: {
      'type-enum': [2, 'always', ['feat', 'fix', 'perf', 'refactor']],
    },
    name: 'Source Code'
  },
  // Next priority: Infrastructure changes
  infrastructure: {
    rules: {
      'type-enum': [2, 'always', ['chore', 'ci', 'docs', 'test', 'build', 'style', 'refactor']],
    },
    name: 'Infrastructure'
  },
  // Lowest priority: Config-only changes
  config: {
    rules: {
      'type-enum': [
        2,
        'always',
        ['feat', 'fix', 'perf', 'refactor', 'chore', 'ci', 'docs', 'test', 'build', 'style'],
      ],
    },
    name: 'Configuration'
  },
};

// 2. Get staged files from git
const stagedFilesOutput = execSync('git diff --cached --name-only', { encoding: 'utf8' });
const stagedFiles = stagedFilesOutput.trim().split('\n').filter(Boolean);

// 3. Determine which rule set to apply based on STRICT hierarchy (src/ beats everything)
let activeValidation;

// Priority 1 (HIGHEST): src/ changes - beats everything, even if mixed with infrastructure/config
if (stagedFiles.some(file => file.startsWith('src/'))) {
  activeValidation = validationHierarchy.src;
}
// Priority 2: Infrastructure changes - beats config only
else if (stagedFiles.some(file =>
    file.startsWith('.github/') ||
    file.startsWith('tests/') ||
    file.startsWith('docs/') ||
    file.startsWith('scripts/') ||
    file.endsWith('.md')
)) {
  activeValidation = validationHierarchy.infrastructure;
}
// Priority 3 (LOWEST): Config files only
else {
  activeValidation = validationHierarchy.config;
}

console.log(`[injx-validator] Applying "${activeValidation.name}" validation rules.`);

// 4. Load base conventional config and merge the active ruleset
const conventionalConfig = require('@commitlint/config-conventional');
const finalRules = { ...conventionalConfig.rules, ...activeValidation.rules };

// 5. Lint the commit message against the dynamic rules
lint(commitMessage, finalRules)
  .then(report => {
    if (report.valid) {
      console.log('[injx-validator] Commit message is valid.');
      process.exit(0);
    } else {
      console.error('\n❌ Commit message validation failed:');
      report.errors.forEach(err => console.error(`  - ${err.message}`));
      report.warnings.forEach(warn => console.warn(`  - (WARN) ${warn.message}`));
      console.error('\nPlease fix your commit message and try again.');
      process.exit(1);
    }
  })
  .catch(err => {
    console.error('[injx-validator] Error running commitlint:', err);
    process.exit(1);
  });