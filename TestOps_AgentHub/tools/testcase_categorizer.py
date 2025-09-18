# tools/testcase_categorizer.py

import os
import json
from typing import Dict, Any, Optional

class TestCaseCategorizer:
    def __init__(self):
        self.test_data = {}
        self.load_test_data()
    
    def load_test_data(self):
        """Load test data from JSON file"""
        try:
            json_file_path = "test-data-source.json"
            
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r') as file:
                    self.test_data = json.load(file)
            else:
                # Fallback data structure
                self.test_data = {
                    "testManagement": {
                        "testSuites": {
                            "standardTests": {
                                "testCases": [
                                    "Invoice creation UI",
                                    "Customer Creation UI",
                                    "Register Supplier UI"
                                ]
                            },
                            "bulkTests": {
                                "testCases": ["BulkAPISupplierCreation"]
                            },
                            "endToEndFlows": {
                                "flows": [
                                    {
                                        "id": "Procure to Pay Flow",
                                        "name": "Procure to Pay Flow",
                                        "sequence": ["TC_API_SUPPLIER_01", "Invoice creation UI"]
                                    }
                                ]
                            }
                        }
                    }
                }
        except Exception as e:
            print(f"Error loading test data: {e}")
    
    def categorize_test_case(self, test_case_name: str) -> Dict[str, Any]:
        """
        Determine which category a test case belongs to
        Returns: {"category": str, "tool": str, "details": dict}
        """
        test_suites = self.test_data.get("testManagement", {}).get("testSuites", {})
        
        # Check in standard tests
        standard_tests = test_suites.get("standardTests", {}).get("testCases", [])
        for test in standard_tests:
            if test.lower() == test_case_name.lower():
                return {
                    "category": "standardTests",
                    "tool": "execute_standard_mode",
                    "test_name": test,
                    "details": {
                        "type": "individual",
                        "execution_mode": "standard"
                    }
                }
        
        # Check in bulk tests
        bulk_tests = test_suites.get("bulkTests", {}).get("testCases", [])
        for test in bulk_tests:
            if test.lower() == test_case_name.lower():
                return {
                    "category": "bulkTests",
                    "tool": "execute_bulk_mode",
                    "test_name": test,
                    "details": {
                        "type": "bulk",
                        "execution_mode": "bulk_data_processing"
                    }
                }
        
        # Check in end-to-end flows
        e2e_flows = test_suites.get("endToEndFlows", {}).get("flows", [])
        for flow in e2e_flows:
            flow_name = flow.get("name", "")
            flow_id = flow.get("id", "")
            
            if (flow_name.lower() == test_case_name.lower() or 
                flow_id.lower() == test_case_name.lower()):
                return {
                    "category": "endToEndFlows",
                    "tool": "execute_e2e_mode",
                    "test_name": flow_name,
                    "details": {
                        "type": "end-to-end",
                        "flow_id": flow_id,
                        "flow_name": flow_name,
                        "sequence": flow.get("sequence", [])
                    }
                }
        
        return {
            "category": "unknown",
            "tool": "execute_standard_mode",  # Default fallback
            "test_name": test_case_name,
            "details": {"type": "unknown"}
        }

# Global instance
categorizer = TestCaseCategorizer()
