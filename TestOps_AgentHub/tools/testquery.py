# tools/testquery.py
import os
import json
from langchain.tools import Tool

class TestDataQuery:
    def __init__(self):
        self.test_management_data = {}
        self.load_test_data()
    
    def load_test_data(self):
        """Load test data from test-data-source.json"""
        try:
            # Get the project root directory (go up from tools/)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            test_data_path = os.path.join(project_root, "test-data-source.json")
            
            with open(test_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.test_management_data = data.get("testManagement", {})
                print("✅ Test data loaded successfully from tools/testquery.py")
        except Exception as e:
            print(f"⚠ Error loading test data: {e}")
            self.test_management_data = {}
    
    def query_test_data(self, query: str) -> str:
        """
        Get relevant test data from modules section for the LLM to process.
        Returns raw data that the LLM can use to generate natural responses.
        """
        try:
            if not self.test_management_data:
                return "Test data is not available. Please check if test-data-source.json is loaded."
            
            modules = self.test_management_data.get("modules", [])
            query_lower = query.lower()
            
            # Always provide the modules data to LLM for processing
            relevant_data = {
                "modules": modules,
                "query": query
            }
            
            # Convert to a format the LLM can understand and process
            data_for_llm = f"User Query: {query}\n\nAvailable Test Modules Data:\n"
            
            for module in modules:
                data_for_llm += f"\nModule: {module['moduleName']}\n"
                data_for_llm += f"Test Cases in this module:\n"
                for test_case in module['testCases']:
                    data_for_llm += f"- Test {test_case['sNo']}: {test_case['testCaseName']}\n"
                    data_for_llm += f"  Description: {test_case['testDescription']}\n"
                    data_for_llm += f"  Category: {test_case['category']}\n"
                data_for_llm += "\n"
            
            data_for_llm += "\nPlease analyze this data and provide a helpful response to the user's query based on the modules and test cases information above."
            
            return data_for_llm
            
        except Exception as e:
            return f"Error retrieving test data: {str(e)}"

# Create the tool instance
test_query_instance = TestDataQuery()

# Create the LangChain tool
test_data_query_tool = Tool(
    name="query_test_data",
    description="Get test modules data to answer user questions about test cases, modules, and test organization. This tool provides raw test data from the modules section for the LLM to analyze and respond to user queries naturally.",
    func=test_query_instance.query_test_data
)
