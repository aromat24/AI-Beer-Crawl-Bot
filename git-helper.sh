#!/bin/bash
# Git workflow helper script for AI Beer Crawl Bot

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🍺 AI Beer Crawl Bot - Git Workflow Helper${NC}"
echo "=============================================="

# Function to show git status
show_status() {
    echo -e "${YELLOW}Current Git Status:${NC}"
    git status --short
    echo ""
}

# Function to create a new feature branch
new_feature() {
    if [ -z "$1" ]; then
        echo "Usage: $0 feature <branch-name>"
        exit 1
    fi
    git checkout -b "feature/$1"
    echo -e "${GREEN}Created and switched to feature/$1${NC}"
}

# Function to commit changes
quick_commit() {
    if [ -z "$1" ]; then
        echo "Usage: $0 commit <message>"
        exit 1
    fi
    git add .
    git commit -m "$1"
    echo -e "${GREEN}Changes committed: $1${NC}"
}

# Function to push changes
push_changes() {
    current_branch=$(git branch --show-current)
    git push -u origin "$current_branch"
    echo -e "${GREEN}Pushed changes to origin/$current_branch${NC}"
}

# Function to deploy (commit and push)
deploy() {
    if [ -z "$1" ]; then
        echo "Usage: $0 deploy <commit-message>"
        exit 1
    fi
    git add .
    git commit -m "$1"
    current_branch=$(git branch --show-current)
    git push -u origin "$current_branch"
    echo -e "${GREEN}Deployed: $1${NC}"
}

# Main menu
case "$1" in
    "status"|"s")
        show_status
        ;;
    "feature"|"f")
        new_feature "$2"
        ;;
    "commit"|"c")
        quick_commit "$2"
        ;;
    "push"|"p")
        push_changes
        ;;
    "deploy"|"d")
        deploy "$2"
        ;;
    *)
        echo "Git Workflow Commands:"
        echo "  $0 status     - Show git status"
        echo "  $0 feature <name> - Create new feature branch"
        echo "  $0 commit <msg>   - Add all and commit"
        echo "  $0 push           - Push current branch"
        echo "  $0 deploy <msg>   - Add, commit, and push"
        echo ""
        echo "Examples:"
        echo "  $0 feature admin-controls"
        echo "  $0 deploy 'Add bot behavior controls to dashboard'"
        ;;
esac
