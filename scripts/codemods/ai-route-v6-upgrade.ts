/*
 * Codemod: ai-route-v6-upgrade
 *
 * Goal
 * - Ensure Next.js route handlers that use the Vercel AI SDK return
 *   UI Message Stream responses via `result.toUIMessageStreamResponse()`.
 * - Remove legacy `StreamingTextResponse` patterns and enforce `streamText` usage.
 * - Ensure `convertToModelMessages(messages)` is used when passing UIMessage[].
 *
 * Scope
 * - Targets files named `route.ts` or `route.tsx` under Next.js app routes.
 * - Matches imports from `ai` and `@ai-sdk/*` packages.
 *
 * Idempotent: yes.
 */
import type { API, FileInfo, JSCodeshift } from 'jscodeshift';

const withTs = (j: JSCodeshift) => j.withParser('ts');

function ensureImport(j: JSCodeshift, root: any, source: string, imported: string) {
  const existing = root.find(j.ImportDeclaration, { source: { value: source } });
  if (existing.size() === 0) {
    root.get().node.program.body.unshift(
      j.importDeclaration([j.importSpecifier(j.identifier(imported))], j.literal(source))
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

  const isRoute = /\/app\/.+\/route\.(ts|tsx)$/.test(file.path);
  if (!isRoute) return root.toSource();

  // Remove StreamingTextResponse imports and usages; enforce toUIMessageStreamResponse
  root
    .find(j.ImportDeclaration, { source: { value: 'ai' } })
    .forEach((path) => {
      // Drop StreamingTextResponse if present
      path.node.specifiers = (path.node.specifiers || []).filter((s: any) => {
        return !(
          s.type === 'ImportSpecifier' &&
          (s.imported as any).name === 'StreamingTextResponse'
        );
      });
    });

  // Replace `return new StreamingTextResponse(result.toAIStream());` → `return result.toUIMessageStreamResponse();`
  root
    .find(j.NewExpression, {
      callee: { type: 'Identifier', name: 'StreamingTextResponse' },
    })
    .forEach((p) => {
      const parentStmt = p.parent;
      const arg = p.node.arguments?.[0];
      if (!arg) return;
      // Replace full return statement
      const ret = j.returnStatement(
        j.callExpression(j.memberExpression(arg as any, j.identifier('toUIMessageStreamResponse')), [])
      );
      j(parentStmt).replaceWith(ret);
    });

  // Ensure return of result.toUIMessageStreamResponse() when returning `result` directly
  root
    .find(j.ReturnStatement, {
      argument: { type: 'Identifier', name: 'result' },
    })
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

  // If messages are passed directly without convertToModelMessages, add it.
  root
    .find(j.CallExpression, { callee: { type: 'Identifier', name: 'streamText' } })
    .forEach((p) => {
      const arg = p.node.arguments[0];
      if (!arg || arg.type !== 'ObjectExpression') return;
      const messagesProp = arg.properties.find(
        (prop: any) => prop.type === 'Property' && (prop.key as any).name === 'messages'
      ) as any;
      if (!messagesProp) return;
      // only wrap if not already a convertToModelMessages call
      if (messagesProp.value.type === 'Identifier') {
        messagesProp.value = j.callExpression(j.identifier('convertToModelMessages'), [
          messagesProp.value,
        ]);
        ensureImport(j, root, 'ai', 'convertToModelMessages');
      }
    });

  return root.toSource();
}

