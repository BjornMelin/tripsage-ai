/**
 * ai-route-v6-upgrade (CommonJS)
 * Ensures Next.js routes using Vercel AI SDK return UI Message Stream responses
 * and wraps messages with convertToModelMessages when needed.
 */
module.exports = function transformer(file, api) {
  const j = api.jscodeshift.withParser('ts');
  const root = j(file.source);

  const isRoute = /\/app\/.+\/route\.(ts|tsx)$/.test(file.path);
  if (!isRoute) return root.toSource();

  function ensureImport(source, imported) {
    const decls = root.find(j.ImportDeclaration, { source: { value: source } });
    if (decls.size() === 0) {
      root.get().node.program.body.unshift(
        j.importDeclaration([j.importSpecifier(j.identifier(imported))], j.literal(source))
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

  // Remove StreamingTextResponse imports
  root
    .find(j.ImportDeclaration, { source: { value: 'ai' } })
    .forEach((p) => {
      p.node.specifiers = (p.node.specifiers || []).filter((s) => {
        return !(
          s.type === 'ImportSpecifier' &&
          s.imported && s.imported.name === 'StreamingTextResponse'
        );
      });
    });

  // Replace new StreamingTextResponse(arg) returns → arg.toUIMessageStreamResponse()
  root
    .find(j.NewExpression, { callee: { type: 'Identifier', name: 'StreamingTextResponse' } })
    .forEach((p) => {
      const arg = p.node.arguments && p.node.arguments[0];
      if (!arg) return;
      const ret = j.returnStatement(
        j.callExpression(j.memberExpression(arg, j.identifier('toUIMessageStreamResponse')), [])
      );
      j(p.parent).replaceWith(ret);
    });

  // Replace `return result` only when `result` is from streamText(...)
  const streamTextResultDeclExists = root.find(j.VariableDeclarator).filter((vd) => {
    const id = vd.node.id;
    if (id.type !== 'Identifier' || id.name !== 'result') return false;
    const init = vd.node.init;
    if (!init) return false;
    if (init.type === 'CallExpression' && init.callee.type === 'Identifier' && init.callee.name === 'streamText') {
      return true;
    }
    if (
      init.type === 'AwaitExpression' &&
      init.argument &&
      init.argument.type === 'CallExpression' &&
      init.argument.callee.type === 'Identifier' &&
      init.argument.callee.name === 'streamText'
    ) {
      return true;
    }
    return false;
  }).size() > 0;

  if (streamTextResultDeclExists) {
    root
      .find(j.ReturnStatement, { argument: { type: 'Identifier', name: 'result' } })
      .forEach((p) => {
        p.replace(
          j.returnStatement(
            j.callExpression(
              j.memberExpression(j.identifier('result'), j.identifier('toUIMessageStreamResponse')),
              []
            )
          )
        );
      });
  }

  // Wrap messages with convertToModelMessages when messages is a bare identifier
  root
    .find(j.CallExpression, { callee: { type: 'Identifier', name: 'streamText' } })
    .forEach((p) => {
      const arg = p.node.arguments && p.node.arguments[0];
      if (!arg || arg.type !== 'ObjectExpression') return;
      const messagesProp = arg.properties.find(
        (prop) => prop.type === 'Property' && prop.key && prop.key.name === 'messages'
      );
      if (!messagesProp) return;
      if (messagesProp.value && messagesProp.value.type === 'Identifier') {
        messagesProp.value = j.callExpression(j.identifier('convertToModelMessages'), [
          messagesProp.value,
        ]);
        ensureImport('ai', 'convertToModelMessages');
      }
    });

  return root.toSource();
};
