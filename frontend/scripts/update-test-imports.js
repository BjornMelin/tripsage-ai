#!/usr/bin/env node
/**
 * Script to update test imports from @testing-library/react to @/test/test-utils
 * This ensures all component tests use the renderWithProviders utility
 */

const fs = require("fs").promises;
const path = require("path");

const findTestFiles = async (dir, files = []) => {
  const entries = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (
      entry.isDirectory() &&
      !entry.name.startsWith(".") &&
      entry.name !== "node_modules"
    ) {
      await findTestFiles(fullPath, files);
    } else if (entry.isFile() && entry.name.match(/\.test\.(ts|tsx)$/)) {
      files.push(fullPath);
    }
  }

  return files;
};

const updateImports = async (filePath) => {
  try {
    let content = await fs.readFile(filePath, "utf8");
    let updated = false;

    // Pattern 1: Import render from @testing-library/react
    if (
      content.includes("import { render") &&
      content.includes('from "@testing-library/react"')
    ) {
      const oldImportRegex =
        /import\s*{\s*([^}]+)\s*}\s*from\s*["']@testing-library\/react["']/g;

      content = content.replace(oldImportRegex, (match, imports) => {
        const importList = imports.split(",").map((imp) => imp.trim());
        const _testUtilImports = ["render", "renderWithProviders", "createMockUser"];
        const remainingImports = [];
        const movedImports = [];

        importList.forEach((imp) => {
          if (imp === "render") {
            movedImports.push(imp);
          } else {
            remainingImports.push(imp);
          }
        });

        updated = true;
        let result = "";

        // Add imports from test-utils
        if (movedImports.length > 0) {
          // Check if test-utils import already exists
          if (!content.includes('from "@/test/test-utils"')) {
            const additionalImports = [...movedImports];
            // Add createMockUser if useAuth is used in the file
            if (content.includes("useAuth") && !content.includes("createMockUser")) {
              additionalImports.push("createMockUser");
            }
            result = `import { ${additionalImports.join(", ")} } from "@/test/test-utils";\n`;
          }
        }

        // Keep remaining imports from RTL
        if (remainingImports.length > 0) {
          result += `import { ${remainingImports.join(", ")} } from "@testing-library/react"`;
        }

        return result.trim();
      });
    }

    // Pattern 2: Update existing test-utils imports to include createMockUser if needed
    if (
      content.includes('from "@/test/test-utils"') &&
      content.includes("useAuth") &&
      !content.includes("createMockUser")
    ) {
      const testUtilsRegex =
        /import\s*{\s*([^}]+)\s*}\s*from\s*["']@\/test\/test-utils["']/g;

      content = content.replace(testUtilsRegex, (match, imports) => {
        const importList = imports.split(",").map((imp) => imp.trim());
        if (!importList.includes("createMockUser")) {
          importList.push("createMockUser");
          updated = true;
        }
        return `import { ${importList.join(", ")} } from "@/test/test-utils"`;
      });
    }

    // Pattern 3: Update mock user objects to use createMockUser
    if (content.includes("useAuth") && content.includes("user: {")) {
      // Replace inline user objects with createMockUser calls
      const userObjectRegex =
        /user:\s*{\s*id:\s*["'][^"']+["'],\s*email:\s*["'][^"']+["'][^}]*}/g;

      content = content.replace(userObjectRegex, (match) => {
        // Extract properties from the match
        const idMatch = match.match(/id:\s*["']([^"']+)["']/);
        const emailMatch = match.match(/email:\s*["']([^"']+)["']/);
        const nameMatch = match.match(/name:\s*["']([^"']+)["']/);

        if (idMatch || emailMatch || nameMatch) {
          updated = true;
          const props = [];
          if (idMatch && idMatch[1] !== "test-user-id")
            props.push(`id: "${idMatch[1]}"`);
          if (emailMatch && emailMatch[1] !== "test@example.com")
            props.push(`email: "${emailMatch[1]}"`);
          if (nameMatch && nameMatch[1] !== "Test User")
            props.push(`name: "${nameMatch[1]}"`);

          if (props.length > 0) {
            return `user: createMockUser({ ${props.join(", ")} })`;
          } else {
            return "user: createMockUser()";
          }
        }
        return match;
      });
    }

    if (updated) {
      // Clean up double line breaks
      content = content.replace(/\n\n\n+/g, "\n\n");

      await fs.writeFile(filePath, content, "utf8");
      console.log(`✅ Updated: ${path.relative(process.cwd(), filePath)}`);
      return true;
    }

    return false;
  } catch (error) {
    console.error(`❌ Error processing ${filePath}:`, error.message);
    return false;
  }
};

const main = async () => {
  console.log("🔍 Finding component test files...");

  const srcPath = path.join(process.cwd(), "src");
  const testFiles = await findTestFiles(srcPath);

  console.log(`📋 Found ${testFiles.length} test files`);

  let updatedCount = 0;
  for (const file of testFiles) {
    const updated = await updateImports(file);
    if (updated) updatedCount++;
  }

  console.log(`\n✨ Complete! Updated ${updatedCount} files.`);
};

main().catch(console.error);
