/**
 * tests-env-stub (CommonJS)
 * Replace process.env.X=Y in tests with vi.stubEnv('X', Y) and add afterEach cleanup.
 */
module.exports = function transformer(file, api) {
  const j = api.jscodeshift.withParser('ts');
  const root = j(file.source);
  if (!/\.test\.(ts|tsx)$/.test(file.path)) return root.toSource();

  let mutated = false;

  function ensureViImport() {
    const hasVi = root
      .find(j.ImportDeclaration, { source: { value: 'vitest' } })
      .some((p) => (p.node.specifiers || []).some((s) => s.type === 'ImportSpecifier' && s.imported.name === 'vi'));
    if (!hasVi) {
      root.get().node.program.body.unshift(
        j.importDeclaration([j.importSpecifier(j.identifier('vi'))], j.literal('vitest'))
      );
    }
  }

  // Replace assignments to process.env.KEY
  root
    .find(j.AssignmentExpression, {
      operator: '=',
      left: {
        type: 'MemberExpression',
        object: {
          type: 'MemberExpression',
          object: { type: 'Identifier', name: 'process' },
          property: { name: 'env' },
        },
      },
    })
    .forEach((p) => {
      const left = p.node.left;
      const key = left.property && (left.property.name || left.property.value);
      if (!key) return;
      const call = j.expressionStatement(
        j.callExpression(j.memberExpression(j.identifier('vi'), j.identifier('stubEnv')), [
          j.literal(key),
          p.node.right,
        ])
      );
      j(p).replaceWith(call);
      mutated = true;
    });

  if (mutated) {
    ensureViImport();
    // Ensure afterEach cleanup exists
    const hasAfterEachCall = root
      .find(j.CallExpression, { callee: { type: 'Identifier', name: 'afterEach' } })
      .some((p) => j(p.node).toSource().includes('vi.unstubAllEnvs'));

    if (!hasAfterEachCall) {
      // import { afterEach } if missing
      const vitestImport = root.find(j.ImportDeclaration, { source: { value: 'vitest' } });
      if (vitestImport.size() > 0) {
        const decl = vitestImport.get();
        const hasAfterEach = (decl.node.specifiers || []).some(
          (s) => s.type === 'ImportSpecifier' && s.imported.name === 'afterEach'
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

  return root.toSource();
};

