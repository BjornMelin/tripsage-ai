/**
 * vitest-mock-unify (CommonJS)
 * Convert vi.mocked(require('module').Identifier) → import { Identifier } from 'module'; vi.mocked(Identifier)
 */
module.exports = function transformer(file, api) {
  const j = api.jscodeshift.withParser('ts');
  const root = j(file.source);
  if (!/\.test\.(ts|tsx)$/.test(file.path)) return root.toSource();
  let mutated = false;

  function ensureNamedImport(moduleName, imported) {
    const decls = root.find(j.ImportDeclaration, { source: { value: moduleName } });
    if (decls.size() === 0) {
      root.get().node.program.body.unshift(
        j.importDeclaration([j.importSpecifier(j.identifier(imported))], j.literal(moduleName))
      );
      return;
    }
    const decl = decls.get();
    const has = (decl.node.specifiers || []).some(
      (s) => s.type === 'ImportSpecifier' && s.imported.name === imported
    );
    if (!has) {
      decl.node.specifiers = decl.node.specifiers || [];
      decl.node.specifiers.push(j.importSpecifier(j.identifier(imported)));
    }
  }

  // Find vi.mocked(require('module').Identifier)
  root
    .find(j.CallExpression, { callee: { type: 'MemberExpression', property: { name: 'mocked' } } })
    .forEach((p) => {
      const arg = p.node.arguments && p.node.arguments[0];
      if (!arg || arg.type !== 'MemberExpression') return;
      const obj = arg.object;
      const prop = arg.property;
      if (
        obj && obj.type === 'CallExpression' &&
        obj.callee.type === 'Identifier' && obj.callee.name === 'require' &&
        obj.arguments.length === 1 && obj.arguments[0].type === 'Literal' &&
        prop && prop.type === 'Identifier'
      ) {
        const moduleName = obj.arguments[0].value;
        const imported = prop.name;
        ensureNamedImport(moduleName, imported);
        j(p).replaceWith(
          j.callExpression(j.memberExpression(j.identifier('vi'), j.identifier('mocked')), [
            j.identifier(imported),
          ])
        );
        mutated = true;
      }
    });

  return mutated ? root.toSource() : file.source;
};

