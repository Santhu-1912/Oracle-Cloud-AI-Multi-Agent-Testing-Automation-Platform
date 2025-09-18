from fastapi import APIRouter

router = APIRouter(tags=["system"])

# This will be set by the main app
enhanced_tools = []

def set_tools(tools):
    """Set the tools list from main app"""
    global enhanced_tools
    enhanced_tools = tools

@router.get("/health")
async def health():
    return {
        "status": "healthy", 
        "available_tools": len(enhanced_tools),
        "normal_mode_tools": ["execute_standard_mode", "execute_bulk_mode", "execute_e2e_mode"],
        "agent_type": "LLM_DRIVEN_ENHANCED"
    }

@router.get("/tools")
async def list_tools():
    """List all available tools and their enhanced descriptions"""
    tools_info = []
    for tool in enhanced_tools:
        tools_info.append({
            "name": tool.name,
            "description": tool.description
        })
    return {
        "available_tools": tools_info,
        "selection_method": "LLM_DRIVEN_WITH_CATEGORIZATION"
    }
