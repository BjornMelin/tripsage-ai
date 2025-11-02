/*
 * Codemod: tests-env-stub
 *
 * Goal
 * - Replace direct process.env mutations in test files with `vi.stubEnv` and
 *   add `vi.unstubAllEnvs()` cleanup if missing.
 *
 * Scope
 * - Files matching *.test.ts or *.test.tsx
 *
 * Idempotent: yes.
 */
import type { API, FileInfo, JSCodeshift } from 'jscodeshift';

const withTs = (j: JSCodeshift) => j.withParser('ts');

function ensureVitestImport(j: JSCodeshift, root: any) {
  const hasVi = root.find(j.ImportDeclaration, { source: { value: 'vitest' } }).some((p: any) => {
    return (p.node.specifiers || []).some((s: any) => s.type === 'ImportSpecifier' && s.imported.name === 'vi');
  });
  if (!hasVi) {
    root.get().node.program.body.unshift(
      j.importDeclaration([j.importSpecifier(j.identifier('vi'))], j.literal('vitest'))
    );
  }
}

export default function transformer(file: FileInfo, api: API) {
  const j = withTs(api.jscodeshift);
  const root = j(file.source);

  const isTest = /\.test\.(ts|tsx)$/.test(file.path);
  if (!isTest) return root.toSource();

  let mutated = false;

  // Replace `process.env.FOO = 'bar'` → `vi.stubEnv('FOO', 'bar')`
  root
    .find(j.AssignmentExpression, {
      left: {
        type: 'MemberExpression',
        object: { type: 'MemberExpression', object: { type: 'Identifier', name: 'process' }, property: { name: 'env' } },
      },
      operator: '=',
    })
    .forEach((p) => {
      const left = p.node.left as any;
      const key = left.property?.name || (left.property?.value as string);
      if (!key) return;
      const call = j.expressionStatement(
        j.callExpression(j.memberExpression(j.identifier('vi'), j.identifier('stubEnv')), [
          j.literal(key),
          p.node.right as any,
        ])
      );
      j(p).replaceWith(call);
      mutated = true;
    });

  if (mutated) {
    ensureVitestImport(j, root);
    // Ensure afterEach(() => vi.unstubAllEnvs()) exists
    const hasAfterEachCall = root
      .find(j.CallExpression, { callee: { type: 'Identifier', name: 'afterEach' } })
      .some((p) => {
        const cb = p.node.arguments[0];
        if (!cb) return false;
        // naive check for vi.unstubAllEnvs inside callback
        const cbSrc = j(cb).toSource();
        return cbSrc.includes('vi.unstubAllEnvs');
      });
    if (!hasAfterEachCall) {
      // ensure afterEach is imported from vitest
      const vitestImport = root.find(j.ImportDeclaration, { source: { value: 'vitest' } });
      if (vitestImport.size() > 0) {
        const decl = vitestImport.get();
        const hasAfterEach = decl.node.specifiers?.some(
          (s: any) => s.type === 'ImportSpecifier' && s.imported.name === 'afterEach'
        );
        if (!hasAfterEach) {
          decl.node.specifiers = decl.node.specifiers || [];
          decl.node.specifiers.push(j.importSpecifier(j.identifier('afterEach')));
        }
      } else {
        root.get().node.program.body.unshift(
          j.importDeclaration([j.importSpecifier(j.identifier('afterEach'))], j.literal('vitest'))
        );
      }
      const afterEachStmt = j.expressionStatement(
        j.callExpression(j.identifier('afterEach'), [
          j.arrowFunctionExpression([], j.blockStatement([
            j.expressionStatement(
              j.callExpression(j.memberExpression(j.identifier('vi'), j.identifier('unstubAllEnvs')), [])
            ),
          ])),
        ])
      );
      root.get().node.program.body.push(afterEachStmt);
    }
  }

  return mutated ? root.toSource() : file.source;
}
