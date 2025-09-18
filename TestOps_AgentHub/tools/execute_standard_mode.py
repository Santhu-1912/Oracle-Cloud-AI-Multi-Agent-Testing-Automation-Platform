# tools/execute_standard_mode.py

import requests
from langchain.tools import tool
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("HOST_BASE_URL")

@tool("execute_standard_mode", return_direct=True)
def standard_mode_tool(testcase_name: str) -> str:
    """
    STANDARD MODE EXECUTION - Step 1: Extract data and present options to user
    
    For specific test cases that require entity selection:
    - Invoice creation UI: Shows available suppliers
    - AR Invoice UI: Shows available consumers (future)
    - Other entity-driven tests: Shows relevant entities
    
    For other tests: Direct trigger without preprocessing
    """
    try:
        # Special handling for Invoice creation UI test case
        if testcase_name == "Invoice creation UI":
            return handle_invoice_creation_ui_discovery(testcase_name)
        # Future entity-driven tests can be added here
        # elif testcase_name == "AR Invoice UI":
        #     return handle_ar_invoice_ui_discovery(testcase_name)
        # elif testcase_name == "Purchase Order UI":
        #     return handle_purchase_order_ui_discovery(testcase_name)
        else:
            # Standard mode for other test cases - direct trigger
            return execute_direct_trigger(testcase_name)
            
    except requests.exceptions.RequestException as e:
        return f"❌ Network error while executing test '{testcase_name}': {str(e)}"
    except Exception as e:
        return f"❌ Error during execution of '{testcase_name}': {str(e)}"

def handle_invoice_creation_ui_discovery(testcase_name: str) -> str:
    """
    Handle the Invoice creation UI test case - Step 1: Show available suppliers
    """
    try:
        # Step 1: Get supplier list from /supplierInvoice/summary
        supplier_resp = requests.get(f"{BASE_URL}/supplierInvoice/summary")
        
        if supplier_resp.status_code != 200:
            return f"❌ Failed to get supplier list: {supplier_resp.text}"
        
        supplier_data = supplier_resp.json()
        unique_suppliers = supplier_data.get("unique_suppliers", [])
        total_suppliers = supplier_data.get("total_unique_suppliers", 0)
        
        # Step 2: Check if suppliers are available
        if total_suppliers == 0:
            return f"""❌ **NO SUPPLIERS AVAILABLE**

🎯 **Test Case**: {testcase_name}
⚠️ **Issue**: No suppliers found in TC_API_SUPPLIER_01 reports

📋 **Action Required**: 
Please create a supplier first by running the supplier creation test case before attempting to create an invoice.

**Available suppliers**: {total_suppliers}
**Files processed**: {supplier_data.get('total_files_processed', 0)}

Cannot proceed with invoice creation until at least one supplier is available."""

        # Store data globally for the second step (like bulk mode)
        global standard_data_cache
        standard_data_cache = {testcase_name: unique_suppliers}
        
        # Step 3: Display suppliers and command options (like bulk mode)
        suppliers_display = ', '.join(unique_suppliers)
        
        return f"""🔄 **INVOICE CREATION UI - SUPPLIER SELECTION REQUIRED**

🎯 **Test Case**: {testcase_name}
📊 **Available Suppliers**: {total_suppliers} suppliers found

**Suppliers**: {suppliers_display}

**Please choose ONE supplier using the command below:**

🔹 **Select Supplier**: 
Command: `execute {testcase_name} with [SupplierName]`

**Examples**:
• `execute {testcase_name} with {unique_suppliers[0]}`
• `execute {testcase_name} with {unique_suppliers[1] if len(unique_suppliers) > 1 else unique_suppliers}`

Once you select a supplier, I'll update the invoice data and trigger the test execution."""

    except Exception as e:
        return f"❌ Error in supplier discovery process: {str(e)}"

def execute_direct_trigger(testcase_name: str) -> str:
    """
    Execute direct test trigger for standard test cases
    """
    try:
        trigger_payload = {"test_name": testcase_name}
        resp = requests.post(f"{BASE_URL}/trigger-test", json=trigger_payload)
        
        if resp.status_code != 200:
            return f"❌ Failed to trigger test '{testcase_name}': {resp.text}"
        
        trigger_result = resp.json()
        
        # Check if the trigger was successful
        if trigger_result.get("success", False):
            return f"""✅ **STANDARD MODE EXECUTION ACTIVATED**

🎯 **Test Case**: {testcase_name}
🚀 **Status**: Test execution completed successfully

📊 **Result**: {trigger_result.get('message', 'Test executed successfully')}

✨ **Summary**: Standard test '{testcase_name}' has been executed directly!"""
        else:
            return f"""❌ **STANDARD MODE EXECUTION FAILED**

🎯 **Test Case**: {testcase_name}
❌ **Status**: Test execution failed

📊 **Error**: {trigger_result.get('message', 'Unknown error occurred')}

Please check the test case name and try again."""
            
    except Exception as e:
        return f"❌ Error executing standard test: {str(e)}"

# Global cache for standard mode data (like bulk mode)
standard_data_cache = {}

@tool("execute_standard_mode_with_selection", return_direct=True)
def standard_mode_with_selection_tool(command: str) -> str:
    """
    STANDARD MODE EXECUTION - Step 2: Execute with user selection
    
    Parses commands like:
    - execute Invoice creation UI with TEST_Sup_011
    - execute AR Invoice UI with TEST_Cons_001 (future)
    - execute Purchase Order UI with TEST_Vendor_005 (future)
    """
    try:
        # Parse the command
        command = command.strip()
        
        # Check for "execute [TestName] with [Entity]" pattern
        if " with " not in command:
            return "❌ Invalid command format. Use: execute [TestName] with [EntityName]"
        
        parts = command.split(" with ")
        if len(parts) != 2:
            return "❌ Invalid command format. Use: execute [TestName] with [EntityName]"
        
        testcase_part = parts[0].replace("execute ", "").strip()
        selected_entity = parts[1].strip()
        
        # Route to appropriate handler based on test case
        if testcase_part == "Invoice creation UI":
            return handle_invoice_creation_execution(testcase_part, selected_entity)
        # Future handlers can be added here
        # elif testcase_part == "AR Invoice UI":
        #     return handle_ar_invoice_execution(testcase_part, selected_entity)
        # elif testcase_part == "Purchase Order UI":
        #     return handle_purchase_order_execution(testcase_part, selected_entity)
        else:
            return f"❌ Unknown test case pattern: '{testcase_part}'. Please check the test case name."
            
    except Exception as e:
        return f"❌ Error during standard execution with selection: {str(e)}"

def handle_invoice_creation_execution(testcase_name: str, supplier_name: str) -> str:
    """
    Handle Invoice creation UI execution with selected supplier
    """
    try:
        # Get cached suppliers (like bulk mode)
        if testcase_name not in standard_data_cache:
            return f"❌ No cached supplier data found for '{testcase_name}'. Please run the standard mode first."
        
        cached_suppliers = standard_data_cache[testcase_name]
        
        # Validate supplier exists in cached list
        if supplier_name not in cached_suppliers:
            available = ", ".join(cached_suppliers)
            return f"❌ Invalid supplier '{supplier_name}'. Available suppliers: {available}"
        
        # Step 1: Update supplier in invoice data
        update_resp = requests.post(f"{BASE_URL}/updateSupplierInInvoice?Supplier={supplier_name}")
        
        if update_resp.status_code != 200:
            return f"❌ Failed to update supplier '{supplier_name}': {update_resp.text}"
        
        update_result = update_resp.json()
        
        # Step 2: Trigger the test after successful supplier update
        trigger_payload = {"test_name": testcase_name}
        trigger_resp = requests.post(f"{BASE_URL}/trigger-test", json=trigger_payload)
        
        if trigger_resp.status_code != 200:
            return f"❌ Supplier updated successfully, but failed to trigger test: {trigger_resp.text}"
        
        trigger_result = trigger_resp.json()
        
        # Clean up cache (like bulk mode)
        if testcase_name in standard_data_cache:
            del standard_data_cache[testcase_name]
        
        if trigger_result.get("success", False):
            return f"""✅ **INVOICE CREATION UI - EXECUTION COMPLETED**

🎯 **Test Case**: {testcase_name}
👤 **Selected Supplier**: {supplier_name}

**Step 1 - Supplier Update**:
✅ {update_result.get('message', 'Supplier updated successfully')}

**Step 2 - Test Execution**:
🚀 **Status**: Test execution completed successfully
📊 **Result**: {trigger_result.get('message', 'Test executed successfully')}

✨ **Summary**: Invoice creation test executed successfully with supplier '{supplier_name}'!"""
        else:
            return f"""⚠️ **PARTIAL SUCCESS - TEST EXECUTION FAILED**

👤 **Selected Supplier**: {supplier_name}

**Step 1 - Supplier Update**:
✅ {update_result.get('message', 'Supplier updated successfully')}

**Step 2 - Test Execution**:
❌ **Status**: Test execution failed
📊 **Error**: {trigger_result.get('message', 'Unknown error occurred')}

The supplier was updated successfully, but the test execution failed. Please check the test configuration."""
            
    except Exception as e:
        return f"❌ Error during invoice creation execution: {str(e)}"

# Future execution handlers can be added here
def handle_ar_invoice_execution(testcase_name: str, consumer_name: str) -> str:
    """
    Handle AR Invoice UI execution with selected consumer (future implementation)
    """
    return f"🚧 AR Invoice execution with consumer '{consumer_name}' coming soon!"

def handle_purchase_order_execution(testcase_name: str, vendor_name: str) -> str:
    """
    Handle Purchase Order UI execution with selected vendor (future implementation)
    """
    return f"🚧 Purchase Order execution with vendor '{vendor_name}' coming soon!"
