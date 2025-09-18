# tools/test_manager_overview.py

import os
import requests
from langchain.tools import Tool
import json
import re
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
class TestManagerProcessor:
    def __init__(self):
        self.api_base_url = os.getenv("HOST_BASE_URL")
    
    def get_test_manager_data(self):
        """Get test manager overview data from API endpoint"""
        try:
            response = requests.get(f"{self.api_base_url}/testmanageroverview", timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error calling API: {e}")
            return None
        except Exception as e:
            print(f"Error processing API response: {e}")
            return None

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze user query to determine intent and response style"""
        query_lower = query.lower().strip()
        
        intent = {
            "query_type": "overview",  # overview, scheduled, summary, count, specific_module, configuration, data_sources
            "response_style": "detailed",  # detailed, brief, count_only, list_only
            "focus_area": None,  # tests, configuration, data, statistics, modules
            "specific_module": None,  # financial, supplier, hcm, ui, payment
            "original_query": query,
            "conversational_tone": "professional"  # professional, casual, technical
        }
        
        # Determine query type
        if any(phrase in query_lower for phrase in ["currently scheduled", "scheduled tests", "marked yes", "marked for execution", "tests to run", "tests running"]):
            intent["query_type"] = "scheduled"
        elif any(phrase in query_lower for phrase in ["how many", "count", "number of"]):
            intent["query_type"] = "count"
            intent["response_style"] = "count_only"
        elif any(phrase in query_lower for phrase in ["summary", "brief", "quick overview", "quick summary"]):
            intent["query_type"] = "summary"
            intent["response_style"] = "brief"
        elif any(phrase in query_lower for phrase in ["configuration", "config", "api endpoints", "authentication"]):
            intent["query_type"] = "configuration"
            intent["focus_area"] = "configuration"
        elif any(phrase in query_lower for phrase in ["data sources", "data management", "datasheets", "excel files"]):
            intent["query_type"] = "data_sources"
            intent["focus_area"] = "data"
        elif any(phrase in query_lower for phrase in ["financial", "fin", "invoice"]):
            intent["query_type"] = "specific_module"
            intent["specific_module"] = "Financial (FIN)"
        elif any(phrase in query_lower for phrase in ["supplier", "vendor"]):
            intent["query_type"] = "specific_module"
            intent["specific_module"] = "Supplier Management"
        elif any(phrase in query_lower for phrase in ["hcm", "human capital", "employee", "hire"]):
            intent["query_type"] = "specific_module"
            intent["specific_module"] = "Human Capital Management (HCM)"
        elif any(phrase in query_lower for phrase in ["ui tests", "user interface", "ui validation"]):
            intent["query_type"] = "specific_module"
            intent["specific_module"] = "User Interface Tests"
        elif any(phrase in query_lower for phrase in ["payment", "pay", "receipt"]):
            intent["query_type"] = "specific_module"
            intent["specific_module"] = "Payment (PAY)"
        elif any(phrase in query_lower for phrase in ["modules", "distribution", "breakdown"]):
            intent["query_type"] = "modules"
            intent["focus_area"] = "modules"
        
        # Determine response style
        if any(phrase in query_lower for phrase in ["list", "show me", "give me"]) and "detailed" not in query_lower:
            intent["response_style"] = "list_only"
        elif any(phrase in query_lower for phrase in ["detailed", "comprehensive", "complete", "full"]):
            intent["response_style"] = "detailed"
        
        # Determine conversational tone
        if any(phrase in query_lower for phrase in ["please", "can you", "could you", "would you"]):
            intent["conversational_tone"] = "polite"
        elif any(phrase in query_lower for phrase in ["what", "which", "where", "how"]):
            intent["conversational_tone"] = "direct"
        
        return intent

    def generate_conversational_intro(self, intent: Dict[str, Any]) -> str:
        """Generate a conversational introduction based on query intent"""
        query = intent["original_query"]
        
        if intent["query_type"] == "scheduled":
            return f"Based on your request about **{query}**, here are the tests currently marked for execution:\n\n"
        elif intent["query_type"] == "count":
            return f"You asked **\"{query}\"** - let me give you those numbers:\n\n"
        elif intent["query_type"] == "summary":
            return f"Here's a **{query}** as requested:\n\n"
        elif intent["query_type"] == "configuration":
            return f"Regarding **{query}**, here's the configuration information:\n\n"
        elif intent["query_type"] == "data_sources":
            return f"For your question about **{query}**, here's the data management overview:\n\n"
        elif intent["query_type"] == "specific_module":
            module = intent["specific_module"]
            return f"You asked about **{query}**. Here's information about {module} tests:\n\n"
        else:
            return f"Here's the **{query}** information you requested:\n\n"

    def format_scheduled_tests_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format response for scheduled tests queries"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        scheduled_tests = data.get('currently_scheduled_tests', [])
        summary = data.get('test_execution_summary', {})
        
        if intent["response_style"] == "count_only":
            response += f"🎯 **{len(scheduled_tests)} tests** are currently scheduled for execution.\n\n"
            response += f"📊 This represents **{summary.get('execution_percentage', 0)}%** of your total test suite ({summary.get('total_test_cases', 0)} tests).\n"
        elif intent["response_style"] == "list_only":
            response += f"📋 **Currently Scheduled Tests ({len(scheduled_tests)} total):**\n\n"
            for i, test in enumerate(scheduled_tests, 1):
                response += f"{i}. **{test['test_case_id']}** (Data: {test['datasheet_name']})\n"
        else:
            response += f"## 🎯 Tests Marked 'Yes' for Execution\n\n"
            response += f"**{len(scheduled_tests)} tests** are currently scheduled:\n\n"
            
            if scheduled_tests:
                response += "| # | Test Case ID | DataSheet | Reference ID | ID Name |\n"
                for i, test in enumerate(scheduled_tests, 1):
                    response += f"| {i} | **{test['test_case_id']}** | {test['datasheet_name']} | {test['reference_id']} | {test['id_name']} |\n"
                
                response += f"\n📈 **Execution Statistics:**\n"
                response += f"- **Scheduled:** {summary.get('tests_scheduled', 0)} tests\n"
                response += f"- **Pending:** {summary.get('tests_not_scheduled', 0)} tests\n"
                response += f"- **Coverage:** {summary.get('execution_percentage', 0)}%\n"
        
        response += f"\n💡 **Need more details?** Ask me about specific test cases or modules!\n"
        return response

    def format_count_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format response for count-related queries"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        summary = data.get('test_execution_summary', {})
        distribution = data.get('test_distribution_by_module', {})
        config = data.get('test_configuration_overview', {})
        
        response += "📊 **Test Manager Statistics:**\n\n"
        response += f"🎯 **{summary.get('tests_scheduled', 0)}** tests scheduled for execution\n"
        response += f"📝 **{summary.get('total_test_cases', 0)}** total test cases available\n"
        response += f"⚙️ **{config.get('total_configured_tests', 0)}** tests configured\n"
        response += f"🌐 **{config.get('unique_api_endpoints', 0)}** unique API endpoints\n"
        response += f"📁 **{len(distribution)}** test modules\n\n"
        
        response += "**Module Breakdown:**\n"
        for module, details in distribution.items():
            response += f"• **{module}:** {details['count']} tests\n"
        
        return response

    def format_summary_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format brief summary response"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        summary = data.get('test_execution_summary', {})
        distribution = data.get('test_distribution_by_module', {})
        
        response += "## 📊 Quick Test Manager Summary\n\n"
        response += f"🎯 **{summary.get('tests_scheduled', 0)}/{summary.get('total_test_cases', 0)}** tests scheduled ({summary.get('execution_percentage', 0)}%)\n\n"
        
        response += "**Top Modules:**\n"
        sorted_modules = sorted(distribution.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
        for module, details in sorted_modules:
            response += f"• **{module}:** {details['count']} tests\n"
        
        if len(distribution) > 3:
            remaining = len(distribution) - 3
            response += f"• *...and {remaining} more modules*\n"
        
        response += f"\n💬 **Want details?** Ask about specific modules or configurations!\n"
        return response

    def format_configuration_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format configuration-focused response"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        config = data.get('test_configuration_overview', {})
        
        response += "## ⚙️ Test Configuration Details\n\n"
        
        if intent["response_style"] == "brief":
            response += f"📋 **{config.get('total_configured_tests', 0)}** tests configured\n"
            response += f"🌐 **{config.get('unique_api_endpoints', 0)}** API endpoints\n"
            if 'authentication' in config:
                auth = config['authentication']
                response += f"👤 **{auth.get('total_configured_users', 0)}** configured users\n"
        else:
            response += "| Configuration Item | Value |\n"
            response += f"| **Total Configured Tests** | {config.get('total_configured_tests', 0)} |\n"
            response += f"| **Unique API Endpoints** | {config.get('unique_api_endpoints', 0)} |\n"
            
            if 'authentication' in config:
                auth = config['authentication']
                response += f"| **Primary User** | {auth.get('primary_user', 'N/A')} |\n"
                response += f"| **Total Users** | {auth.get('total_configured_users', 0)} |\n"
            
            response += "\n**API Endpoints:**\n"
            endpoints = config.get('api_endpoints', [])
            for i, endpoint in enumerate(endpoints[:3], 1):  # Show first 3
                response += f"{i}. `{endpoint}`\n"
            if len(endpoints) > 3:
                response += f"*...and {len(endpoints) - 3} more endpoints*\n"
        
        return response

    def format_module_specific_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format response for specific module queries"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        module = intent["specific_module"]
        distribution = data.get('test_distribution_by_module', {})
        scheduled_tests = data.get('currently_scheduled_tests', [])
        
        if module in distribution:
            module_data = distribution[module]
            response += f"## 📁 {module} Module Details\n\n"
            response += f"📊 **{module_data['count']} tests** in this module\n\n"
            
            # Show test cases
            if intent["response_style"] == "list_only":
                response += "**Test Cases:**\n"
                for i, test_case in enumerate(module_data['test_cases'], 1):
                    # Check if this test is scheduled
                    is_scheduled = any(test['test_case_id'] == test_case for test in scheduled_tests)
                    status = "🟢 Scheduled" if is_scheduled else "⚪ Not Scheduled"
                    response += f"{i}. **{test_case}** - {status}\n"
            else:
                response += "| # | Test Case ID | Status |\n"
                for i, test_case in enumerate(module_data['test_cases'], 1):
                    is_scheduled = any(test['test_case_id'] == test_case for test in scheduled_tests)
                    status = "🟢 Scheduled" if is_scheduled else "⚪ Not Scheduled"
                    response += f"| {i} | **{test_case}** | {status} |\n"
            
            # Add module statistics
            scheduled_in_module = sum(1 for test in scheduled_tests 
                                    if test['test_case_id'] in module_data['test_cases'])
            response += f"\n📈 **Module Statistics:**\n"
            response += f"- **Total Tests:** {module_data['count']}\n"
            response += f"- **Scheduled:** {scheduled_in_module}\n"
            response += f"- **Pending:** {module_data['count'] - scheduled_in_module}\n"
        else:
            response += f"❌ No tests found for **{module}** module.\n\n"
            response += "**Available modules:**\n"
            for available_module in distribution.keys():
                response += f"• {available_module}\n"
        
        return response

    def format_comprehensive_overview(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format complete overview response"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        summary = data.get('test_execution_summary', {})
        distribution = data.get('test_distribution_by_module', {})
        scheduled_tests = data.get('currently_scheduled_tests', [])
        config = data.get('test_configuration_overview', {})
        
        response += "# 📊 Complete Test Manager Overview\n\n"
        
        # Executive Summary
        response += "## 🎯 Executive Summary\n\n"
        response += f"📈 **{summary.get('tests_scheduled', 0)}/{summary.get('total_test_cases', 0)}** tests scheduled ({summary.get('execution_percentage', 0)}% coverage)\n"
        response += f"📁 **{len(distribution)}** modules with **{config.get('total_configured_tests', 0)}** configured tests\n"
        response += f"🌐 **{config.get('unique_api_endpoints', 0)}** API endpoints ready for testing\n\n"
        
        # Module Distribution
        response += "## 📁 Test Distribution by Module\n\n"
        response += "| Module | Total Tests | Scheduled | Pending |\n"
        
        
        for module, details in distribution.items():
            scheduled_in_module = sum(1 for test in scheduled_tests 
                                    if test['test_case_id'] in details['test_cases'])
            pending = details['count'] - scheduled_in_module
            response += f"| **{module}** | {details['count']} | {scheduled_in_module} | {pending} |\n"
        
        # Scheduled Tests Summary
        response += f"\n## ⏰ Currently Scheduled Tests ({len(scheduled_tests)} total)\n\n"
        if scheduled_tests:
            for i, test in enumerate(scheduled_tests, 1):
                response += f"{i}. **{test['test_case_id']}** (Data: {test['datasheet_name']})\n"
        else:
            response += "❌ **No tests currently scheduled for execution.**\n"
        
        # Quick Stats
        response += f"\n## 📊 Quick Statistics\n\n"
        response += f"• **Total Test Cases:** {summary.get('total_test_cases', 0)}\n"
        response += f"• **Configured Tests:** {config.get('total_configured_tests', 0)}\n"
        response += f"• **Data Sources:** {data.get('data_management', {}).get('total_data_sources', 0)}\n"
        response += f"• **API Endpoints:** {config.get('unique_api_endpoints', 0)}\n"
        
        response += f"\n💡 **Pro Tip:** Ask about specific modules, configurations, or scheduled tests for detailed information!\n"
        return response

    def process_test_manager_query(self, query: str) -> str:
        """Main method to process test manager queries with dynamic responses"""
        try:
            # Check if query is related to test/run manager
            manager_keywords = [
                "run manager", "test manager", "manager", "test marked", "run marked",
                "detail about manager", "info about test", "info about run",
                "Please share the run", "details about test", "marked in run",
                "test execution", "scheduled tests", "test overview", "currently scheduled",
                "how many", "count", "summary", "configuration", "modules", "distribution"
            ]
            
            query_lower = query.lower()
            is_manager_query = any(keyword in query_lower for keyword in manager_keywords)
            
            if not is_manager_query:
                return f"I understand you're asking about: **\"{query}\"**\n\nThis seems to be related to test management. Let me help you with test manager information, scheduled tests, or test configurations. Could you please rephrase your question to include terms like 'test manager', 'scheduled tests', or 'test overview'?"
            
            # Get test manager data from API
            data = self.get_test_manager_data()
            if not data:
                return "❌ **Unable to fetch test manager data** from the API endpoint.\n\n🔧 Please ensure the test manager service is running at `http://localhost:port/testmanageroverview`\n\n💡 **Try again in a moment** or contact your system administrator."
            
            # Analyze query intent
            intent = self.analyze_query_intent(query)
            
            # Generate dynamic response based on intent
            if intent["query_type"] == "scheduled":
                return self.format_scheduled_tests_response(data, intent)
            elif intent["query_type"] == "count":
                return self.format_count_response(data, intent)
            elif intent["query_type"] == "summary":
                return self.format_summary_response(data, intent)
            elif intent["query_type"] == "configuration":
                return self.format_configuration_response(data, intent)
            elif intent["query_type"] == "data_sources":
                return self.format_data_sources_response(data, intent)
            elif intent["query_type"] == "specific_module":
                return self.format_module_specific_response(data, intent)
            elif intent["query_type"] == "modules":
                return self.format_modules_overview_response(data, intent)
            else:
                return self.format_comprehensive_overview(data, intent)
                
        except Exception as e:
            return f"❌ **Error processing your request:** \"{query}\"\n\n🔍 **Technical details:** {str(e)}\n\n💡 **Suggestion:** Try rephrasing your question or ask for a 'test manager overview'."

    def format_data_sources_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format response for data sources queries"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        data_mgmt = data.get('data_management', {})
        
        response += "## 📊 Data Management Overview\n\n"
        response += f"📁 **{data_mgmt.get('total_data_sources', 0)}** data sources configured\n\n"
        
        sources = data_mgmt.get('data_sources', [])
        if sources:
            response += "**Available Data Sources:**\n"
            for i, source in enumerate(sources, 1):
                response += f"{i}. `{source}`\n"
        
        return response

    def format_modules_overview_response(self, data: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """Format response for modules overview queries"""
        intro = self.generate_conversational_intro(intent)
        response = intro
        
        distribution = data.get('test_distribution_by_module', {})
        scheduled_tests = data.get('currently_scheduled_tests', [])
        
        response += "## 📁 Test Modules Overview\n\n"
        response += f"📊 **{len(distribution)} modules** with tests available\n\n"
        
        response += "| Module | Tests | Scheduled | Coverage |\n"
       
        
        for module, details in distribution.items():
            scheduled_in_module = sum(1 for test in scheduled_tests 
                                    if test['test_case_id'] in details['test_cases'])
            coverage = f"{(scheduled_in_module/details['count']*100):.0f}%" if details['count'] > 0 else "0%"
            response += f"| **{module}** | {details['count']} | {scheduled_in_module} | {coverage} |\n"
        
        return response

# Create tool instance
test_manager_instance = TestManagerProcessor()

test_manager_overview_tool = Tool(
    name="test_manager_overview",
    description="""
    Provides intelligent and dynamic test manager responses based on user queries. 
    
    Handles various types of queries:
    - "currently scheduled tests" or "tests marked yes for execution" - Shows scheduled tests
    - "how many tests" or "count" - Provides numerical statistics  
    - "summary" or "quick overview" - Brief overview
    - "configuration" or "api endpoints" - Configuration details
    - "financial tests" or module-specific queries - Module-specific information
    - "test manager overview" - Comprehensive overview
    
    The tool analyzes the user's specific question and provides contextual, conversational responses
    instead of static formatted output. Each response is tailored to what the user actually asked for.
    """,
    func=test_manager_instance.process_test_manager_query
)
