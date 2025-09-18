# tools/TDM_generator.py
import requests
import json
import os
from langchain.tools import tool
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


# Base URL and cached templates
TDM_BASE_URL = BASE_URL = os.getenv("TDM_BASE_URL")
_last_used_template = ""

@tool("tdm_data_generator", return_direct=True)
def tdm_data_generator(query: str) -> str:
    """
    TDM DATA GENERATOR - Generates new test data
    Handles: "generate test data for template_name" or "generate test data for template_name X rows"
    """
    global _last_used_template
    
    try:
        query_lower = query.lower().strip()
        
        # Extract template and row count
        template_name = _extract_template_name(query)
        row_count = _extract_row_count(query)
        
        if not template_name:
            return "❌ **TEMPLATE NOT SPECIFIED**\n\nPlease specify: 'generate test data for [template_name]'"
        
        # Validate template exists
        if not _validate_template(template_name):
            return _get_template_error(template_name)
        
        # Store last used template
        matched_template = _get_matched_template(template_name)
        _last_used_template = matched_template
        
        # Generate data directly (always has row count now - default 50)
        return _generate_test_data(matched_template, row_count)
        
    except Exception as e:
        return f"❌ **TDM GENERATOR ERROR**: {str(e)}"

def _extract_template_name(query: str) -> str:
    """Extract template name from query"""
    try:
        query_lower = query.lower().strip()
        
        if " for " in query_lower:
            # Split and get everything after "for"
            template_part = query_lower.split(" for ")[1]
            
            # Remove row-related suffixes
            for suffix in [" rows", " row", " 10", " 20", " 30", " 50"]:
                if suffix in template_part:
                    template_part = template_part.split(suffix)[0]
            
            return template_part.strip()
        
        return ""
    except Exception as e:
        print(f"Error extracting template name: {e}")
        return ""

def _extract_row_count(query: str) -> int:
    """Extract row count from query. Default to 50 if none specified."""
    try:
        import re
        # Try to find any number in the query
        matches = re.findall(r'\b(\d+)\b', query)
        if matches:
            # Take the first number found that looks like a row count
            return int(matches[0])
        # Default row count
        return 50
    except Exception as e:
        print(f"Error extracting row count: {e}")
        return 50

def _validate_template(template_name: str) -> bool:
    """Validate if template exists"""
    try:
        templates_url = f"{TDM_BASE_URL}/templates/TDM User"
        response = requests.get(templates_url, timeout=10)
        
        if response.status_code == 200:
            available_templates = response.json().get("templates", [])
            return _find_matching_template(template_name, available_templates) is not None
        return False
    except:
        return False

def _get_matched_template(template_name: str) -> str:
    """Get the actual matched template name"""
    try:
        templates_url = f"{TDM_BASE_URL}/templates/TDM User"
        response = requests.get(templates_url, timeout=10)
        
        if response.status_code == 200:
            available_templates = response.json().get("templates", [])
            return _find_matching_template(template_name, available_templates)
        return template_name
    except:
        return template_name

def _find_matching_template(template_name: str, available_templates: list) -> str:
    """Find matching template"""
    template_lower = template_name.lower()
    
    # Exact match
    for template in available_templates:
        if template.lower() == template_lower:
            return template
    
    # Partial match
    for template in available_templates:
        if template_lower in template.lower() or template.lower() in template_lower:
            return template
    
    return None

def _get_template_error(template_name: str) -> str:
    """Get template error message with available templates"""
    try:
        templates_url = f"{TDM_BASE_URL}/templates/TDM User"
        response = requests.get(templates_url, timeout=10)
        
        if response.status_code == 200:
            available_templates = response.json().get("templates", [])
            templates_list = ", ".join(available_templates)
            
            return f"""❌ **TEMPLATE NOT FOUND**
🔍 **Searched for**: {template_name}
📋 **Available Templates for data generation**: {templates_list}
❗ Please ask the admin to add the template '{template_name}' or use an available template."""
        else:
            return f"❌ **TEMPLATE ERROR**: Cannot validate template '{template_name}'"
    except:
        return f"❌ **API ERROR**: Cannot fetch available templates"

def _generate_test_data(template_name: str, row_count: int) -> str:
    """Generate test data via API"""
    try:
        generate_url = f"{TDM_BASE_URL}/generate-test-data"
        payload = {
            "username": "TDM User",
            "template_name": template_name,
            "num_records": str(row_count)
        }
        
        response = requests.post(generate_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            filename, filepath = _save_file(response, template_name)
            
            # Create response with file attachment capability
            response_text = f"""✅ **TEST DATA GENERATED SUCCESSFULLY**
🎯 **Template**: {template_name}
📊 **Records**: {row_count}
📁 **File**: {filename}
📂 **Location**: TDM_files folder
🔍 **Review**: Check the data in TDM data sub app
💡 **Need Changes?** Mention field names in your request:
- "Invoice ID should start with ABC"
- "Customer Name should be realistic"
- "Amount field should be between 1000-5000"

[FILE_ATTACHMENT:{filepath}]"""
            
            return response_text
        else:
            return f"❌ **GENERATION FAILED**: {response.text}"
            
    except Exception as e:
        return f"❌ **GENERATION ERROR**: {str(e)}"

def _save_file(response, filename_prefix: str) -> tuple:
    """Save file to TDM_files folder and return filename and filepath"""
    try:
        os.makedirs("TDM_files", exist_ok=True)
        filename = f"{filename_prefix}.xlsx"
        filepath = os.path.join("TDM_files", filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filename, filepath
    except Exception as e:
        error_filename = f"file_save_error_{filename_prefix}.xlsx"
        return error_filename, ""
