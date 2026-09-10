import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function honoVersionFromLockfile(): string {
  const lockPath = join(import.meta.dirname, '..', 'package-lock.json');
  const lock = JSON.parse(readFileSync(lockPath, 'utf8')) as {
    packages: Record<string, { version?: string } | undefined>;
  };
  return lock.packages['node_modules/hono']?.version ?? '';
}

describe('security dependency pins', () => {
  it('overrides hono to a release that patches GHSA-crvj-82cr-hjcx and GHSA-gqvv-2mrq-wpjv', () => {
    const version = honoVersionFromLockfile();
    const [major, minor, patch] = version.split('.').map(Number);
    const patched =
      major > 4 || (major === 4 && minor > 13) || (major === 4 && minor === 13 && patch >= 7);
    expect(patched).toBe(true);
  });

  it('finds frontend/package-lock.json when the process cwd is the repository root', () => {
    const previous = process.cwd();
    process.chdir(join(import.meta.dirname, '..', '..'));
    try {
      expect(honoVersionFromLockfile().length).toBeGreaterThan(0);
    } finally {
      process.chdir(previous);
    }
  });
});
