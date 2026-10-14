import { describe, it, expect } from 'vitest'
import {
  parseMinimumNode,
  parseVersion,
  compareVersions,
  checkNodeVersion
} from './nodeVersion'

describe('parseMinimumNode', () => {
  it('parses a plain >=X.Y.Z range', () => {
    expect(parseMinimumNode('>=20.19.0')).toEqual({ major: 20, minor: 19, patch: 0 })
  })

  it('tolerates surrounding whitespace', () => {
    expect(parseMinimumNode('  >=22.13.0  ')).toEqual({ major: 22, minor: 13, patch: 0 })
  })

  it('returns null for unsupported range syntax (fail closed)', () => {
    expect(parseMinimumNode('^20.19.0')).toBeNull()
    expect(parseMinimumNode('>=20 || >=22')).toBeNull()
    expect(parseMinimumNode('20.x')).toBeNull()
    expect(parseMinimumNode('')).toBeNull()
    expect(parseMinimumNode(undefined)).toBeNull()
    expect(parseMinimumNode(null)).toBeNull()
  })
})

describe('parseVersion', () => {
  it('parses a full version and strips a leading v', () => {
    expect(parseVersion('v20.19.4')).toEqual({ major: 20, minor: 19, patch: 4 })
    expect(parseVersion('22.13.0')).toEqual({ major: 22, minor: 13, patch: 0 })
  })

  it('ignores prerelease/build suffixes after the patch level', () => {
    expect(parseVersion('23.0.0-nightly20250101')).toEqual({ major: 23, minor: 0, patch: 0 })
  })

  it('returns null for unparseable input', () => {
    expect(parseVersion('twenty')).toBeNull()
    expect(parseVersion('')).toBeNull()
  })
})

describe('compareVersions', () => {
  it('orders by major, then minor, then patch', () => {
    const v = (major, minor, patch) => ({ major, minor, patch })
    expect(compareVersions(v(20, 19, 0), v(20, 19, 0))).toBe(0)
    expect(compareVersions(v(20, 18, 9), v(20, 19, 0))).toBe(-1)
    expect(compareVersions(v(21, 0, 0), v(20, 19, 0))).toBe(1)
    expect(compareVersions(v(20, 19, 1), v(20, 19, 0))).toBe(1)
    expect(compareVersions(v(20, 20, 0), v(20, 19, 99))).toBe(1)
  })
})

describe('checkNodeVersion', () => {
  it('accepts the exact minimum version', () => {
    const result = checkNodeVersion('20.19.0', '>=20.19.0')
    expect(result.ok).toBe(true)
    expect(result.required).toEqual({ major: 20, minor: 19, patch: 0 })
  })

  it('accepts newer major versions', () => {
    expect(checkNodeVersion('22.13.0', '>=20.19.0').ok).toBe(true)
    expect(checkNodeVersion('25.1.0', '>=20.19.0').ok).toBe(true)
  })

  it('rejects a version below the minimum patch/minor', () => {
    expect(checkNodeVersion('20.18.9', '>=20.19.0').ok).toBe(false)
    expect(checkNodeVersion('18.20.0', '>=20.19.0').ok).toBe(false)
  })

  it('fails closed when the range syntax is unsupported', () => {
    const result = checkNodeVersion('25.1.0', '^20.19.0')
    expect(result.ok).toBe(false)
    expect(result.reason).toMatch(/unsupported/)
  })

  it('fails closed when the current version cannot be parsed', () => {
    const result = checkNodeVersion('not-a-version', '>=20.19.0')
    expect(result.ok).toBe(false)
    expect(result.reason).toMatch(/cannot parse/)
  })

  it('fails closed when engines.node is missing', () => {
    expect(checkNodeVersion('25.1.0', undefined).ok).toBe(false)
  })
})
