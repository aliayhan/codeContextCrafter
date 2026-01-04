---
name: CICD/Automated Review Architecture with MCP Integration
about: Build AI-powered code review system for CI/CD pipelines
title: '[FEATURE] CICD Code Review with MCP Server'
labels: enhancement, mcp, cicd, high-impact
assignees: ''
---

## Problem Statement

CodeContextCrafter can extract focused code context, but lacks integration with CI/CD workflows for automated code review. Current limitations:

**What's Missing:**
- No git/PR integration - can't automatically review changed files
- No structured output for AI reviewers - just markdown text
- No mechanism to post AI comments back to PRs
- No line number mapping for dependencies - AI can't reference specific lines
- No MCP server - external systems can't integrate programmatically

**The Opportunity:**

AI code review is valuable but expensive/slow if done manually:
1. Developer opens PR
2. Copy changed files to Claude/ChatGPT
3. Manually provide context (dependencies, project structure)
4. Copy-paste AI feedback back to PR
5. Repeat for each iteration

**Goal:** Automate this entire workflow in CI/CD.

## Proposed Solution

Build a complete **AI Code Review System** with:
1. GitHub Action that triggers on PRs
2. MCP Server for programmatic access
3. Structured review format (JSON) for AI output
4. Automated PR comment posting

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub PR Opened                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              GitHub Action: AI Code Review                      │
│  1. Get changed files (git diff)                                │
│  2. Generate context (ccc --changed-files)                      │
│  3. Call MCP Server with context + diff                         │
│  4. Parse structured JSON review output                         │
│  5. Post comments to PR via GitHub API                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server (ccc-review)                      │
│  Tools:                                                         │
│  - get_code_context(changed_files, diff, depth)                │
│  - submit_review(comments[])                                    │
│  - get_file_content(path, with_line_numbers=true)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI Review (Claude/GPT)                        │
│  Input: Code context + diff + review instructions               │
│  Output: Structured JSON with comments                          │
│  {                                                              │
│    "comments": [                                                │
│      {                                                          │
│        "file": "main.py",                                       │
│        "line": 42,                                              │
│        "severity": "error",                                     │
│        "message": "Null pointer risk",                          │
│        "suggestion": "if user:\n    user.save()"               │
│      }                                                          │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Design

### Component 1: GitHub Action Workflow

```yaml
# .github/workflows/ai-code-review.yml

name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]
  issue_comment:
    types: [created]  # Trigger via "/review" comment

permissions:
  pull-requests: write
  contents: read

jobs:
  ai-review:
    # Only run if: auto-trigger on PR OR manual "/review" comment
    if: |
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '/review'))

    runs-on: ubuntu-latest

    steps:
      - name: Checkout PR branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0  # Full history for diff

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install CodeContextCrafter
        run: |
          pip install codecontextcrafter

      - name: Get changed files
        id: changed-files
        run: |
          # Get list of changed files in this PR
          git diff --name-only origin/${{ github.base_ref }}...HEAD > changed_files.txt
          echo "Changed files:"
          cat changed_files.txt

          # Get full diff with context
          git diff origin/${{ github.base_ref }}...HEAD > changes.diff
          echo "file_count=$(wc -l < changed_files.txt)" >> $GITHUB_OUTPUT

      - name: Generate code context
        id: context
        run: |
          # Generate context for changed files with dependencies
          cat changed_files.txt | xargs ccc \
            --dep-depth-max 2 \
            --format json-review \
            --diff changes.diff \
            -o context.json

          echo "Context generated: $(wc -l < context.json) lines"

      - name: Run AI review via API
        id: ai-review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Call Claude API with review prompt
          python .github/scripts/run_ai_review.py \
            --context context.json \
            --diff changes.diff \
            --output review.json

      - name: Post review comments
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const review = JSON.parse(fs.readFileSync('review.json', 'utf8'));

            // Group comments by file
            const commentsByFile = {};
            for (const comment of review.comments) {
              if (!commentsByFile[comment.file]) {
                commentsByFile[comment.file] = [];
              }
              commentsByFile[comment.file].push(comment);
            }

            // Post review with comments
            await github.rest.pulls.createReview({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
              event: 'COMMENT',
              body: `🤖 **AI Code Review**\n\nReviewed ${review.comments.length} potential issues.`,
              comments: review.comments.map(c => ({
                path: c.file,
                line: c.line,
                body: `**${c.severity.toUpperCase()}**: ${c.message}\n\n${c.suggestion ? '```suggestion\n' + c.suggestion + '\n```' : ''}`
              }))
            });

      - name: Update review status
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            // Post summary comment
            const status = '${{ job.status }}';
            const emoji = status === 'success' ? '✅' : '❌';

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `${emoji} AI code review ${status}`
            });
```

### Component 2: Review-Specific CLI Mode

```python
# codecontextcrafter/code_context_crafter.py

def _create_argument_parser():
    # ... existing args ...

    parser.add_argument(
        '--format',
        choices=['markdown', 'json-review'],
        default='markdown',
        help='Output format (markdown for humans, json-review for CI/CD)'
    )

    parser.add_argument(
        '--diff',
        type=str,
        help='Path to git diff file (for review mode)'
    )

    parser.add_argument(
        '--changed-files-only',
        action='store_true',
        help='Only include changed files as primary (others as deps)'
    )

def _format_review_output(
    primary_files: List[str],
    signatures: str,
    diff_file: Optional[str]
) -> str:
    """
    Format output for AI code review.

    Output structure:
    {
      "changed_files": [
        {
          "path": "main.py",
          "content": "full content with line numbers",
          "diff": "+/- hunks for this file"
        }
      ],
      "dependencies": [
        {
          "path": "utils.py",
          "signatures": [
            {
              "name": "validate_input",
              "line": 42,
              "signature": "def validate_input(value: str) -> bool:",
              "docstring": "Validate user input"
            }
          ]
        }
      ],
      "diff_summary": {
        "files_changed": 5,
        "insertions": 120,
        "deletions": 45
      },
      "review_instructions": "Review ONLY the changed lines marked with + in diff..."
    }
    """
    output = {
        "changed_files": [],
        "dependencies": [],
        "diff_summary": {},
        "review_instructions": REVIEW_PROMPT
    }

    # Parse diff to identify changed lines
    if diff_file:
        diff_data = parse_diff(diff_file)
        output["diff_summary"] = diff_data.summary

    # Add primary files with line numbers and diff hunks
    for file_path in primary_files:
        content = read_file_with_line_numbers(file_path)
        file_diff = diff_data.get_file_diff(file_path) if diff_file else None

        output["changed_files"].append({
            "path": file_path,
            "content": content,
            "diff": file_diff,
            "changed_lines": diff_data.get_changed_lines(file_path)
        })

    # Add dependencies with signatures + line numbers
    output["dependencies"] = parse_signatures_to_json(signatures)

    return json.dumps(output, indent=2)

REVIEW_PROMPT = """
You are reviewing a pull request. You have access to:

1. **Changed files** (full content with line numbers)
2. **Changed lines** (specific lines that were modified)
3. **Dependencies** (signatures showing available functions/classes with line numbers)
4. **Git diff** (what actually changed: additions, deletions, modifications)

**Your task:**
- Review ONLY the changed lines (marked with + in diff)
- Check for: bugs, security issues, performance problems, style violations
- Reference dependency signatures to verify correct usage
- Be concise but specific
- Suggest code fixes when possible

**CRITICAL RULES:**
1. ONLY comment on lines that were actually changed
2. Include line numbers in your comments
3. Reference dependency functions with file:line notation
4. Severity levels: error (must fix), warning (should fix), info (suggestion)

**Output format:**
Return JSON with this exact structure:
{
  "comments": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "severity": "error|warning|info",
      "message": "Brief description of the issue",
      "suggestion": "Optional code fix (if applicable)",
      "reference": "Optional reference to dependency (e.g., utils.py:25)"
    }
  ]
}

**Example:**
{
  "comments": [
    {
      "file": "main.py",
      "line": 42,
      "severity": "error",
      "message": "Potential NullPointerException when user is None",
      "suggestion": "if user is not None:\\n    user.save()",
      "reference": "utils.py:15 - get_user() can return None"
    }
  ]
}
"""
```

### Component 3: MCP Server Implementation

```python
# codecontextcrafter/mcp_server.py

"""
MCP Server for CodeContextCrafter review integration.

Provides tools for external systems to:
- Get code context for changed files
- Submit review comments
- Retrieve file content with line numbers
"""

from typing import List, Dict, Optional
import json
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("codecontextcrafter-review")

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_code_context",
            description="Get code context for changed files with dependencies",
            inputSchema={
                "type": "object",
                "properties": {
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of changed file paths"
                    },
                    "diff_file": {
                        "type": "string",
                        "description": "Path to git diff file"
                    },
                    "depth": {
                        "type": "integer",
                        "default": 2,
                        "description": "Dependency traversal depth"
                    },
                    "base_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Project root paths for dependency resolution"
                    }
                },
                "required": ["changed_files"]
            }
        ),
        Tool(
            name="submit_review",
            description="Submit structured review comments",
            inputSchema={
                "type": "object",
                "properties": {
                    "comments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file": {"type": "string"},
                                "line": {"type": "integer"},
                                "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                                "message": {"type": "string"},
                                "suggestion": {"type": "string"}
                            },
                            "required": ["file", "line", "severity", "message"]
                        }
                    }
                },
                "required": ["comments"]
            }
        ),
        Tool(
            name="get_file_with_lines",
            description="Get file content with line numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"}
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle MCP tool calls."""

    if name == "get_code_context":
        # Run ccc to generate context
        from codecontextcrafter.code_context_crafter import generate_review_context

        context = generate_review_context(
            changed_files=arguments["changed_files"],
            diff_file=arguments.get("diff_file"),
            depth=arguments.get("depth", 2),
            base_paths=arguments.get("base_paths")
        )

        return [TextContent(
            type="text",
            text=json.dumps(context, indent=2)
        )]

    elif name == "submit_review":
        # Store review comments (implementation depends on backend)
        comments = arguments["comments"]

        # Could post to:
        # - GitHub API
        # - GitLab API
        # - Custom review system
        # - Database

        return [TextContent(
            type="text",
            text=f"Submitted {len(comments)} review comments"
        )]

    elif name == "get_file_with_lines":
        # Read file with line numbers
        from codecontextcrafter.code_context_crafter import read_file_with_line_numbers

        content = read_file_with_line_numbers(
            arguments["file_path"],
            start_line=arguments.get("start_line"),
            end_line=arguments.get("end_line")
        )

        return [TextContent(type="text", text=content)]

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(main())
```

### Component 4: AI Review Script

```python
# .github/scripts/run_ai_review.py

"""
Call Claude API with review context and parse structured output.
"""

import json
import argparse
import anthropic
import os

def run_review(context_file: str, diff_file: str, output_file: str):
    """Run AI review using Claude."""

    # Load context
    with open(context_file) as f:
        context = json.load(f)

    # Load diff
    with open(diff_file) as f:
        diff = f.read()

    # Construct prompt
    prompt = f"""
{context['review_instructions']}

# Changed Files

{json.dumps(context['changed_files'], indent=2)}

# Dependencies (for reference)

{json.dumps(context['dependencies'], indent=2)}

# Git Diff

```diff
{diff}
```

Please review the changed lines and return structured JSON comments.
"""

    # Call Claude API
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # Parse response
    review_text = response.content[0].text

    # Extract JSON from response (Claude might wrap it in markdown)
    import re
    json_match = re.search(r'```json\n(.*?)\n```', review_text, re.DOTALL)
    if json_match:
        review_json = json.loads(json_match.group(1))
    else:
        # Assume entire response is JSON
        review_json = json.loads(review_text)

    # Write output
    with open(output_file, 'w') as f:
        json.dump(review_json, f, indent=2)

    print(f"Review complete: {len(review_json['comments'])} comments generated")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    run_review(args.context, args.diff, args.output)
```

## Phased Rollout

### Phase 1: Local CLI Review Tool (Week 1)
- [ ] Add `--format json-review` flag to ccc
- [ ] Implement review output format with line numbers
- [ ] Create local review script: `ccc review --pr 123`
- [ ] Test manually on real PRs

**Deliverable:** Developers can run locally:
```bash
# Review uncommitted changes
ccc review --local

# Review specific PR
ccc review --pr 123 --depth 2
```

### Phase 2: GitHub Action (Week 2)
- [ ] Create `.github/workflows/ai-code-review.yml`
- [ ] Implement GitHub API comment posting
- [ ] Add manual trigger via `/review` comment
- [ ] Rate limiting and cost controls

**Deliverable:** GitHub Action that runs on demand

### Phase 3: MCP Server (Week 3)
- [ ] Implement MCP server (`mcp_server.py`)
- [ ] Create tools: `get_code_context`, `submit_review`, `get_file_with_lines`
- [ ] Documentation for MCP integration
- [ ] Example: Integrate with Slack for review notifications

**Deliverable:** MCP server for external integrations

### Phase 4: Advanced Features (Week 4)
- [ ] Auto-approve trivial changes (docs, comments)
- [ ] Confidence scores for AI comments
- [ ] Learn from dismissed comments
- [ ] Custom review rules per repository

## Success Criteria

1. **Accuracy**: AI catches 80%+ of bugs found in manual review
2. **False Positive Rate**: <20% of AI comments are invalid/unhelpful
3. **Performance**: Review completes in <2 minutes for typical PR
4. **Cost**: <$0.10 per PR review (using Claude Haiku)
5. **Adoption**: Used in 10+ repositories within 3 months

## Challenges & Solutions

### Challenge 1: Context Window Limits

**Problem:** Large PRs (50+ files) exceed LLM context limits

**Solutions:**
- **Chunk reviews**: Review 5-10 files at a time
- **Prioritize high-risk files**: Focus on .py, .js, .java (not docs/tests)
- **Smart summarization**: Use smaller model for triage, detailed model for review
- **File filtering**: Only review files >10 lines changed

### Challenge 2: Cost Control

**Problem:** AI API calls on every PR can be expensive

**Solutions:**
- **Model selection**: Use Claude Haiku ($0.25/M tokens) for most reviews
- **Rate limiting**: Max 10 reviews per day per repo
- **Conditional trigger**:
  - Only after tests pass
  - Only for files matching patterns (src/**, not docs/**)
- **Cache contexts**: Reuse dependency signatures across reviews

### Challenge 3: False Positives

**Problem:** AI flags non-issues, reducing trust

**Solutions:**
- **Confidence scores**: Only post high-confidence comments
- **"Dismiss" mechanism**: Users can dismiss bad suggestions
- **Learning system**: Track dismissed comments, improve prompts
- **Human-in-loop**: Require approval before posting to PR

### Challenge 4: Integration Complexity

**Problem:** Different CI/CD systems (GitHub, GitLab, Bitbucket)

**Solutions:**
- **MCP Server**: Platform-agnostic interface
- **Webhook support**: Generic webhook for any platform
- **Adapter pattern**: Platform-specific adapters for posting comments

## Benefits

### For Developers
- ✅ Catch bugs before manual review
- ✅ Learn best practices from AI suggestions
- ✅ Faster feedback loop (minutes vs hours)
- ✅ Consistent review quality

### For Teams
- ✅ Reduce reviewer burden
- ✅ Enforce coding standards automatically
- ✅ Improve code quality metrics
- ✅ Faster PR merge times

### For Organizations
- ✅ Scale code review process
- ✅ Reduce security vulnerabilities
- ✅ Knowledge transfer (junior devs learn from AI)
- ✅ Measurable ROI (bugs caught / cost)

## Open Questions

1. **Review scope**: Review entire PR or just diff?
   - **Recommendation**: Just diff (changed lines only)

2. **Approval workflow**: Auto-approve after AI review?
   - **Recommendation**: No, AI is advisory only

3. **Privacy**: How to handle proprietary code?
   - **Recommendation**: Self-hosted LLM option, or redaction

4. **Customization**: Per-repo review rules?
   - **Recommendation**: `.ccc-review.yml` config file

5. **Integration with existing tools**:
   - SonarQube, ESLint, Pylint integration?
   - **Recommendation**: Run AI review AFTER static analyzers

## Related Issues

- #TBD Direct tree-sitter integration (enables better code understanding)
- #TBD Enhanced import detection (more accurate dependency context)
- #TBD Line-level annotations (essential for posting comments)

## Testing Strategy

**Test Repositories:**
1. **Simple project**: <10 files, basic Python
2. **Medium project**: CodeContextCrafter itself
3. **Complex project**: Spring Boot (multi-module Java)

**Metrics to Track:**
- Accuracy: % of real bugs caught
- False positives: % of invalid comments
- Review time: End-to-end duration
- Cost per review: API token usage
- Developer satisfaction: Survey scores

## Additional Notes

This is a **high-impact feature** that:
- Demonstrates unique value proposition of CCC
- Drives adoption (teams need automated review)
- Justifies premium pricing (if commercialized)
- Opens door to enterprise sales

Should be implemented **after**:
- Direct tree-sitter integration (#TBD)
- Line-level annotation support (#TBD)

**Marketing angle:**
> "CodeContextCrafter: The only AI code review tool that understands your dependencies"
