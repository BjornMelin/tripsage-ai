#!/usr/bin/env node

/**
 * @fileoverview Boundary violation detection script for Next.js App Router.
 *
 * Scans TypeScript/TSX files for server/client boundary violations:
 * - Direct server-only imports in client components
 * - Indirect imports through dependency chains
 *
 * Usage: node scripts/check-boundaries.js
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { existsSync } from "fs";
import { join, relative } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = join(__filename, "..");

const FRONTEND_DIR = join(__dirname, "..", "frontend", "src");
const SERVER_ONLY_MARKER = 'import "server-only"';
const CLIENT_MARKER = '"use client"';
// Fallback list for modules that cannot carry the server-only marker
// (e.g., third-party packages). Prefer detecting via SERVER_ONLY_MARKER.
const SERVER_ONLY_IMPORTS = [
  "server-only",
];

/**
 * Recursively finds all TypeScript/TSX files in a directory.
 */
function findTsFiles(dir, fileList = []) {
  const files = readdirSync(dir);

  for (const file of files) {
    const filePath = join(dir, file);
    const stat = statSync(filePath);

    if (stat.isDirectory()) {
      // Skip node_modules and other build artifacts
      if (
        !file.startsWith(".") &&
        file !== "node_modules" &&
        file !== ".next" &&
        file !== "dist"
      ) {
        findTsFiles(filePath, fileList);
      }
    } else if (file.endsWith(".ts") || file.endsWith(".tsx")) {
      fileList.push(filePath);
    }
  }

  return fileList;
}

/**
 * Checks if a file is a client component.
 */
function isClientComponent(content) {
  return content.includes(CLIENT_MARKER);
}

/**
 * Checks if a file is a server-only module.
 */
function isServerOnlyModule(content) {
  return content.includes(SERVER_ONLY_MARKER);
}

/**
 * Extracts import statements from file content.
 */
function extractImports(content) {
  const imports = [];
  const importRegex =
    /import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?["']([^"']+)["']/g;

  let match;
  while ((match = importRegex.exec(content)) !== null) {
    imports.push(match[1]);
  }

  return imports;
}

/**
 * Resolves an import path to actual file paths, trying common extensions.
 */
function resolveImportPath(importPath, fromFile) {
  // Handle @/ alias
  if (importPath.startsWith("@/")) {
    const pathWithoutAlias = importPath.replace("@/", "");
    const basePath = join(FRONTEND_DIR, pathWithoutAlias);
    // Try common extensions
    for (const ext of [".ts", ".tsx", ".js", ".jsx", ""]) {
      const candidate = basePath + ext;
      if (existsSync(candidate)) {
        return candidate;
      }
      // Also try index files
      const indexCandidate = join(basePath, `index${ext}`);
      if (existsSync(indexCandidate)) {
        return indexCandidate;
      }
    }
    return basePath; // Return base path even if not found (for graph building)
  }

  // Handle relative imports
  if (importPath.startsWith("./") || importPath.startsWith("../")) {
    const fromDir = join(fromFile, "..");
    const resolved = join(fromDir, importPath);
    // Try common extensions
    for (const ext of [".ts", ".tsx", ".js", ".jsx", ""]) {
      const candidate = resolved + ext;
      if (existsSync(candidate)) {
        return candidate;
      }
      // Also try index files
      const indexCandidate = join(resolved, `index${ext}`);
      if (existsSync(indexCandidate)) {
        return indexCandidate;
      }
    }
    return resolved; // Return resolved path even if not found
  }

  // External/third-party imports - return null
  return null;
}

/**
 * Checks if an import path is server-only based on hardcoded list.
 * Note: Prefer checking the actual file content via isServerOnlyModule.
 */
function isServerOnlyImport(importPath) {
  return SERVER_ONLY_IMPORTS.some((pattern) => importPath.includes(pattern));
}

/**
 * Builds a dependency graph of imports.
 */
function buildDependencyGraph(files) {
  const graph = new Map();

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    const imports = extractImports(content);
    const relativePath = relative(FRONTEND_DIR, file);

    // Resolve imports to actual file paths
    const resolvedImports = imports
      .map((imp) => resolveImportPath(imp, file))
      .filter(Boolean);

    graph.set(relativePath, {
      isClient: isClientComponent(content),
      isServerOnly: isServerOnlyModule(content),
      imports: resolvedImports,
      rawImports: imports,
      absolutePath: file,
    });
  }

  return graph;
}

/**
 * Checks for indirect server-only imports through dependency chains.
 */
function checkIndirectImports(filePath, graph, visited = new Set(), chain = []) {
  if (visited.has(filePath)) {
    return [];
  }
  visited.add(filePath);

  const node = graph.get(filePath);
  if (!node) {
    return [];
  }

  const violations = [];
  const currentChain = [...chain, filePath];

  // Check direct imports
  for (const imp of node.rawImports) {
    if (isServerOnlyImport(imp)) {
      violations.push({
        file: filePath,
        type: "direct",
        import: imp,
        chain: currentChain,
      });
    }
  }

  // Check indirect imports
  // Only flag if we're in a client component (node.isClient is true for the starting node)
  for (let i = 0; i < node.imports.length; i++) {
    const resolvedImport = node.imports[i];
    const rawImport = node.rawImports[i];
    
    // Try to find the file in the graph
    let relativeImportPath = null;
    for (const [graphPath, graphNode] of graph.entries()) {
      if (graphNode.absolutePath === resolvedImport) {
        relativeImportPath = graphPath;
        break;
      }
    }

    if (relativeImportPath && graph.has(relativeImportPath)) {
      const importNode = graph.get(relativeImportPath);
      // Determine the starting node (first in chain, or current node if chain is empty)
      const startingNode = chain.length > 0 ? graph.get(chain[0]) : node;
      
      // Only flag if the imported module is server-only AND we're checking from a client component
      // Server components can safely import server-only modules
      if (importNode.isServerOnly && startingNode && startingNode.isClient) {
        violations.push({
          file: filePath,
          type: chain.length === 0 ? "direct" : "indirect",
          import: rawImport,
          target: relativeImportPath,
          chain: [...currentChain, relativeImportPath],
        });
      }
      // Recursively check dependencies only if we're still in a client component chain
      if (startingNode && startingNode.isClient) {
        violations.push(...checkIndirectImports(relativeImportPath, graph, visited, currentChain));
      }
    }
  }

  return violations;
}

/**
 * Main function to detect boundary violations.
 */
function detectBoundaryViolations() {
  console.log("🔍 Scanning for server/client boundary violations...\n");

  const files = findTsFiles(FRONTEND_DIR);
  const graph = buildDependencyGraph(files);
  const violations = [];

  // Check all client components only
  // Note: Server components can safely import server-only modules,
  // even if they're used as children of client components.
  for (const [filePath, node] of graph.entries()) {
    if (node.isClient) {
      const fileViolations = checkIndirectImports(filePath, graph);
      violations.push(...fileViolations);
    }
  }

  if (violations.length === 0) {
    console.log("✅ No boundary violations found!\n");
    return 0;
  }

  console.error(`❌ Found ${violations.length} boundary violation(s):\n`);

  // Group violations by file
  const violationsByFile = new Map();
  for (const violation of violations) {
    if (!violationsByFile.has(violation.file)) {
      violationsByFile.set(violation.file, []);
    }
    violationsByFile.get(violation.file).push(violation);
  }

  // Print violations
  for (const [file, fileViolations] of violationsByFile.entries()) {
    console.error(`📄 ${file}`);
    for (const violation of fileViolations) {
      if (violation.type === "direct") {
        console.error(`   ⚠️  direct import: ${violation.import}`);
      } else {
        console.error(`   🔗 indirect import: ${violation.import}`);
        console.error(`      → targets server-only module: ${violation.target}`);
        if (violation.chain && violation.chain.length > 2) {
          console.error(`      → import chain: ${violation.chain.join(" → ")}`);
        }
      }
    }
    console.error("");
  }

  return 1;
}

// Run the detection
const exitCode = detectBoundaryViolations();
process.exit(exitCode);

