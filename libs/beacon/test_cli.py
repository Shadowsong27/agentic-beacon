"""Test script to verify CLI functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentic_warehouse_cli.distributor import WarehouseDistributor

# Test paths
warehouse_root = Path(__file__).parent.parent.parent
test_project = Path(__file__).parent / "test_project"

print("=" * 60)
print("Testing Agentic Warehouse CLI")
print("=" * 60)
print()

print(f"Warehouse root: {warehouse_root}")
print(f"Test project: {test_project}")
print()

# Create test project directory
test_project.mkdir(exist_ok=True)

# Create distributor
distributor = WarehouseDistributor(
    warehouse_root=warehouse_root, target_root=test_project
)

# Test 1: List available content
print("Test 1: Listing available content")
print("-" * 60)
available = distributor.list_available()
print(f"Contexts: {available['contexts']}")
print(f"Knowledge: {available['knowledge']}")
print(f"Skills: {available['skills']}")
print()

# Test 2: Setup distribution
print("Test 2: Setting up distribution")
print("-" * 60)
result = distributor.setup(
    contexts=["global", "python"],
    knowledge_scopes=["global"],
    skills=["example-skill"],
)
print(f"Installed {result['contexts']} contexts")
print(f"Installed {result['knowledge']} knowledge files")
print(f"Installed {result['skills']} skills")
print(f"Target directory: {result['target_dir']}")
print()

# Test 3: Verify installation
print("Test 3: Verifying installation")
print("-" * 60)
opencode_dir = test_project / ".opencode"
if opencode_dir.exists():
    print(f"✓ .opencode directory created: {opencode_dir}")
    print(f"✓ Contexts: {list((opencode_dir / 'contexts').glob('*.md'))}")
    print(f"✓ Knowledge: {list((opencode_dir / 'knowledge').rglob('*.md'))}")
    print(f"✓ Skills: {list((opencode_dir / 'skills').iterdir())}")
else:
    print("✗ .opencode directory not created")
print()

# Test 4: Status check
print("Test 4: Reading configuration")
print("-" * 60)
config = distributor._read_config()
print(f"Config: {config}")
print()

# Test 5: Clean up
print("Test 5: Cleaning up")
print("-" * 60)
if distributor.clean():
    print("✓ Cleaned up successfully")
else:
    print("✗ Nothing to clean")
print()

print("=" * 60)
print("All tests completed!")
print("=" * 60)
