# tools/TDM_editor.py

import requests
import json
import os
import re
from langchain.tools import tool
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


# Base URL and cached templates
TDM_BASE_URL = BASE_URL = os.getenv("TDM_BASE_URL")
_cached_templates = []
_last_used_template = ""

def _get_available_templates() -> list:
    """Get and cache available templates"""
    global _cached_templates
    try:
        templates_url = f"{TDM_BASE_URL}/templates/TDM User"
        response = requests.get(templates_url, timeout=10)
        
        if response.status_code == 200:
            _cached_templates = response.json().get("templates", [])
            return _cached_templates
        return _cached_templates
    except:
        return _cached_templates

def _validate_template(template_name: str) -> bool:
    """Validate if template exists"""
    available_templates = _get_available_templates()
    return _find_matching_template(template_name, available_templates) is not None

def _get_matched_template(template_name: str) -> str:
    """Get the actual matched template name"""
    available_templates = _get_available_templates()
    matched = _find_matching_template(template_name, available_templates)
    return matched if matched else template_name

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
    available_templates = _get_available_templates()
    templates_list = ", ".join(available_templates)
    
    return f"""❌ **TEMPLATE NOT FOUND**

🔍 **Searched for**: {template_name}
📋 **Available Templates**: {templates_list}

❗ Please use an available template."""

@tool("tdm_data_editor", return_direct=True)
def tdm_data_editor(query: str) -> str:
    """
    TDM DATA EDITOR - Modifies existing test data based on field specifications
    Handles: Template editing requests with field modifications
    """
    global _last_used_template
    
    try:
        template_name = _extract_template_name(query)
        feedback_text = _extract_feedback_text(query)
        
        if not template_name:
            return "❌ **TEMPLATE NOT SPECIFIED**\n\nPlease specify the template name in your request."
        
        if not feedback_text:
            return "❌ **MODIFICATION REQUEST NOT CLEAR**\n\nPlease specify what changes you want to make."
        
        # Simple validation
        if not _validate_template(template_name):
            return _get_template_error(template_name)
        
        matched_template = _get_matched_template(template_name)
        _last_used_template = matched_template
        
        return _apply_feedback(matched_template, feedback_text)
        
    except Exception as e:
        return f"❌ **TDM EDITOR ERROR**: {str(e)}"

def _extract_template_name(query: str) -> str:
    """Extract template name from various query patterns"""
    query_lower = query.lower()
    
    # Pattern 1: "edit [template_name]" or "update [template_name]"
    edit_patterns = [
        r'edit\s+(?:the\s+)?(?:data\s+for\s+)?(?:template\s+)?(?:name\s+)?[\'"]?([^\'"\s,]+)[\'"]?',
        r'update\s+(?:the\s+)?(?:template\s+)?[\'"]?([^\'"\s,]+)[\'"]?',
        r'modify\s+(?:the\s+)?(?:template\s+)?[\'"]?([^\'"\s,]+)[\'"]?',
        r'change\s+(?:the\s+)?(?:template\s+)?[\'"]?([^\'"\s,]+)[\'"]?'
    ]
    
    for pattern in edit_patterns:
        match = re.search(pattern, query_lower)
        if match:
            return match.group(1).strip()
    
    # Pattern 2: "in [template_name]" or "for [template_name]"
    in_patterns = [
        r'in\s+(?:the\s+)?[\'"]?([^\'"\s,]+)[\'"]?',
        r'for\s+(?:the\s+)?(?:template\s+)?[\'"]?([^\'"\s,]+)[\'"]?'
    ]
    
    for pattern in in_patterns:
        match = re.search(pattern, query_lower)
        if match:
            template_candidate = match.group(1).strip()
            # Check if it looks like a template name (contains template keywords)
            if any(keyword in template_candidate for keyword in ['template', 'td_', '_template']):
                return template_candidate
    
    return ""

def _extract_feedback_text(query: str) -> str:
    """Extract the feedback/modification text from the query"""
    # Remove common prefixes to get the actual feedback
    feedback = query
    
    # Remove edit/update prefixes
    prefixes_to_remove = [
        r'^i\s+want\s+to\s+edit\s+(?:the\s+)?(?:data\s+for\s+)?(?:template\s+)?(?:name\s+)?[\'"]?[^\'"\s,]+[\'"]?\s*',
        r'^edit\s+(?:the\s+)?(?:data\s+for\s+)?(?:template\s+)?(?:name\s+)?[\'"]?[^\'"\s,]+[\'"]?\s*',
        r'^update\s+(?:the\s+)?(?:template\s+)?[\'"]?[^\'"\s,]+[\'"]?\s*',
        r'^modify\s+(?:the\s+)?(?:template\s+)?[\'"]?[^\'"\s,]+[\'"]?\s*',
        r'^change\s+(?:the\s+)?(?:template\s+)?[\'"]?[^\'"\s,]+[\'"]?\s*'
    ]
    
    for prefix in prefixes_to_remove:
        feedback = re.sub(prefix, '', feedback, flags=re.IGNORECASE).strip()
    
    # Remove "so that" connectors
    feedback = re.sub(r'^so\s+that\s+', '', feedback, flags=re.IGNORECASE).strip()
    feedback = re.sub(r'^—\s*', '', feedback).strip()
    feedback = re.sub(r'^-\s*', '', feedback).strip()
    
    return feedback if feedback else query

def _apply_feedback(template_name: str, feedback_text: str) -> str:
    """Apply feedback modifications via API"""
    try:
        feedback_url = f"{TDM_BASE_URL}/apply-feedback"
        payload = {
            "username": "TDM User",
            "template_name": template_name,
            "feedback_text": feedback_text
        }
        
        response = requests.post(feedback_url, json=payload, timeout=600)
        
        if response.status_code == 200:
            filename = _save_file(response, template_name)
            
            return f"""✅ **TEMPLATE DATA UPDATED SUCCESSFULLY**

🎯 **Template**: {template_name}
🔄 **Changes Applied**: {feedback_text}
📁 **File**: {filename}
📂 **Location**: TDM_files folder

🔍 **Review**: Check the updated data in TDM data sub app

💡 **Need More Changes?** You can make additional modifications:
- "Edit {template_name} - Customer Name should be more realistic"
- "Update {template_name} - Date fields should be recent"
- "Modify {template_name} - Amount values should be between 1000-5000" """
        else:
            return f"❌ **UPDATE FAILED**: {response.text}"
            
    except Exception as e:
        return f"❌ **UPDATE ERROR**: {str(e)}"

def _save_file(response, template_name: str) -> str:
    """Save file to TDM_files folder with template name (overwriting if exists)"""
    try:
        os.makedirs("TDM_files", exist_ok=True)
        
        # Clean the template name - remove common processing suffixes
        clean_template_name = template_name
        suffixes_to_remove = ["_processed", "_modified", "_updated", "_edited"]
        
        for suffix in suffixes_to_remove:
            clean_template_name = clean_template_name.replace(suffix, "")
        
        # Use clean template name to overwrite existing file
        filename = f"{clean_template_name}.xlsx"
        filepath = os.path.join("TDM_files", filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filename
    except Exception as e:
        clean_name = clean_template_name if 'clean_template_name' in locals() else template_name
        return f"file_save_error_{clean_name}.xlsx"
