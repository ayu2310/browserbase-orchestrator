"""Push code to GitHub - creates repo and pushes if needed."""
import os
import sys
import subprocess
import httpx
import json
from pathlib import Path


def check_git_remote():
    """Check if git remote is configured."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def create_github_repo(token, repo_name, description="Browserbase Orchestrator API"):
    """Create a GitHub repository using API."""
    print(f"📦 Creating GitHub repository: {repo_name}")
    
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False,  # We already have code
    }
    
    try:
        async def create():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code == 201:
                    repo_data = response.json()
                    return repo_data.get("clone_url"), repo_data.get("html_url")
                elif response.status_code == 422:
                    # Repo might already exist
                    error = response.json()
                    if "already exists" in str(error).lower():
                        return f"https://github.com/{get_github_username(token)}/{repo_name}.git", f"https://github.com/{get_github_username(token)}/{repo_name}"
                response.raise_for_status()
                return None, None
        
        import asyncio
        clone_url, html_url = asyncio.run(create())
        return clone_url, html_url
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, None


def get_github_username(token):
    """Get GitHub username from token."""
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        async def get_user():
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("login")
                return None
        
        import asyncio
        return asyncio.run(get_user())
    except Exception:
        return None


def push_to_github(repo_url, branch="master"):
    """Push code to GitHub."""
    print(f"📤 Pushing to GitHub...")
    
    # Check if remote exists
    try:
        subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
        )
        # Remote exists, update it
        subprocess.run(
            ["git", "remote", "set-url", "origin", repo_url],
            check=True,
            capture_output=True,
        )
        print("   ✅ Updated remote URL")
    except subprocess.CalledProcessError:
        # Remote doesn't exist, add it
        subprocess.run(
            ["git", "remote", "add", "origin", repo_url],
            check=True,
            capture_output=True,
        )
        print("   ✅ Added remote")
    
    # Rename branch to main if needed
    try:
        subprocess.run(
            ["git", "branch", "-M", "main"],
            check=True,
            capture_output=True,
        )
        branch = "main"
    except subprocess.CalledProcessError:
        pass  # Already on main or can't rename
    
    # Push
    try:
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("   ✅ Successfully pushed to GitHub!")
            return True
        else:
            print(f"   ⚠️  Push output: {result.stderr}")
            if "Authentication failed" in result.stderr:
                print("   ❌ Authentication failed. You may need to:")
                print("      - Use a Personal Access Token instead of password")
                print("      - Set up SSH keys")
                return False
            return False
    except Exception as e:
        print(f"   ❌ Error pushing: {e}")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("🚀 Push to GitHub")
    print("=" * 60)
    print()
    
    # Check for GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("📝 GitHub Personal Access Token required")
        print("   Get one from: https://github.com/settings/tokens")
        print("   Required scopes: repo (full control of private repositories)")
        print()
        token = input("Enter your GitHub token (or press Enter to skip API creation): ").strip()
        if not token:
            print("\n⚠️  No token provided. You'll need to:")
            print("   1. Create repo manually on GitHub")
            print("   2. Run: git remote add origin https://github.com/USERNAME/REPO.git")
            print("   3. Run: git push -u origin main")
            return
    
    # Get repo name from env or use default
    repo_name = os.getenv("GITHUB_REPO_NAME", "browserbase-orchestrator")
    if len(sys.argv) > 1:
        repo_name = sys.argv[1]
    
    # Check if remote already exists
    existing_remote = check_git_remote()
    if existing_remote:
        print(f"✅ Git remote already configured: {existing_remote}")
        # Just push to existing remote
        success = push_to_github(existing_remote)
        if success:
            print(f"\n✅ Code pushed to: {existing_remote}")
        return
    
    # Create repo via API
    clone_url, html_url = create_github_repo(token, repo_name)
    
    if clone_url:
        print(f"   ✅ Repository created: {html_url}")
        print(f"   Clone URL: {clone_url}")
        
        # Push code
        success = push_to_github(clone_url)
        if success:
            print(f"\n✅ Success! Your code is on GitHub:")
            print(f"   {html_url}")
            print(f"\n📋 Next step: Deploy on Render")
            print(f"   Go to https://dashboard.render.com → New → Blueprint")
            print(f"   Select your repository and deploy!")
    else:
        print("   ⚠️  Could not create repository via API")
        print("   You can create it manually and push:")
        print(f"   1. Create repo: https://github.com/new")
        print(f"   2. Name: {repo_name}")
        print(f"   3. Run: git remote add origin https://github.com/USERNAME/{repo_name}.git")
        print(f"   4. Run: git push -u origin main")


if __name__ == "__main__":
    main()

