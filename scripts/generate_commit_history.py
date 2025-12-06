#!/usr/bin/env python3
"""
Generate COMMIT_HISTORY.md from git log.
Run from project root: python3 scripts/generate_commit_history.py
"""

import subprocess
from collections import defaultdict
from datetime import datetime


def generate_commit_history():
    """Generate commit history markdown file from git log."""
    
    # Get git log with date and subject
    cmd = ['git', 'log', '--format=%ad|%s', '--date=short', '--reverse']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    # Parse commits and group by date
    commits_by_date = defaultdict(list)
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            date_str, subject = line.split('|', 1)
            commits_by_date[date_str].append(subject)
    
    # Calculate statistics
    total_commits = sum(len(commits) for commits in commits_by_date.values())
    total_days = len(commits_by_date)
    
    # Generate markdown
    output = ["# Commit History by Date", ""]
    output.append(f"**Total Commits:** {total_commits}")
    output.append(f"**Total Days Worked:** {total_days}")
    output.append("")
    output.append("---")
    output.append("")
    
    # Sort dates in reverse chronological order (newest first)
    sorted_dates = sorted(commits_by_date.keys(), reverse=True)
    
    for date_str in sorted_dates:
        commits = commits_by_date[date_str]
        count = len(commits)
        output.append(f"## {date_str} ({count} commit{'s' if count != 1 else ''})")
        output.append("")
        
        # Add each commit message
        for commit in commits:
            output.append(f"- {commit}")
        
        output.append("")
    
    return '\n'.join(output)


if __name__ == '__main__':
    content = generate_commit_history()
    with open('COMMIT_HISTORY.md', 'w') as f:
        f.write(content)
    print("Generated COMMIT_HISTORY.md")

