# GPT-4.1 Prompting Essentials

*A condensed guide to the key best practices for prompting GPT-4.1 models*

## Core Insights

- **GPT-4.1 follows instructions more literally** than its predecessors
- The model is highly steerable - a single clear sentence can correct unexpected behavior
- Explicit instructions often outperform implicit rules

## 1. Agentic Workflows

### Three Critical Reminders (20% performance boost)

1. **Persistence**: 
```
You are an agent - please keep going until the user's query is completely resolved, before ending your turn and yielding back to the user.
```

2. **Tool-calling**:
```
If you are not sure about file content or codebase structure, use your tools to read files and gather relevant information: do NOT guess or make up an answer.
```

3. **Planning (optional, +4% success)**:
```
You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls.
```

### Tool Best Practices
- Use the API tools field exclusively (2% better performance)
- Name tools clearly with detailed descriptions
- Place examples in system prompt's `# Examples` section

## 2. Long Context (up to 1M tokens)

### Key Strategies
- Place instructions at **both** beginning and end of long context for best performance
- If using instructions once, place them above the context
- Use appropriate delimiters for documents:
  - XML: `<doc id='1' title='The Fox'>Content here</doc>` (recommended)
  - Lee et al. format: `ID: 1 | TITLE: The Fox | CONTENT: Content here`
  - Avoid JSON for document lists

### Context Reliance Options
```
// For strict context-only answers:
- Only use the documents in the provided External Context to answer the User Query.

// For mixed knowledge:
- By default, use the provided external context, but if other basic knowledge is needed, you can use some of your own knowledge.
```

## 3. Chain of Thought

While GPT-4.1 isn't a reasoning model, you can induce step-by-step thinking:

Basic prompt:
```
First, think carefully step by step about what documents are needed to answer the query. Then, print out the TITLE and ID of each document. Then, format the IDs into a list.
```

For complex analysis:
```
# Reasoning Strategy
1. Query Analysis: Break down and analyze the query
2. Context Analysis: Carefully select relevant documents
3. Synthesis: Summarize which documents are most relevant and why
```

## 4. Instruction Following

### Development Workflow
1. Start with `# Instructions` section with high-level bullet points
2. Add specific sections for detailed behaviors (`# Sample Phrases`)
3. Create ordered lists for specific workflow steps
4. Debug by:
   - Checking for conflicts (later instructions override earlier ones)
   - Adding examples that demonstrate desired behavior
   - Avoiding all-caps or incentives unless necessary

### Common Fixes
- For tool-calling issues: Add "if you don't have enough information, ask the user"
- For repetitive responses: Instruct to "vary sample phrases as necessary"
- For verbose outputs: Provide specific formatting instructions

## 5. Optimal Prompt Structure

```
# Role and Objective

# Instructions
## Sub-categories for detailed instructions

# Reasoning Steps

# Output Format

# Examples
## Example 1

# Context

# Final instructions and prompt to think step by step
```

## 6. Delimiter Guidelines

1. **Markdown** (recommended): Use for sections, code blocks, lists
2. **XML**: Good for nesting and metadata
3. **JSON**: Only for coding contexts (more verbose)

## Quick Tips

- **Be explicit**: GPT-4.1 won't infer implicit rules as strongly
- **Order matters**: Later instructions override earlier ones if conflicting
- **Test thoroughly**: The model is nondeterministic, so iterate often
- **Simple fixes work**: One clear sentence often corrects unwanted behavior

## Caveats

- May resist very long, repetitive outputs - break down tasks if needed
- Rare issues with parallel tool calls - set `parallel_tool_calls` to false if problems occur