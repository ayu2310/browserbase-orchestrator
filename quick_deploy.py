#!/usr/bin/env python3
"""Quick test script for Temporal Cloud connection."""
import asyncio
import os
import sys
from temporalio.client import Client
from config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, validate_config


def check_credentials():
    """Check if required credentials are set."""
    print("🔍 Checking credentials...")
    
    required = {
        "TEMPORAL_ADDRESS": os.getenv("TEMPORAL_ADDRESS"),
        "TEMPORAL_NAMESPACE": os.getenv("TEMPORAL_NAMESPACE", "default"),
        "TEMPORAL_API_KEY": os.getenv("TEMPORAL_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }
    
    missing = [key for key, value in required.items() if not value and key != "TEMPORAL_NAMESPACE"]
    
    if missing:
        print(f"❌ Missing required credentials: {', '.join(missing)}")
        print("\n💡 Set environment variables:")
        print("   TEMPORAL_ADDRESS=your-namespace.xyz.tmprl.cloud:7233")
        print("   TEMPORAL_NAMESPACE=default")
        print("   TEMPORAL_API_KEY=tck_xxxxxxxxxxxxx")
        print("   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx")
        return False
    
    print("✅ All credentials are set")
    print(f"   Temporal: {required['TEMPORAL_ADDRESS']}")
    print(f"   Namespace: {required['TEMPORAL_NAMESPACE']}")
    return True


async def test_connection():
    """Test connection to Temporal Cloud."""
    print("\n🔍 Testing connection to Temporal Cloud...")
    
    try:
        api_key = os.getenv("TEMPORAL_API_KEY")
        address = os.getenv("TEMPORAL_ADDRESS")
        namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
        client = await Client.connect(
            target_host=address,
            namespace=namespace,
            api_key=api_key,
            tls=True,
        )
        
        print(f"✅ Connected to Temporal Cloud!")
        print(f"   Address: {address}")
        print(f"   Namespace: {namespace}")
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check TEMPORAL_ADDRESS is correct (include :7233 port)")
        print("   - Verify API key is correct and not expired")
        print("   - Ensure namespace name is correct")
        return False


async def main():
    """Main function."""
    print("=" * 60)
    print("🚀 Quick Deploy Test")
    print("=" * 60)
    print()
    
    if not check_credentials():
        sys.exit(1)
    
    try:
        validate_config()
        print("✅ Configuration valid")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    success = await test_connection()
    if not success:
        sys.exit(1)
    
    print("\n✅ Ready to deploy!")
    print("\n📋 Next Steps:")
    print("   1. Deploy worker: python worker_cloud.py")
    print("   2. Or deploy to Render using render.yaml")
    print("   3. Test: python cli.py run 'Navigate to example.com'")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
