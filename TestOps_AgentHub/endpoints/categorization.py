import re
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/categorize", tags=["categorization"])

class UserRequest(BaseModel):
    user_input: str
    username: str = "guest"

# This will be set by the main app
categorizer = None

def set_categorizer(app_categorizer):
    """Set the categorizer from main app"""
    global categorizer
    categorizer = app_categorizer

@router.post("/test")
async def categorize_test(req: UserRequest):
    """Debug endpoint to see test case categorization"""
    try:
        # Extract test case name
        patterns = [
            r'execute\s+(.+?)(?:\s*$)',
            r'trigger\s+(.+?)(?:\s*$)',
            r'run\s+(.+?)(?:\s*$)'
        ]
        
        test_case_name = None
        for pattern in patterns:
            match = re.search(pattern, req.user_input.lower())
            if match:
                test_case_name = match.group(1).strip()
                break
        
        if not test_case_name:
            test_case_name = req.user_input.strip()
        
        categorization = categorizer.categorize_test_case(test_case_name)
        
        return {
            "user_query": req.user_input,
            "extracted_test_case": test_case_name,
            "categorization": categorization,
            "recommended_tool": categorization.get("tool")
        }
        
    except Exception as e:
        return {"error": str(e)}
