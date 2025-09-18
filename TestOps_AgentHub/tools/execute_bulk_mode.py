# tools/execute_bulk_mode.py

import requests
import random
import re
from langchain.tools import tool
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("HOST_BASE_URL")
bulk_data_cache = {}

def format_data_display(extracted_data):
    """
    Format data display: if more than 30 items, show first 10, count hidden, last 10.
    Otherwise display all.
    """
    if len(extracted_data) <= 30:
        return ', '.join(extracted_data)
    else:
        first_10 = ', '.join(extracted_data[:10])
        last_10 = ', '.join(extracted_data[-10:])
        total_hidden = len(extracted_data) - 20
        return f"{first_10} ... ({total_hidden} more) ... {last_10}"
@tool("execute_bulk_mode", return_direct=True)
def bulk_mode_tool(testcase_name: str) -> str:
    """
    BULK MODE EXECUTION ACTIVATED
    Step 1: Extract data and present options to user
    """
    try:
        # --- 4.1 Get the Datasheet Name ---
        resp = requests.post(f"{BASE_URL}/search-testcase", json={"testcase_name": testcase_name})
        if resp.status_code != 200:
            return f"❌ Failed to search testcase: {resp.text}"
        
        search_result = resp.json()
        if not search_result.get("found"):
            return f"❌ Testcase '{testcase_name}' not found in bulk tests."
        
        datasheet_name = search_result.get("datasheet_name")
        if not datasheet_name:
            return f"❌ Datasheet name not found for testcase '{testcase_name}'."

        # --- 4.2 Extract Data from Datasheet ---
        resp = requests.post(f"{BASE_URL}/extract-data", json={"excel_file_name": datasheet_name})
        if resp.status_code != 200:
            return f"❌ Failed to extract data: {resp.text}"
        
        data_result = resp.json()
        if not data_result.get("found"):
            return f"❌ Could not find excel file '{datasheet_name}'."
        
        extracted_data = data_result.get("extracted_data", [])
        if not extracted_data:
            return f"❌ No data extracted for '{datasheet_name}'."

        # Store data globally for the second step (you could use Redis/database in production)
        global bulk_data_cache
        bulk_data_cache = {testcase_name: extracted_data}

        # Return selection options to UI
        return f"""📄 BULK MODE EXECUTION ACTIVATED for '{testcase_name}'
✅ Datasheet: {datasheet_name}
📊 Extracted {len(extracted_data)} values from '{data_result.get('column_name')}' column:

{format_data_display(extracted_data)}

**Please choose one of the following options:**

🔹 **Option 1**: All values ({len(extracted_data)} items)
   Command: `execute bulk {testcase_name} all`

🔹 **Option 2**: First N values (specify number)  
   Command: `execute bulk {testcase_name} first 10`

🔹 **Option 3**: Random selection (specify number)
   Command: `execute bulk {testcase_name} random 5`

🔹 **Option 4**: Range selection (from index to index)
   Command: `execute bulk {testcase_name} range 7 15`

🔹 **Option 5**: Custom selection (specify exact values)
   Command: `execute bulk {testcase_name} custom Supplier__015,Supplier__016`"""

    except Exception as e:
        return f"❌ Error during bulk execution: {str(e)}"

# Global cache for bulk data (use proper storage in production)
bulk_data_cache = {}

@tool("execute_bulk_mode_with_selection", return_direct=True)
def bulk_mode_with_selection_tool(command: str) -> str:
    """
    BULK MODE EXECUTION - Step 2: Execute with user selection
    Parses commands like:
    - execute bulk TestName all
    - execute bulk TestName first 10
    - execute bulk TestName random 5
    - execute bulk TestName range 7 15
    - execute bulk TestName custom Supplier__015,Supplier__016
    """
    try:
        # Parse the command
        parts = command.strip().split()
        if len(parts) < 4 or parts[0] != "execute" or parts[1] != "bulk":
            return "❌ Invalid command format. Use: execute bulk <testcase_name> <selection_type> [parameters]"
        
        testcase_name = parts[2]
        selection_type = parts[3].lower()
        
        # Get cached data
        if testcase_name not in bulk_data_cache:
            return f"❌ No cached data found for '{testcase_name}'. Please run the bulk mode first."
        
        extracted_data = bulk_data_cache[testcase_name]
        selected_values = []
        
        # Process different selection types
        if selection_type == "all":
            selected_values = extracted_data
            
        elif selection_type == "first":
            if len(parts) < 5:
                return "❌ Please specify the number: execute bulk <testcase> first <number>"
            n = int(parts[4])
            selected_values = extracted_data[:n]
            
        elif selection_type == "random":
            if len(parts) < 5:
                return "❌ Please specify the number: execute bulk <testcase> random <number>"
            n = int(parts[4])
            selected_values = random.sample(extracted_data, min(n, len(extracted_data)))
            
        elif selection_type == "range":
            if len(parts) < 6:
                return "❌ Please specify start and end indices: execute bulk <testcase> range <start> <end>"
            start_idx = int(parts[4]) - 1  # Convert to 0-based index
            end_idx = int(parts[5])        # End is exclusive
            selected_values = extracted_data[start_idx:end_idx]
            
        elif selection_type == "custom":
            if len(parts) < 5:
                return "❌ Please specify custom values: execute bulk <testcase> custom <value1,value2,value3>"
            custom_values = parts[4].split(',')
            # Validate that custom values exist in extracted data
            selected_values = [val.strip() for val in custom_values if val.strip() in extracted_data]
            if not selected_values:
                return f"❌ None of the specified values found in extracted data: {custom_values}"
        else:
            return f"❌ Unknown selection type: {selection_type}. Use: all, first, random, range, or custom"
        
        if not selected_values:
            return "❌ No values selected. Please check your selection criteria."
        
        # --- 4.3 Update reference IDs ---
        update_payload = {
            "testcase_name": testcase_name,
            "reference_ids": selected_values
        }
        
        resp = requests.post(f"{BASE_URL}/update-reference-ids", json=update_payload)
        if resp.status_code != 200:
            return f"❌ Failed to update reference IDs: {resp.text}"
        
        update_result = resp.json()
        if not update_result.get("success", False):
            return f"❌ Failed to update reference IDs for '{testcase_name}'. Response: {update_result}"
        
        # --- 4.4 Trigger the test ---
        trigger_payload = {"test_name": testcase_name}
        resp = requests.post(f"{BASE_URL}/trigger-test", json=trigger_payload)
        if resp.status_code != 200:
            return f"❌ Failed to trigger test: {resp.text}"
        
        trigger_result = resp.json()
        
        # Clean up cache
        if testcase_name in bulk_data_cache:
            del bulk_data_cache[testcase_name]
        
        return f"""✅ **Bulk Test Execution Completed!**

🎯 **Test Case**: {testcase_name}
📊 **Selected IDs**: {len(selected_values)} items
📝 **IDs Used**: {', '.join(selected_values[:10])}{'...' if len(selected_values) > 10 else ''}

🔄 **Update Status**: Reference IDs successfully updated
🚀 **Trigger Status**: Test execution initiated

✨ **Final Result**: Bulk test '{testcase_name}' has been successfully executed with your selected data!"""
        
    except ValueError as e:
        return f"❌ Invalid number format: {str(e)}"
    except Exception as e:
        return f"❌ Error during bulk execution: {str(e)}"
