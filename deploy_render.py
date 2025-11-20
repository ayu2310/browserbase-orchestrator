"""Deploy to Render using Render API."""
import os
import sys
import json
import httpx
from pathlib import Path


def check_prerequisites():
    """Check if we have what we need to deploy."""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check for Render API key
    api_key = os.getenv("RENDER_API_KEY")
    if not api_key:
        issues.append("RENDER_API_KEY environment variable not set")
        print("   ⚠️  RENDER_API_KEY not found")
    else:
        print("   ✅ RENDER_API_KEY found")
    
    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        issues.append("OPENAI_API_KEY environment variable not set")
        print("   ⚠️  OPENAI_API_KEY not found")
    else:
        print("   ✅ OPENAI_API_KEY found")
    
    # Check for git repo
    if not Path(".git").exists():
        issues.append("Not a git repository - need to initialize git first")
        print("   ⚠️  Not a git repository")
    else:
        print("   ✅ Git repository found")
    
    # Check for render.yaml
    if not Path("render.yaml").exists():
        issues.append("render.yaml not found")
        print("   ⚠️  render.yaml not found")
    else:
        print("   ✅ render.yaml found")
    
    if issues:
        print("\n❌ Prerequisites not met:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("\n✅ All prerequisites met!")
    return True


def get_render_api_key():
    """Get Render API key from user or environment."""
    api_key = os.getenv("RENDER_API_KEY")
    if api_key:
        return api_key
    
    print("\n📝 Render API Key required")
    print("   Get it from: https://dashboard.render.com/account/api-keys")
    api_key = input("   Enter your Render API Key: ").strip()
    
    if not api_key:
        print("❌ API key is required")
        sys.exit(1)
    
    return api_key


async def deploy_via_api():
    """Deploy using Render API."""
    print("\n🚀 Deploying to Render via API...")
    
    api_key = get_render_api_key()
    
    # Render API base URL
    base_url = "https://api.render.com/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    # Check if service already exists
    print("\n📋 Checking existing services...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/services",
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            services = response.json()
            
            existing = None
            for service in services:
                if service.get("name") == "browserbase-orchestrator-api":
                    existing = service
                    break
            
            if existing:
                print(f"   ✅ Service already exists: {existing.get('service', {}).get('url', 'N/A')}")
                print(f"   Service ID: {existing.get('service', {}).get('id', 'N/A')}")
                print("\n💡 Service is already deployed!")
                print(f"   URL: {existing.get('service', {}).get('url', 'Check Render dashboard')}")
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("   ❌ Invalid API key")
                return False
            print(f"   ⚠️  Could not check existing services: {e}")
        except Exception as e:
            print(f"   ⚠️  Error checking services: {e}")
    
    print("\n❌ Cannot deploy via API without GitHub repository connection")
    print("\n💡 Alternative: Deploy via Render Dashboard")
    print("   1. Go to https://dashboard.render.com")
    print("   2. Click 'New +' → 'Blueprint'")
    print("   3. Connect your GitHub repository")
    print("   4. Render will detect render.yaml")
    print("   5. Set OPENAI_API_KEY environment variable")
    print("   6. Click 'Apply'")
    
    return False


def setup_git_repo():
    """Initialize git repo if needed."""
    if Path(".git").exists():
        print("✅ Git repository already initialized")
        return True
    
    print("\n📦 Setting up git repository...")
    
    try:
        import subprocess
        
        # Initialize git
        subprocess.run(["git", "init"], check=True, capture_output=True)
        print("   ✅ Git initialized")
        
        # Add files
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        print("   ✅ Files staged")
        
        # Initial commit
        subprocess.run(
            ["git", "commit", "-m", "Initial commit - Browserbase Orchestrator"],
            check=True,
            capture_output=True,
        )
        print("   ✅ Initial commit created")
        
        print("\n⚠️  You need to:")
        print("   1. Create a repository on GitHub")
        print("   2. Add it as remote: git remote add origin <your-repo-url>")
        print("   3. Push: git push -u origin main")
        print("\n   Then deploy via Render Dashboard → Blueprint")
        
        return False
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        return False
    except FileNotFoundError:
        print("   ❌ Git not installed")
        return False


async def main():
    """Main deployment function."""
    print("=" * 60)
    print("🚀 Render Deployment Script")
    print("=" * 60)
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n💡 Setting up prerequisites...")
        
        # Try to set up git
        if not Path(".git").exists():
            setup_git_repo()
            return
        
        print("\n❌ Please fix the issues above before deploying")
        sys.exit(1)
    
    # Try API deployment
    import asyncio
    success = await deploy_via_api()
    
    if not success:
        print("\n" + "=" * 60)
        print("📋 Manual Deployment Instructions")
        print("=" * 60)
        print()
        print("Since API deployment requires GitHub connection, use the dashboard:")
        print()
        print("1. Push your code to GitHub:")
        print("   git remote add origin <your-repo-url>")
        print("   git push -u origin main")
        print()
        print("2. Go to https://dashboard.render.com")
        print("3. Click 'New +' → 'Blueprint'")
        print("4. Connect GitHub and select your repository")
        print("5. Set environment variable: OPENAI_API_KEY")
        print("6. Click 'Apply'")
        print()
        print("Your render.yaml is already configured!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

