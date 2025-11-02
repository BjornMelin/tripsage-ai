/*
 * Codemod: vitest-mock-unify
 *
 * Goal
 * - Replace ad-hoc `vi.mocked(require('...').symbol)` patterns with direct imports
 *   and `vi.mocked(importedSymbol)` usage.
 *
 * Scope
 * - Test files *.test.ts(x)
 * - Only transforms `vi.mocked(require('module').Identifier)` MemberExpressions.
 *
 * Idempotent: yes (skips if already imported identifier exists).
 */
import type { API, FileInfo, JSCodeshift } from 'jscodeshift';

const withTs = (j: JSCodeshift) => j.withParser('ts');

function ensureNamedImport(j: JSCodeshift, root: any, moduleName: string, imported: string) {
  const existing = root.find(j.ImportDeclaration, { source: { value: moduleName } });
  if (existing.size() === 0) {
    root.get().node.program.body.unshift(
      j.importDeclaration([j.importSpecifier(j.identifier(imported))], j.literal(moduleName))
    );
    return;
  }
  const decl = existing.get();
  const has = decl.node.specifiers?.some(
    (s: any) => s.type === 'ImportSpecifier' && s.imported.name === imported
  );
  if (!has) {
    decl.node.specifiers = decl.node.specifiers || [];
    decl.node.specifiers.push(j.importSpecifier(j.identifier(imported)));
  }
}

export default function transformer(file: FileInfo, api: API) {
  const j = withTs(api.jscodeshift);
  const root = j(file.source);
  if (!/\.test\.(ts|tsx)$/.test(file.path)) return file.source;

  let mutated = false;

  // Find vi.mocked(require('module').Identifier)
  root
    .find(j.CallExpression, { callee: { type: 'MemberExpression', property: { name: 'mocked' } } })
    .forEach((p) => {
      const [arg] = p.node.arguments;
      if (!arg || arg.type !== 'MemberExpression') return;
      const obj = arg.object;
      const prop = arg.property;
      if (
        obj.type === 'CallExpression' &&
        obj.callee.type === 'Identifier' &&
        obj.callee.name === 'require' &&
        obj.arguments.length === 1 &&
        obj.arguments[0].type === 'Literal' &&
        prop.type === 'Identifier'
      ) {
        const moduleName = (obj.arguments[0] as any).value as string;
        const importedName = prop.name;

        // Ensure import { importedName } from 'moduleName'
        ensureNamedImport(j, root, moduleName, importedName);

        // Replace require('module').Imported → Imported
        j(p).replaceWith(
          j.callExpression(j.memberExpression(j.identifier('vi'), j.identifier('mocked')), [
            j.identifier(importedName),
          ])
        );
        mutated = true;
      }
    });

  return mutated ? root.toSource() : file.source;
}

