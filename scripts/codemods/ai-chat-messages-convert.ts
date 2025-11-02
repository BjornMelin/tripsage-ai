/*
 * Codemod: ai-chat-messages-convert
 *
 * Goal
 * - Wrap UIMessage[] passed to `streamText({ messages })` with
 *   `convertToModelMessages(messages)` and ensure import.
 *
 * Scope
 * - Any .ts/.tsx files importing from 'ai'.
 *
 * Idempotent: yes.
 */
import type { API, FileInfo, JSCodeshift } from 'jscodeshift';

const withTs = (j: JSCodeshift) => j.withParser('ts');

function ensureImport(j: JSCodeshift, root: any) {
  const aiImport = root.find(j.ImportDeclaration, { source: { value: 'ai' } });
  if (aiImport.size() === 0) {
    root.get().node.program.body.unshift(
      j.importDeclaration([j.importSpecifier(j.identifier('convertToModelMessages'))], j.literal('ai'))
    );
    return;
  }
  const decl = aiImport.get();
  const has = decl.node.specifiers?.some(
    (s: any) => s.type === 'ImportSpecifier' && s.imported.name === 'convertToModelMessages'
  );
  if (!has) {
    decl.node.specifiers = decl.node.specifiers || [];
    decl.node.specifiers.push(j.importSpecifier(j.identifier('convertToModelMessages')));
  }
}

export default function transformer(file: FileInfo, api: API) {
  const j = withTs(api.jscodeshift);
  const root = j(file.source);

  let mutated = false;

  root
    .find(j.CallExpression, { callee: { type: 'Identifier', name: 'streamText' } })
    .forEach((p) => {
      const arg = p.node.arguments[0];
      if (!arg || arg.type !== 'ObjectExpression') return;
      const messagesProp = arg.properties.find(
        (prop: any) => prop.type === 'Property' && (prop.key as any).name === 'messages'
      ) as any;
      if (!messagesProp) return;
      if (messagesProp.value.type === 'Identifier') {
        messagesProp.value = j.callExpression(j.identifier('convertToModelMessages'), [
          messagesProp.value,
        ]);
        ensureImport(j, root);
        mutated = true;
      }
    });

  return mutated ? root.toSource() : file.source;
}

