/** @vitest-environment node */

import { globSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";
import { createAiTelemetry } from "./telemetry";

const AI_OPERATION_EXPORTS = new Set([
  "embed",
  "embedMany",
  "generateObject",
  "generateText",
  "rerank",
  "streamObject",
  "streamText",
]);

function isProductionSource(filePath: string): boolean {
  return (
    !filePath.includes("/__tests__/") &&
    !filePath.startsWith("src/test/") &&
    !/\.(?:spec|test)\.[cm]?[jt]sx?$/.test(filePath)
  );
}

interface AiImports {
  operationAliases: Set<string>;
  toolLoopAgentAliases: Set<string>;
}

function getAiImports(sourceFile: ts.SourceFile): AiImports {
  const operationAliases = new Set<string>();
  const toolLoopAgentAliases = new Set<string>();

  for (const statement of sourceFile.statements) {
    if (
      !ts.isImportDeclaration(statement) ||
      !ts.isStringLiteral(statement.moduleSpecifier) ||
      statement.moduleSpecifier.text !== "ai"
    ) {
      continue;
    }

    const bindings = statement.importClause?.namedBindings;
    if (!bindings || !ts.isNamedImports(bindings)) continue;

    for (const specifier of bindings.elements) {
      const exportName = specifier.propertyName?.text ?? specifier.name.text;
      if (AI_OPERATION_EXPORTS.has(exportName)) {
        operationAliases.add(specifier.name.text);
      }
      if (exportName === "ToolLoopAgent") {
        toolLoopAgentAliases.add(specifier.name.text);
      }
    }
  }

  return { operationAliases, toolLoopAgentAliases };
}

function propertyNameText(name: ts.PropertyName): string | undefined {
  return ts.isIdentifier(name) || ts.isStringLiteral(name) ? name.text : undefined;
}

function unwrapExpression(expression: ts.Expression): ts.Expression {
  let current = expression;
  while (
    ts.isAsExpression(current) ||
    ts.isNonNullExpression(current) ||
    ts.isParenthesizedExpression(current) ||
    ts.isSatisfiesExpression(current) ||
    ts.isTypeAssertionExpression(current)
  ) {
    current = current.expression;
  }
  return current;
}

function resolveOptionsObject(
  expression: ts.Expression | undefined,
  initializers: Map<string, ts.Expression>
): ts.ObjectLiteralExpression | undefined {
  let current = expression ? unwrapExpression(expression) : undefined;
  const visited = new Set<string>();

  while (current && ts.isIdentifier(current) && !visited.has(current.text)) {
    visited.add(current.text);
    const initializer = initializers.get(current.text);
    current = initializer ? unwrapExpression(initializer) : undefined;
  }

  return current && ts.isObjectLiteralExpression(current) ? current : undefined;
}

function usesPrivacySafeTelemetry(
  options: ts.ObjectLiteralExpression | undefined
): boolean {
  const telemetry = options?.properties.find(
    (property): property is ts.PropertyAssignment =>
      ts.isPropertyAssignment(property) &&
      propertyNameText(property.name) === "telemetry"
  );

  return Boolean(
    telemetry &&
      ts.isCallExpression(telemetry.initializer) &&
      ts.isIdentifier(telemetry.initializer.expression) &&
      telemetry.initializer.expression.text === "createAiTelemetry"
  );
}

function findUnsafeAiOperations(filePath: string): string[] {
  const absolutePath = resolve(process.cwd(), filePath);
  const sourceFile = ts.createSourceFile(
    filePath,
    readFileSync(absolutePath, "utf8"),
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  const { operationAliases, toolLoopAgentAliases } = getAiImports(sourceFile);
  if (operationAliases.size === 0 && toolLoopAgentAliases.size === 0) return [];

  const unsafeCalls: string[] = [];
  const initializers = new Map<string, ts.Expression>();
  const collectInitializers = (node: ts.Node): void => {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer
    ) {
      initializers.set(node.name.text, node.initializer);
    }
    ts.forEachChild(node, collectInitializers);
  };
  collectInitializers(sourceFile);

  const visit = (node: ts.Node): void => {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      operationAliases.has(node.expression.text)
    ) {
      if (
        !usesPrivacySafeTelemetry(resolveOptionsObject(node.arguments[0], initializers))
      ) {
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
        unsafeCalls.push(`${filePath}:${line + 1} ${node.expression.text}()`);
      }
    }

    if (
      ts.isNewExpression(node) &&
      ts.isIdentifier(node.expression) &&
      toolLoopAgentAliases.has(node.expression.text) &&
      !usesPrivacySafeTelemetry(resolveOptionsObject(node.arguments?.[0], initializers))
    ) {
      const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
      unsafeCalls.push(`${filePath}:${line + 1} new ${node.expression.text}()`);
    }

    ts.forEachChild(node, visit);
  };
  visit(sourceFile);

  return unsafeCalls;
}

describe("AI SDK telemetry privacy", () => {
  it("disables model input and output recording", () => {
    expect(createAiTelemetry({ functionId: "test.operation" })).toEqual({
      functionId: "test.operation",
      recordInputs: false,
      recordOutputs: false,
    });
  });

  it("routes every production AI operation through the privacy-safe helper", () => {
    const sourceFiles = globSync(["src/**/*.ts", "src/**/*.tsx"], {
      cwd: process.cwd(),
    }).filter(isProductionSource);
    const unsafeCalls = sourceFiles.flatMap(findUnsafeAiOperations);

    expect(unsafeCalls).toEqual([]);
  });
});
