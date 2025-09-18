import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentType, initialize_agent
from langchain.schema import SystemMessage

# Import all tools
from tools.testquery import test_data_query_tool
from tools.execute_healmode import heal_mode_tool
from tools.TDM_generator import tdm_data_generator
from tools.TDM_editor import tdm_data_editor
from tools.test_data_file_manager import test_data_file_manager_tool
from tools.DataRecon_tool import data_recon_tool
from tools.patchversiontool import patch_version_tool
from tools.test_manager_overview import test_manager_overview_tool
from tools.execute_standard_mode import standard_mode_tool,standard_mode_with_selection_tool
from tools.execute_bulk_mode import bulk_mode_tool, bulk_mode_with_selection_tool
from tools.execute_e2e_mode import e2e_mode_tool
from tools.testcase_categorizer import categorizer
from tools.execute_run_manager_mode import execute_run_manager_mode

# Import endpoint routers
from endpoints.reports import router as reports_router
from endpoints.testdata import router as testdata_router
from endpoints.mcp_agent import router as agent_router, set_agent_and_categorizer
from endpoints.categorization import router as categorization_router, set_categorizer
from endpoints.system import router as system_router, set_tools

# Load environment variables
load_dotenv()

app = FastAPI(title="MCP UI Backend - Enhanced Normal Mode", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# LLM + Agent Setup
# ---------------------------
llm = AzureChatOpenAI(
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

# Enhanced tools list
enhanced_tools = [
    test_data_query_tool,
    heal_mode_tool,
    tdm_data_generator,
    tdm_data_editor,
    execute_run_manager_mode,
    data_recon_tool,
    patch_version_tool,
    standard_mode_tool,
    standard_mode_with_selection_tool,
    bulk_mode_tool,
    bulk_mode_with_selection_tool,
    e2e_mode_tool,
    test_data_file_manager_tool,
    test_manager_overview_tool
]

# Enhanced system message
system_message = """
You are an intelligent assistant with access to specialized tools. Analyze user queries carefully and choose the most appropriate tool.

TOOL SELECTION PRIORITY (Check in this order):
0. **RUN MANAGER MODE** — If query is exactly one of these commands:
   `run test manager`, `run run manager`, `trigger test manager`, `trigger run manager`, 
   `execute run manager`, `execute test manager`
   OR begins with any of these commands followed by ` with`:
   `run test manager with`, `run run manager with`, `trigger test manager with`, 
   `trigger run manager with`, `execute run manager with`, `execute test manager with`
   → Use execute_run_manager_mode
   - Only activate for these exact phrases; ignore partial words/subwords.

1. **TEST/RUN MANAGER Detection** - If query contains "overview of test manager", "run manager", "manager","run manager overview","Shceduled tests from run/test Manager":
   → Use test_manager_overview

2. **HEALING MODE Detection** - If query contains "healing", "heal mode", "healing mode" anywhere:
   → Use execute_heal_mode

3. **STANDARD MODE WITH SELECTION** - If query contains "execute [TestName] with [Entity]" pattern:
   → Use execute_standard_mode_with_selection
   
   Examples: 
   - "execute Invoice creation UI with TEST_Sup_011" → Use execute_standard_mode_with_selection
   - "execute AR Invoice UI with TEST_Cons_001" → Use execute_standard_mode_with_selection
   
4.  **TDM DATA EDITOR** (tdm_data_editor) - Use when query contains:
   - Field names: "field ID", "Feild value","header","lines"
    → Use tdm_data_editor

5. **TDM/ESAN Generator** - If query contains "TDM", "ESAN", "TDM ESAN","Generate Test Data":
   → Use tdm_data_generator

6. **TEST DATA FILE MANAGER** - If query contains "update test data", "add new test data", "replace test data":
   → Use test_data_file_manager

7. **DATA RECON Detection** - If query contains "data recon", "reconciliation", "consolidation":
   → Use data_reconciliation

8. **PATCH Detection** - If query contains "patch", "version", "Oracle patch":
   → Use patch_version_generator

9. **BULK MODE SELECTION** - If query starts with "execute bulk":
   → Use execute_bulk_mode_with_selection
   Examples: "execute bulk TestName all", "execute bulk TestName first 10", etc.

10. **NORMAL MODE/UI Testing** - For UI operations, testing, triggering, execution:
   Based on test case type:
   - **Standard Tests** (individual test cases): Use execute_standard_mode
   - **Bulk Tests** (data processing workflows): Use execute_bulk_mode
   - **End-to-End Flows** (sequential test chains): Use execute_e2e_mode

11. **General Queries** - For basic information requests:
   → Use test_data_query 
   
NORMAL MODE TOOL SELECTION:
- For queries like "execute Invoice creation UI" → Use execute_standard_mode
- For queries like "run BulkAPISupplierCreation" → Use execute_bulk_mode
- For queries like "execute Procure to Pay Flow" → Use execute_e2e_mode

BULK MODE SPECIFIC PATTERNS:
- "execute bulk [TestName] all" → Use execute_bulk_mode_with_selection
- "execute bulk [TestName] first [N]" → Use execute_bulk_mode_with_selection
- "execute bulk [TestName] random [N]" → Use execute_bulk_mode_with_selection
- "execute bulk [TestName] range [start] [end]" → Use execute_bulk_mode_with_selection
- "execute bulk [TestName] custom [values]" → Use execute_bulk_mode_with_selection

IMPORTANT RULES FOR TEST EXECUTION:
- Always scan the ENTIRE query for healing mode keywords first
- Check for "execute bulk" pattern before other test execution patterns
- For bulk selection commands, pass the ENTIRE command string to execute_bulk_mode_with_selection
- For test execution, analyze the test case name to determine the appropriate normal mode tool
- Be case-insensitive in your analysis
- Provide comprehensive responses using the selected tool

PATCH REPORT PATTERNS:
- "execute patch report" → Show available versions via patch_version_generator
- "patch report" → Show available versions via patch_version_generator
- "execute patch report version 24C" → Generate report for specific version
- "patch report version 25A" → Generate report for specific version

IMPORTANT RULES FOR PATCH REPORT:
- Always pass the ENTIRE user query to patch_version_generator for patch-related requests
- The tool will handle version validation and user guidance internally
- For patch queries, check for "patch" keyword anywhere in the query

For TEST MANAGER queries:
- ANALYZE the user's specific question
- Don't always provide the full overview
- Match response scope to user intent:
  * "currently scheduled tests" → Show only scheduled tests
  * "quick summary" → Provide brief statistics
  * "financial tests" → Filter by Financial module
  * "how many tests" → Provide counts only

IMPORTANT: Pass the EXACT user query to test_manager_overview tool so it can analyze intent and provide targeted responses.

Example responses should vary:
- User: "how many tests are scheduled?" → "4 tests are currently scheduled"
- User: "show financial tests" → Show only Financial module tests
- User: "quick overview" → Brief summary with key metrics
- User: "detailed test manager overview" → Full comprehensive view
"""

# Initialize agent with system message
agent = initialize_agent(
    tools=enhanced_tools,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True,
    agent_kwargs={
        "system_message": SystemMessage(content=system_message)
    }
)

# Set up endpoint dependencies
set_agent_and_categorizer(agent, categorizer)
set_categorizer(categorizer)
set_tools(enhanced_tools)

# Include all routers
app.include_router(reports_router)
app.include_router(testdata_router)
app.include_router(agent_router)
app.include_router(categorization_router)
app.include_router(system_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
