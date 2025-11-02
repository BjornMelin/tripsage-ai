/**
 * ai-chat-messages-convert (CommonJS)
 * Wraps streamText({ messages }) with convertToModelMessages(messages) and ensures import.
 */
module.exports = function transformer(file, api) {
  const j = api.jscodeshift.withParser('ts');
  const root = j(file.source);
  let mutated = false;

  function ensureImport() {
    const decls = root.find(j.ImportDeclaration, { source: { value: 'ai' } });
    if (decls.size() === 0) {
      root.get().node.program.body.unshift(
        j.importDeclaration([j.importSpecifier(j.identifier('convertToModelMessages'))], j.literal('ai'))
      );
      return;
    }
    const decl = decls.get();
    const has = (decl.node.specifiers || []).some(
      (s) => s.type === 'ImportSpecifier' && s.imported.name === 'convertToModelMessages'
    );
    if (!has) {
      decl.node.specifiers = decl.node.specifiers || [];
      decl.node.specifiers.push(j.importSpecifier(j.identifier('convertToModelMessages')));
    }
  }

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
        ensureImport();
        mutated = true;
      }
    });

  return mutated ? root.toSource() : file.source;
};

