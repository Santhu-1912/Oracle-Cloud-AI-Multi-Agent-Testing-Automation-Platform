# tools/execute_e2e_mode.py

import requests
import json
import os
from langchain.tools import tool
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("HOST_BASE_URL")

@tool("execute_e2e_mode", return_direct=True)
def e2e_mode_tool(flow_name: str) -> str:
    """
    END-TO-END MODE EXECUTION
    Finds the flow sequence from JSON and triggers all tests in sequence
    """
    try:
        # Load the JSON file from project root
        json_file_path = os.path.join(os.getcwd(), "test-data-source.json")
        
        if not os.path.exists(json_file_path):
            return f"❌ test-data-source.json not found in project root"
        
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Find the flow in endToEndFlows
        flows = data.get("testManagement", {}).get("testSuites", {}).get("endToEndFlows", {}).get("flows", [])
        
        target_flow = None
        for flow in flows:
            if flow.get("name", "").lower() == flow_name.lower() or flow.get("id", "").lower() == flow_name.lower():
                target_flow = flow
                break
        
        if not target_flow:
            available_flows = [flow.get("name", flow.get("id", "Unknown")) for flow in flows]
            return f"""❌ **END-TO-END FLOW NOT FOUND**

🔍 **Searched for**: {flow_name}
📋 **Available flows**: {', '.join(available_flows)}

Please use one of the available flow names."""
        
        # Get the sequence
        sequence = target_flow.get("sequence", [])
        if not sequence:
            return f"❌ No test sequence found for flow '{flow_name}'"
        
        # Create comma-separated test names for the API
        test_names = ",".join(sequence)
        
        # Trigger the tests in sequence
        trigger_payload = {"test_name": test_names}
        resp = requests.post(f"{BASE_URL}/trigger-test", json=trigger_payload)
        
        if resp.status_code != 200:
            return f"❌ Failed to trigger E2E flow '{flow_name}': {resp.text}"
        
        trigger_result = resp.json()
        
        # Check if the trigger was successful
        if trigger_result.get("success", False):
            return f"""✅ **END-TO-END MODE EXECUTION ACTIVATED**

🎯 **Flow Name**: {target_flow.get('name', flow_name)}
📊 **Test Sequence**: {len(sequence)} tests
📝 **Tests**: {' → '.join(sequence)}

🚀 **Status**: All tests in sequence triggered successfully

📊 **Result**: {trigger_result.get('message', 'E2E flow executed successfully')}

✨ **Summary**: End-to-End flow '{flow_name}' has been executed with all tests in sequence!"""
        else:
            return f"""❌ **END-TO-END MODE EXECUTION FAILED**

🎯 **Flow Name**: {flow_name}
📊 **Test Sequence**: {' → '.join(sequence)}
❌ **Status**: E2E flow execution failed

📊 **Error**: {trigger_result.get('message', 'Unknown error occurred')}

Please check the flow configuration and try again."""
    
    except FileNotFoundError:
        return f"❌ test-data-source.json file not found in project root"
    except json.JSONDecodeError:
        return f"❌ Invalid JSON format in test-data-source.json"
    except requests.exceptions.RequestException as e:
        return f"❌ Network error while triggering E2E flow '{flow_name}': {str(e)}"
    except Exception as e:
        return f"❌ Error during E2E execution of '{flow_name}': {str(e)}"
