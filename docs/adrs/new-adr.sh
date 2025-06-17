#!/bin/bash
# Script to create a new ADR from template

# Check if title was provided
if [ -z "$1" ]; then
    echo "Usage: ./new-adr.sh \"Title of the Decision\""
    echo "Example: ./new-adr.sh \"Use GraphQL for API\""
    exit 1
fi

# Get the title and create a slug
TITLE="$1"
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

# Find the next ADR number
LAST_ADR=$(ls adr-*.md 2>/dev/null | grep -E 'adr-[0-9]{4}' | sort -V | tail -1)
if [ -z "$LAST_ADR" ]; then
    NEXT_NUM="0001"
else
    LAST_NUM=$(echo "$LAST_ADR" | grep -oE '[0-9]{4}' | head -1)
    NEXT_NUM=$(printf "%04d" $((10#$LAST_NUM + 1)))
fi

# Create the new ADR filename
NEW_FILE="adr-${NEXT_NUM}-${SLUG}.md"
DATE=$(date +%Y-%m-%d)

# Copy template and update placeholders
cp template.md "$NEW_FILE"

# Update the file with the title and date
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/ADR-XXXX: \[short title of solved problem and solution\]/ADR-${NEXT_NUM}: ${TITLE}/" "$NEW_FILE"
    sed -i '' "s/YYYY-MM-DD/${DATE}/" "$NEW_FILE"
    sed -i '' "s/\[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX\]/Proposed/" "$NEW_FILE"
else
    # Linux
    sed -i "s/ADR-XXXX: \[short title of solved problem and solution\]/ADR-${NEXT_NUM}: ${TITLE}/" "$NEW_FILE"
    sed -i "s/YYYY-MM-DD/${DATE}/" "$NEW_FILE"
    sed -i "s/\[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX\]/Proposed/" "$NEW_FILE"
fi

echo "Created new ADR: $NEW_FILE"
echo ""
echo "Next steps:"
echo "1. Edit $NEW_FILE to fill in the details"
echo "2. Update README.md with the new ADR entry"
echo "3. Submit for review via pull request"