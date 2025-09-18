# tools/patchversiontool.py

import requests
import json
import os
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("HOST_BASE_URL")

# Global cache for patch versions and user selection state
patch_cache = {}
user_selection_state = {}

@tool("patch_version_generator", return_direct=True)
def patch_version_tool(query: str) -> str:
    """
    PATCH VERSION REPORT GENERATOR
    Handles patch report generation with version selection
    """
    try:
        # Load patch versions from JSON
        json_file_path = os.path.join(os.getcwd(), "test-data-source.json")
        
        if not os.path.exists(json_file_path):
            return f"❌ test-data-source.json not found in project root"
        
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        available_versions = data.get("testManagement", {}).get("patch_versions", [])
        if not available_versions:
            return "❌ No patch versions found in configuration"
        
        # Cache the available versions
        patch_cache["available_versions"] = available_versions
        
        # Parse the query to check if version is specified
        query_lower = query.lower().strip()
        
        # Check if this is an initial patch report request
        if query_lower in ["execute patch report", "patch report", "execute patch", "patch"]:
            return f"""📊 **PATCH VERSION REPORT GENERATOR ACTIVATED**

🔍 **Available Patch Versions**:
{', '.join(available_versions)}

**Please specify which version you want to generate the report for:**

Use command: `execute patch report version [VERSION]`

**Examples:**
- `execute patch report version 24C`
- `execute patch report version 25A`

**Choose from the available versions listed above.**"""
        
        # Check if version is specified in the query
        if "version" in query_lower:
            # Extract version from query
            parts = query_lower.split()
            version_idx = -1
            for i, part in enumerate(parts):
                if part == "version" and i + 1 < len(parts):
                    version_idx = i + 1
                    break
            
            if version_idx == -1:
                return f"""❌ **VERSION NOT SPECIFIED**

Please specify the version after 'version' keyword.

**Available versions**: {', '.join(available_versions)}

**Usage**: `execute patch report version [VERSION]`"""
            
            requested_version = parts[version_idx].upper()
            
            # Validate version
            if requested_version not in available_versions:
                return f"""❌ **INVALID PATCH VERSION**

🚫 **Requested**: {requested_version}
✅ **Available versions**: {', '.join(available_versions)}

**Please use one of the available versions.**

**Usage**: `execute patch report version [VALID_VERSION]`"""
            
            # Generate the patch report
            return generate_patch_report(requested_version)
        
        # If no version keyword found, show available versions
        return f"""📊 **PATCH VERSION REPORT GENERATOR**

🔍 **Available Patch Versions**:
{', '.join(available_versions)}

**Please specify which version you want:**

Use command: `execute patch report version [VERSION]`"""
    
    except FileNotFoundError:
        return f"❌ test-data-source.json file not found in project root"
    except json.JSONDecodeError:
        return f"❌ Invalid JSON format in test-data-source.json"
    except Exception as e:
        return f"❌ Error in patch version tool: {str(e)}"

def generate_patch_report(version: str) -> str:
    """
    Generate patch report for the specified version
    """
    try:
        # Call the API endpoint
        resp = requests.get(f"{BASE_URL}/run-patchreport/{version}")
        
        if resp.status_code == 200:
            # Your API is working, so any 200 response means success
            return f"""✅ **PATCH VERSION REPORT GENERATED**

🎯 **Version**: {version}
📊 **Status**: Report generated successfully ✅

📋 **Report Generated**: Oracle patch analysis for version {version}
📄 **File Status**: Report files have been created in the reports folder
🔧 **API Response**: HTTP 200 OK - Generation completed

✨ **Summary**: Patch version report for {version} has been successfully generated!

🔍 **Next Steps**: 
- Check the reports folder for the generated files
- Review the Oracle patch analysis data
- Files are ready for download/review"""
        else:
            return f"""❌ **PATCH REPORT GENERATION FAILED**

🎯 **Version**: {version}
❌ **Status**: HTTP {resp.status_code}
📊 **Error**: {resp.text}

Please verify the version and try again."""
    
    except requests.exceptions.RequestException as e:
        return f"❌ Network error while generating patch report for version {version}: {str(e)}"
    except Exception as e:
        return f"❌ Error generating patch report for version {version}: {str(e)}"
